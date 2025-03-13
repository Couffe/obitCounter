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
    urls = ['https://www.swedberg-taylor.com/']

    #Testing site URL: https://www.swedberg-taylor.com/
    #Testing site with memorials subdomain: https://www.burrier-queen.com
    #Obituary URL: https://obituaries.frontrunnerpro.com/runtime/311039/ims/WF2/public/get-records-additional.php
    #payload: pageNum=10&rpp=6&width=159.6&height=186.78555&type=all&template=below&getServiceType=shiva&sort=dod&guid=MzA3OTA4Ok1haW5TaXRl&wholeSite=true
    """
    headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
        }
    Using this request returns a json file, that has all the obit info. Can traverse by doubling page number until we're past last page which
    will be a json that says invalid page number.

    Need to get guid from the page in order to make request
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
            payload = f'pageNum={pgNum}&rpp=6&width=159.6&height=186.78555&type=all&template=below&getServiceType=shiva&sort=dod&guid={guid}&wholeSite=true'
            yield scrapy.Request(url=obitURL,
                                 method='POST',
                                 body=payload,
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
            obits = json_data.get('data', [])
        except json.JSONDecodeError:
            self.logger.info(f'Past Last Page: {pgNum}')
            lowerBound = pgNum // 2
            middlePgNum = (pgNum + lowerBound) // 2
            self.logger.info(f"Lower Bound: {lowerBound}, Middle Bound: {middlePgNum}, Upper Bound: {pgNum}")
            payload = f'pageNum={middlePgNum}&rpp=6&width=159.6&height=186.78555&type=all&template=below&getServiceType=shiva&sort=dod&guid={guid}&wholeSite=true'
            yield scrapy.Request(url=obitURL,
                                 method='POST',
                                 body=payload,
                                 headers=self.build_headers(baseURL, includeContentType=True, includeReferer=True),
                                 callback=self.find_last_page,
                                 cb_kwargs={'guid': guid,
                                            'obitURL': obitURL,
                                            'lowerBound': lowerBound,
                                            'middlePgNum': middlePgNum,
                                            'upperBound': pgNum,
                                            'baseURL': baseURL})

        if pgNum == 1:
            defPageObitCount = len(obits)
            self.logger.info(f"Page Obit Count: {defPageObitCount}")

        if len(obits) == defPageObitCount:
            self.logger.info(f"Not past last page: {pgNum}")
            pgNum *= 2
            payload = f'pageNum={pgNum}&rpp=6&width=159.6&height=186.78555&type=all&template=below&getServiceType=shiva&sort=dod&guid={guid}&wholeSite=true'
            yield scrapy.Request(url=obitURL,
                                 method='POST',
                                 body=payload,
                                 headers=self.build_headers(baseURL, includeContentType=True, includeReferer=True),
                                 callback=self.get_bounds,
                                 cb_kwargs={'guid': guid,
                                            'obitURL': obitURL,
                                            'pgNum': pgNum,
                                            'baseURL': baseURL,
                                            'defPageObitCount': defPageObitCount})

    def find_last_page(self, response, guid, obitURL, lowerBound, middlePgNum, upperBound, baseURL):
        try:
            json_data = response.json()
            obits = json_data.get('data', [])
        except json.JSONDecodeError:
            self.logger.info(f"Past last page: {middlePgNum}")
            upperBound = middlePgNum
            middlePgNum = (upperBound + lowerBound) // 2
            self.logger.info(f"Lower Bound: {lowerBound}, Middle Bound: {middlePgNum}, Upper Bound: {upperBound}")
            payload = f'pageNum={middlePgNum}&rpp=6&width=159.6&height=186.78555&type=all&template=below&getServiceType=shiva&sort=dod&guid={guid}&wholeSite=true'
            yield scrapy.Request(url=obitURL,
                                 method='POST',
                                 body=payload,
                                 headers=self.build_headers(baseURL, includeContentType=True, includeReferer=True),
                                 callback=self.find_last_page,
                                 cb_kwargs={'guid': guid,
                                            'obitURL': obitURL,
                                            'lowerBound': lowerBound,
                                            'middlePgNum': middlePgNum,
                                            'upperBound': upperBound,
                                            'baseURL': baseURL})

    def build_headers(self, baseURL, includeContentType = True, includeReferer = True):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }
        if includeContentType:
            headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
        if includeReferer:
            headers['Referer'] = urljoin(baseURL, '/obituary-listing')
        return headers