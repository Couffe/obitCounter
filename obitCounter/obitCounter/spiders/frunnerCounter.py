import scrapy
import logging
import json
from scrapy.utils.log import configure_logging
from urllib.parse import urljoin, urlparse

class f1ObitCounter(scrapy.Spider):
    configure_logging(install_root_handler=False)
    logging.basicConfig(
        filename='log.txt',
        format='%(levelname)s: %(message)s',
        level=logging.INFO
    )

    name = 'frunnerCounter'
    
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
        
    def get_bounds(self, response, guid, obitURL, pgNum, baseURL):
        try:
            json_data = response.json()
            maxPgNum = json_data.get('maxPages', None)
            obits = json_data.get('data', [])

            if maxPgNum is not None:
                self.logger.info(f"Last Page Number: {maxPgNum}")
                if pgNum == maxPgNum:
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
                                         cb_kwargs={'pgNum': maxPgNum,
                                                    'baseURL': baseURL})
            else:
                self.logger.info(f"maxPages not found in response")
                return
            
        except ValueError:
            self.logger.error("Error parsing JSON response")
            self.logger.debug(f"Response body: {response.text}")
            return
        
    def req_last_page(self, response, pgNum, baseURL):
        json_data = response.json()
        obits = json_data.get('data', [])

        obitCount = (100 * (pgNum - 1) + len(obits))
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