import scrapy
import logging
from scrapy.utils.log import configure_logging
from urllib.parse import urljoin

class ttObitCounter(scrapy.Spider):
    configure_logging(install_root_handler=False)
    logging.basicConfig(
        filename='log.txt',
        format='%(levelname)s: %(message)s',
        level=logging.INFO
    )

    name = 'ttCounter'
    urls = ['']

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }

    def start_requests(self):
        for url in self.urls:
            fullURL = urljoin(url, '/obituaries/obituary-listings')
            self.logger.info(f"URL: {fullURL}")
            yield scrapy.Request(url=fullURL, headers=self.headers, callback=self.get_domainID)

    def get_domainID(self, response):
        pageScripts = response.css('script::text').getall()
        domainID = None
        pgNumber = 1

        for script in pageScripts:
            if "API.domainId =" in script:
                domainID = script.split("API.domainId = '")[1].split("'")[0]
                break
        
        if domainID:
            self.logger.info(f"Domain ID found: {domainID}")
            url = response.urljoin(f"/ObituariesHelper/ObituariesListPagedItems")
            payload = f"PageSize=100&FirstPageObituariesCount=0&ObDomainId={domainID}&CurrentPage={pgNumber}&SearchText=&SortingColumn=3&Dates=0&SelectedLocationId=&HasNextPage=True&X-Requested-With=XMLHttpRequest"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
            }
            self.logger.info(f"URL: {url}")
            yield scrapy.Request(url=url,
                                 method='POST',
                                 body=payload,
                                 headers=headers,
                                 callback=self.get_bounds,
                                 cb_kwargs={'domainID': domainID,
                                             'headers': headers,
                                             'obitPageURL': url,
                                             'pgNumber': pgNumber})

        else:
            self.logger.error("Domain ID not found")
            return
        
    def get_bounds(self, response, domainID, headers, obitPageURL, pgNumber):
        obitCount = len(response.css('.obituary').getall())

        if obitCount == 0:
            self.logger.info(f"Past last page: {pgNumber}")
            upperBound = pgNumber
            lowerBound = pgNumber // 2
            middlePgNumber = (upperBound + lowerBound) // 2
            self.logger.info(f"Upper Bound: {upperBound}, Lower Bound: {lowerBound}, Middle Page Number: {middlePgNumber}")

            payload = f"PageSize=100&FirstPageObituariesCount=0&ObDomainId={domainID}&CurrentPage={middlePgNumber}&SearchText=&SortingColumn=3&Dates=0&SelectedLocationId=&HasNextPage=True&X-Requested-With=XMLHttpRequest"
            yield scrapy.Request(url=obitPageURL,
                                 method='POST',
                                 body=payload,
                                 headers=headers,
                                 callback=self.find_last_page,
                                 cb_kwargs={'lowerBound': lowerBound,
                                            'upperBound': upperBound,
                                            'middlePgNumber': middlePgNumber,
                                            'domainID': domainID,
                                            'headers': headers,
                                            'obitPageURL': obitPageURL})
            
        elif obitCount < 50:
            self.logger.info(f"Found last page: {pgNumber}")
            obitCount = (pgNumber - 1) * 50 + obitCount
            yield {
                'url': response.url,
                'obitCount': obitCount
            }
            
        else:
            self.logger.info(f"Not far enough yet: {pgNumber}")
            pgNumber = pgNumber * 2
            payload = f"PageSize=100&FirstPageObituariesCount=0&ObDomainId={domainID}&CurrentPage={pgNumber}&SearchText=&SortingColumn=3&Dates=0&SelectedLocationId=&HasNextPage=True&X-Requested-With=XMLHttpRequest"
            yield scrapy.Request(url=obitPageURL,
                                 method='POST',
                                 body=payload,
                                 headers=headers,
                                 callback=self.get_bounds,
                                 cb_kwargs={'domainID': domainID,
                                            'headers': headers,
                                            'obitPageURL': obitPageURL,
                                            'pgNumber': pgNumber})


    def find_last_page(self, response, lowerBound, upperBound, middlePgNumber, domainID, headers, obitPageURL):
        obitCount = len(response.css('.obituary').getall())

        if not obitCount:
            self.logger.info(f"Went too far: {middlePgNumber}")
            upperBound = middlePgNumber
            middlePgNumber = (upperBound + lowerBound) // 2

            self.logger.info(f"Upper Bound: {upperBound}, Lower Bound: {lowerBound}, Middle Page Number: {middlePgNumber}")
            payload = f"PageSize=100&FirstPageObituariesCount=0&ObDomainId={domainID}&CurrentPage={middlePgNumber}&SearchText=&SortingColumn=3&Dates=0&SelectedLocationId=&HasNextPage=True&X-Requested-With=XMLHttpRequest"
            yield scrapy.Request(url=obitPageURL,
                                    method='POST',
                                    body=payload,
                                    headers=headers,
                                    callback=self.find_last_page,
                                    cb_kwargs={'lowerBound': lowerBound,
                                                'upperBound': upperBound,
                                                'middlePgNumber': middlePgNumber,
                                                'domainID': domainID,
                                                'headers': headers,
                                                'obitPageURL': obitPageURL})

        elif obitCount < 50:
            self.logger.info(f"Found last page: {middlePgNumber}")
            obitCount = (middlePgNumber - 1) * 50 + obitCount
            yield {
                'url': response.url,
                'obitCount': obitCount
            }
            return

        elif obitCount == 50:
            self.logger.info(f"Not far enough: {middlePgNumber}")
            lowerBound = middlePgNumber
            middlePgNumber = (upperBound + lowerBound) // 2
            self.logger.info(f"Upper Bound: {upperBound}, Lower Bound: {lowerBound}, Middle Page Number: {middlePgNumber}")
            payload = f"PageSize=100&FirstPageObituariesCount=0&ObDomainId={domainID}&CurrentPage={middlePgNumber}&SearchText=&SortingColumn=3&Dates=0&SelectedLocationId=&HasNextPage=True&X-Requested-With=XMLHttpRequest"
            yield scrapy.Request(url=obitPageURL,
                                    method='POST',
                                    body=payload,
                                    headers=headers,
                                    callback=self.find_last_page,
                                    cb_kwargs={'lowerBound': lowerBound,
                                                'upperBound': upperBound,
                                                'middlePgNumber': middlePgNumber,
                                                'domainID': domainID,
                                                'headers': headers,
                                                'obitPageURL': obitPageURL})
