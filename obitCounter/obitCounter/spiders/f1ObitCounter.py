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

    name = 'f1ObitCounter'
    urls = ['https://www.poseyfuneraldirectors.com/']

    #url = 'https://www.owenfuneralhome.com/obituaries/api/search.json'
    #payload = 'orderBy=DeathDate&pageSize=12&pageNumber=1'
    #headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'Referer': 'https://www.owenfuneralhome.com/obituaries/', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}

    def start_requests(self):
        for url in self.urls:
            refURL = urljoin(url, '/obituaries/')
            self.logger.info(f"URL: {refURL}")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': refURL,
                'X-Requested-With': 'XMLHttpRequest'
            }

            fullURL = urljoin(url, '/obituaries/api/search.json')
            payload = 'orderBy=DeathDate&pageSize=12&pageNumber=1'
            self.logger.info(f"URL: {fullURL}")
            yield scrapy.Request(url=fullURL, 
                                method='POST',
                                body=payload,
                                headers=headers,
                                callback=self.get_obit_count)

    def get_obit_count(self, response):
        data = json.loads(response.text)

        obitCount = data.get("totalRecords", 0)
        self.logger.info(f"Obituary count: {obitCount}")
        yield {
            'url': response.url,
            'obitCount': obitCount
        }