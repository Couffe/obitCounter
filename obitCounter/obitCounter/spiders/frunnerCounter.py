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
    urls = ['']