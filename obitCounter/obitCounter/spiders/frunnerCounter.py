import scrapy
import logging
import json
from scrapy.utils.log import configure_logging
from urllib.parse import urljoin

class f1ObitCounter(scrapy.Spider):
    configure_logging(install_root_handler=False)
    logging.basicConfig(
        filename='log.txt',
        format='%(levelname)s: %(message)s',
        level=logging.INFO
    )

    name = 'frunnerCounter'
    urls = ['https://www.burrier-queen.com']

    #Testing site URL: https://www.swedberg-taylor.com/ guid: MzA3OTA4Ok1haW5TaXRl
    #Testing site with memorials subdomain: https://www.burrier-queen.com guid: MTc5NzUzOk1haW5TaXRl
    #Obituary URL: https://obituaries.frontrunnerpro.com/runtime/311039/ims/WF2/public/get-records-additional.php
    #pageNum=10&type=all&template=below&getServiceType=shiva&sort=dod&guid=MzA3OTA4Ok1haW5TaXRl&wholeSite=true
    #pageNum=64&rpp=100&type=all&template=below&getServiceType=shiva&sort=dod&guid=MzA3OTA4Ok1haW5TaXRl&wholeSite=true
    #getting stuck on page 101
    """
    headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
        }
        """
    
    def start_requests(self):
        for url in self.urls:
            fullURL = urljoin(url, '/obituary-listing')
            self.logger.info(f"URL: {fullURL}")
            yield scrapy.Request(url=fullURL, 
                                 headers=self.build_headers(url, includeContentType=False, includeReferer=False), 
                                 callback=self.get_guid, 
                                 cb_kwargs={'baseURL': url})

    def get_guid(self, response, baseURL):
        pageScripts = response.css('script::text').getall()
        guid = None

        for script in pageScripts:
            if "ExternalUid:" in script:
                guid = script.split("ExternalUid: '")[1].split("'")[0]
                self.logger.info(f"guid: {guid}")
                break

        if guid:
            pgNum = 1
            obitURL = 'https://obituaries.frontrunnerpro.com/runtime/311039/ims/WF2/public/get-records-additional.php'
            yield scrapy.Request(url=obitURL,
                                 method='POST',
                                 body=self.build_payload(pgNum, guid),
                                 headers=self.build_headers(baseURL, includeContentType=True, includeReferer=True),
                                 callback=self.get_bounds,
                                 cb_kwargs={'guid': guid,
                                            'obitURL': obitURL,
                                            'pgNum': pgNum,
                                            'baseURL': baseURL})

        else:
            self.logger.error("GUID not found")
            return
        
    def get_bounds(self, response, guid, obitURL, pgNum, baseURL, defPageObitCount=None):
        try:
            json_data = response.json()
            maxPgNum = json_data.get('maxPageNum', None)
            obits = json_data.get('data', [])

            if maxPgNum is not None:
                self.logger.info(f"Max Page Number: {maxPgNum}")
                if pgNum == maxPgNum:
                    self.logger.info(f"Found last page {pgNum}")
                    obitCount = len(obits)
                    yield {
                        'url': baseURL,
                        'obitCount': obitCount
                    }
                    return
                else:
                    self.logger.info(f"Requesting last page {maxPgNum}")
                    yield scrapy.Request(url=obitURL,
                                         method='POST',
                                         body=self.build_payload(maxPgNum, guid),
                                         headers=self.build_headers(baseURL, includeContentType=True, includeReferer=True),
                                         callback=self.req_last_page,
                                         cb_kwargs={'guid': guid,
                                                    'obitURL': obitURL,
                                                    'pgNum': maxPgNum,
                                                    'baseURL': baseURL})
            
        except ValueError:
            self.logger.info(f'Past Last Page: {pgNum}')
            lowerBound = pgNum // 2
            middlePgNum = (pgNum + lowerBound) // 2
            self.logger.info(f"Lower Bound: {lowerBound}, Middle Bound: {middlePgNum}, Upper Bound: {pgNum}")
            yield scrapy.Request(url=obitURL,
                                 method='POST',
                                 body=self.build_payload(middlePgNum, guid),
                                 headers=self.build_headers(baseURL, includeContentType=True, includeReferer=True),
                                 callback=self.find_last_page,
                                 cb_kwargs={'guid': guid,
                                            'obitURL': obitURL,
                                            'lowerBound': lowerBound,
                                            'middlePgNum': middlePgNum,
                                            'upperBound': pgNum,
                                            'baseURL': baseURL,
                                            'defPageObitCount': defPageObitCount})
            return


        """if pgNum == 1:
            defPageObitCount = len(obits)
            self.logger.info(f"Page Obit Count: {defPageObitCount}")

        if len(obits) == defPageObitCount:
            self.logger.info(f"Not past last page: {pgNum}")
            pgNum *= 2
            yield scrapy.Request(url=obitURL,
                                 method='POST',
                                 body=self.build_payload(pgNum, guid),
                                 headers=self.build_headers(baseURL, includeContentType=True, includeReferer=True),
                                 callback=self.get_bounds,
                                 cb_kwargs={'guid': guid,
                                            'obitURL': obitURL,
                                            'pgNum': pgNum,
                                            'baseURL': baseURL,
                                            'defPageObitCount': defPageObitCount})
            
        elif (len(obits) < defPageObitCount):
                self.logger.info(f'Found last page {pgNum}')
                obitCount = (defPageObitCount * (pgNum - 1) + len(obits))
                yield {
                    'url': baseURL,
                    'obitCount': obitCount
                }"""
        
    def req_last_page(self, response, guid, obitURL, pgNum, baseURL):
        json_data = response.json()
        obits = json_data.get('data', [])

        obitCount = (100 * (pgNum - 1) + len(obits))
        yield {
            'url': baseURL,
            'obitCount': obitCount
        }

    def find_last_page(self, response, guid, obitURL, lowerBound, middlePgNum, upperBound, baseURL, defPageObitCount=None):
        try:
            json_data = response.json()
            obits = json_data.get('data', [])
        except ValueError:
            self.logger.info(f"Past last page: {middlePgNum}")
            upperBound = middlePgNum
            middlePgNum = (upperBound + lowerBound) // 2

            if (middlePgNum == lowerBound):
                self.logger.info(f"Found last page {middlePgNum}")
                obitCount = (defPageObitCount * (middlePgNum - 1) + len(obits))
                yield {
                    'url': baseURL,
                    'obitCount': obitCount
                }
                return

            self.logger.info(f"Lower Bound: {lowerBound}, Middle Bound: {middlePgNum}, Upper Bound: {upperBound}")
            yield scrapy.Request(url=obitURL,
                                 method='POST',
                                 body=self.build_payload(middlePgNum, guid),
                                 headers=self.build_headers(baseURL, includeContentType=True, includeReferer=True),
                                 callback=self.find_last_page,
                                 cb_kwargs={'guid': guid,
                                            'obitURL': obitURL,
                                            'lowerBound': lowerBound,
                                            'middlePgNum': middlePgNum,
                                            'upperBound': upperBound,
                                            'baseURL': baseURL,
                                            'defPageObitCount': defPageObitCount})
            return
            
        if (len(obits) == defPageObitCount):
            self.logger.info(f"Not far enough: {middlePgNum}")
            lowerBound = middlePgNum
            middlePgNum = (upperBound + lowerBound) // 2

            if (middlePgNum == lowerBound):
                self.logger.info(f"Found last page {middlePgNum}")
                obitCount = (defPageObitCount * (middlePgNum - 1) + len(obits))
                yield {
                    'url': baseURL,
                    'obitCount': obitCount
                }
                return
            
            self.logger.info(f"Lower Bound: {lowerBound}, Middle Bound: {middlePgNum}, Upper Bound: {upperBound}")
            yield scrapy.Request(url=obitURL,
                                 method='POST',
                                 body=self.build_payload(middlePgNum, guid),
                                 headers=self.build_headers(baseURL, includeContentType=True, includeReferer=True),
                                 callback=self.find_last_page,
                                 cb_kwargs={'guid': guid,
                                            'obitURL': obitURL,
                                            'lowerBound': lowerBound,
                                            'middlePgNum': middlePgNum,
                                            'upperBound': upperBound,
                                            'baseURL': baseURL,
                                            'defPageObitCount': defPageObitCount})
        elif (len(obits) < defPageObitCount):
            self.logger.info(f'Found last page {middlePgNum}')
            obitCount = (defPageObitCount * (middlePgNum - 1) + len(obits))
            yield {
                    'url': baseURL,
                    'obitCount': obitCount
                }

    def build_headers(self, baseURL, includeContentType = True, includeReferer = True):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }
        if includeContentType:
            headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
        if includeReferer:
            headers['Referer'] = urljoin(baseURL, '/obituary-listing')
        return headers
    
    def build_payload(self, pgNum, guid):
        return f'pageNum={pgNum}&rpp=100&type=all&template=below&getServiceType=shiva&sort=dod&guid={guid}&wholeSite=true'