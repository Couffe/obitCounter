import scrapy
import logging
from scrapy.utils.log import configure_logging
from urllib.parse import urljoin

class cfsObitCounter(scrapy.Spider):
    #Puts logs into a file
    configure_logging(install_root_handler=False)
    logging.basicConfig(
        filename='log.txt',
        format='%(levelname)s: %(message)s',
        level=logging.INFO
    )

    obitCount = 0
    pgNumber = 0

    name = 'cfsObitCounter'
    urls = ['https://www.lrbfh.com/']
    payload = f"pg={pgNumber}&term=&paginate=1&ym=0&showmiddlename=0&listcity=0&tgt=obitlist&numlistings=10&sids=12959&typ=1&txtsrch=0"

    headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }
    
    def start_requests(self):
        for url in self.urls:
            fullURL = urljoin(url, '/listings')
            self.logger.info(f"URL: {fullURL}")
            yield scrapy.Request(url=fullURL, headers=self.headers, callback=self.get_fhid)

    def get_fhid(self, response):
        #Get FHID from testimonial slider on homepage
        fhid = response.css('input[name="sids"]::attr(value)').get()

        if fhid:
            self.logger.info(f"FHID found: {fhid}")
            
            #Send to get_last_page
            payload = f"pg={self.pgNumber}&term=&paginate=1&ym=0&showmiddlename=0&listcity=0&tgt=obitlist&numlistings=10&sids={fhid}&typ=1&txtsrch=0"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            url = response.urljoin(f"/pax/obitsrch")

            self.logger.info(f"Payload: {payload}")
            yield scrapy.Request(url=url, 
                                method='POST', 
                                body=payload, 
                                headers=headers, 
                                callback=self.get_bounds,
                                cb_kwargs={'fhid': fhid,
                                            'headers': headers,
                                            'obitPageURL': url})
        else:
            self.logger.error("FHID not found")

    def get_bounds(self, response, fhid, headers, obitPageURL):
        #Check if we're past the last page
        lastPageIndicator = response.css(".bg-info").get()

        if (lastPageIndicator):
            self.logger.info("Past last page")
            upperBound = self.pgNumber
            lowerBound = self.pgNumber // 2
            middlePgNumber = (upperBound + lowerBound) // 2
            self.pgNumber = middlePgNumber
            payload = f"pg={middlePgNumber}&term=&paginate=1&ym=0&showmiddlename=0&listcity=0&tgt=obitlist&numlistings=10&sids={fhid}&typ=1&txtsrch=0"
            self.logger.info(f"Payload: {payload}")
            yield scrapy.Request(url=obitPageURL,
                                 method='POST',
                                 body=payload,
                                 headers=headers,
                                 callback=self.get_last_page,
                                 cb_kwargs={'headers': headers,
                                            'fhid': fhid,
                                            'obitPageURL': obitPageURL,
                                            'upperBound': upperBound,
                                            'lowerBound': lowerBound,
                                            'middlePgNumber': middlePgNumber})

            return
        else:
            #Multiply the page number by 2 then request again
            #If it's 0, set it to 2
            if (self.pgNumber == 0):
                self.pgNumber = 2
                payload = f"pg={self.pgNumber}&term=&paginate=1&ym=0&showmiddlename=0&listcity=0&tgt=obitlist&numlistings=10&sids={fhid}&typ=1&txtsrch=0"
                self.logger.info(f"Payload: {payload}")
                yield scrapy.Request(url=obitPageURL,
                                     method='POST',
                                     body=payload,
                                     headers=headers,
                                     callback=self.get_bounds,
                                     cb_kwargs={'fhid': fhid,
                                                'headers': headers,
                                                'obitPageURL': obitPageURL})
            else:
                self.pgNumber *= 2
                payload = f"pg={self.pgNumber}&term=&paginate=1&ym=0&showmiddlename=0&listcity=0&tgt=obitlist&numlistings=10&sids={fhid}&typ=1&txtsrch=0"
                self.logger.info(f"Payload: {payload}")
                yield scrapy.Request(url=obitPageURL,
                                     method='POST',
                                     body=payload,
                                     headers=headers,
                                     callback=self.get_bounds,
                                     cb_kwargs={'fhid': fhid,
                                                'headers': headers,
                                                'obitPageURL': obitPageURL})
                
    def get_last_page(self, response, fhid, headers, obitPageURL, upperBound, lowerBound, middlePgNumber):
        #Check if we're past the last page
        pastLastPageIndicator = response.css(".bg-info").get()

        self.logger.info(f"Checking page {middlePgNumber}, bounds {lowerBound}, {upperBound}")

        #If we are past the last page, set the upper bound to the middle page number
        if (pastLastPageIndicator):
            self.logger.info("Past last page")
            upperBound = middlePgNumber
            middlePgNumber = (upperBound + lowerBound) // 2
            self.pgNumber = middlePgNumber
            payload = f"pg={self.pgNumber}&term=&paginate=1&ym=0&showmiddlename=0&listcity=0&tgt=obitlist&numlistings=10&sids={fhid}&typ=1&txtsrch=0"
            yield scrapy.Request(url=obitPageURL,
                                 method='POST',
                                 body=payload,
                                 headers=headers,
                                 callback=self.get_last_page,
                                 cb_kwargs={'headers': headers,
                                            'fhid': fhid,
                                            'obitPageURL': obitPageURL,
                                            'upperBound': upperBound,
                                            'lowerBound': lowerBound,
                                            'middlePgNumber': middlePgNumber})
        #Check if we're on the last page
        else:
            obitCount = len(response.css('.row.pad-light').getall())

            if (obitCount < 10):
                self.logger.info(f"Last page found: {middlePgNumber}")
                obitCount = obitCount + (middlePgNumber * 10)
                self.logger.info(f"Obit count: {obitCount}")
                yield {
                    'url': response.url,
                    'obitCount': obitCount
                }
            else:
                self.logger.info(f"Not last page: {middlePgNumber}")
                lowerBound = middlePgNumber
                middlePgNumber = (upperBound + lowerBound) // 2
                self.pgNumber = middlePgNumber
                payload = f"pg={self.pgNumber}&term=&paginate=1&ym=0&showmiddlename=0&listcity=0&tgt=obitlist&numlistings=10&sids={fhid}&typ=1&txtsrch=0"
                yield scrapy.Request(url=obitPageURL,
                                     method='POST',
                                     body=payload,
                                     headers=headers,
                                     callback=self.get_last_page,
                                     cb_kwargs={'fhid': fhid,
                                                'headers': headers,
                                                'obitPageURL': obitPageURL,
                                                'upperBound': upperBound,
                                                'lowerBound': lowerBound,
                                                'middlePgNumber': middlePgNumber})