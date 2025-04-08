import scrapy
import logging
from scrapy.utils.log import configure_logging
from urllib.parse import urljoin, urlparse

class cfsObitCounter(scrapy.Spider):
    # Puts logs into a file
    configure_logging(install_root_handler=False)
    logging.basicConfig(
        filename='log.txt',
        format='%(levelname)s: %(message)s',
        level=logging.INFO
    )

    name = 'cfsCounter'
    
    def __init__(self, domain=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if domain:
            self.urls = self.urls = [d.strip() for d in domain.split(',')]
        else:
            self.urls = []

    def start_requests(self):
        for url in self.urls:
            parsed = urlparse(url)

            if not parsed.scheme:
                url = f"https://{url}"

            parsed = urlparse(url)
            if not parsed.netloc.startswith('www.'):
                url = url.replace(parsed.netloc, f"www.{parsed.netloc}")
                
            fullURL = urljoin(url, '/listings')
            self.logger.info(f"URL: {fullURL}")
            yield scrapy.Request(url=fullURL, headers=self.build_headers(url, include_content_type=False), callback=self.get_fhid)

    def get_fhid(self, response):
        fhid = response.css('input[name="sids"]::attr(value)').get()

        if fhid:
            self.logger.info(f"FHID found: {fhid}")
            url = response.urljoin("/pax/obitsrch")
            base_url = "{}://{}".format(urlparse(response.url).scheme, urlparse(response.url).netloc)
            yield scrapy.Request(url=url, method='POST', body=self.build_payload(fhid, 0), headers=self.build_headers(base_url, include_referer=True),
                                 callback=self.get_bounds, cb_kwargs={'fhid': fhid, 'obitPageURL': url, 'pgNumber': 0})
        else:
            self.logger.error("FHID not found")

    def get_bounds(self, response, fhid, obitPageURL, pgNumber):
        lastPageIndicator = response.css(".bg-info").get()
        base_url = "{}://{}".format(urlparse(response.url).scheme, urlparse(response.url).netloc)

        if lastPageIndicator:
            upperBound = pgNumber
            lowerBound = pgNumber // 2
            middlePgNumber = (upperBound + lowerBound) // 2
            yield scrapy.Request(url=obitPageURL, method='POST', body=self.build_payload(fhid, middlePgNumber),
                                 headers=self.build_headers(base_url, include_referer=True), callback=self.get_last_page,
                                 cb_kwargs={'fhid': fhid, 'obitPageURL': obitPageURL, 'upperBound': upperBound,
                                            'lowerBound': lowerBound, 'middlePgNumber': middlePgNumber})
        else:
            new_pgNumber = 2 if pgNumber == 0 else pgNumber * 2
            yield scrapy.Request(url=obitPageURL, method='POST', body=self.build_payload(fhid, new_pgNumber),
                                 headers=self.build_headers(base_url, include_referer=True), callback=self.get_bounds,
                                 cb_kwargs={'fhid': fhid, 'obitPageURL': obitPageURL, 'pgNumber': new_pgNumber})

    def get_last_page(self, response, fhid, obitPageURL, upperBound, lowerBound, middlePgNumber):
        pastLastPageIndicator = response.css(".bg-info").get()
        base_url = "{}://{}".format(urlparse(response.url).scheme, urlparse(response.url).netloc)

        self.logger.info(f"Checking page {middlePgNumber}, bounds {lowerBound}, {upperBound}")

        if pastLastPageIndicator:
            upperBound = middlePgNumber
            middlePgNumber = (upperBound + lowerBound) // 2
            yield scrapy.Request(url=obitPageURL, method='POST', body=self.build_payload(fhid, middlePgNumber),
                                 headers=self.build_headers(base_url, include_referer=True), callback=self.get_last_page,
                                 cb_kwargs={'fhid': fhid, 'obitPageURL': obitPageURL, 'upperBound': upperBound,
                                            'lowerBound': lowerBound, 'middlePgNumber': middlePgNumber})
        else:
            obitCount = len(response.css('.row.pad-light').getall())
            if obitCount < 10:
                self.logger.info(f"Last page found: {middlePgNumber}")
                obitCount += middlePgNumber * 10
                base_url = "{}://{}".format(urlparse(response.url).scheme, urlparse(response.url).netloc)
                yield {'url': base_url, 'obitCount': obitCount}
            else:
                lowerBound = middlePgNumber
                middlePgNumber = (upperBound + lowerBound) // 2
                yield scrapy.Request(url=obitPageURL, method='POST', body=self.build_payload(fhid, middlePgNumber),
                                     headers=self.build_headers(base_url, include_referer=True), callback=self.get_last_page,
                                     cb_kwargs={'fhid': fhid, 'obitPageURL': obitPageURL, 'upperBound': upperBound,
                                                'lowerBound': lowerBound, 'middlePgNumber': middlePgNumber})

    def build_payload(self, fhid, pgNumber):
        return f"pg={pgNumber}&term=&paginate=1&ym=0&showmiddlename=0&listcity=0&tgt=obitlist&numlistings=10&sids={fhid}&typ=1&txtsrch=0"

    def build_headers(self, base_url, include_content_type=True, include_referer=False):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }
        if include_content_type:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        if include_referer:
            headers['Referer'] = urljoin(base_url, '/listings')
        return headers