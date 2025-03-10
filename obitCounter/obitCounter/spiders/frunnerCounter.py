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
    #Obituary URL: https://obituaries.frontrunnerpro.com/runtime/311039/ims/WF2/public/get-records-additional.php
    #payload: pageNum=1&rpp=6&width=159.6&height=186.78555&type=all&template=below&getServiceType=shiva&sort=dod&guid=MzA3OTA4Ok1haW5TaXRl&wholeSite=true
    """
    headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }
        """