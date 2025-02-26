import scrapy
import logging
from scrapy.utils.log import configure_logging

#Get's the obituary count for all Batesville sites, new or old layout
class bvilleObitCounter(scrapy.Spider):
    #Puts logs into a file
    configure_logging(install_root_handler=False)
    logging.basicConfig(
        filename='log.txt',
        format='%(levelname)s: %(message)s',
        level=logging.INFO
    )

    name = 'bvilleObitCounter'

    headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }
    
    urls = ['https://www.cremationsocietyofvt.com/']

    obitCount = 0

    def start_requests(self):
        #Sends request to URL to get the obituary page link
        for url in self.urls:
            yield scrapy.Request(url=url, 
                                callback=self.getObitPage, 
                                headers=self.headers, 
                                cb_kwargs={'url': url})

    #Gets obit count for the old Batesville layout
    def getObitCount(self, response):
        #Finds the total obituary count from the obit widget
        obitCount = int(response.css('#total-records::text').get())
        if obitCount:
            self.logger.info(f"Obituary count: {obitCount}")
            #Returns the URL and obituary count
            yield {
                'url': response.url,
                'obitCount': obitCount
            }
        else:
            self.logger.info("No obituary count found") 
            yield {
                'url': response.url,
                'obitCount': "No obituary count found"
            }

    #Gets the obituary page link
    def getObitPage(self, response, url):
        #Finds the obituary page link from the header
        obitPageLink = None
        headerA = response.css('#mobile-nav .list-inline a').getall()

        for a in headerA:
            if "Obituaries" in a:
                obitPageLink = a.split('href="')[1].split('"')[0]
                break

        #If it finds the obit link sends a request to the obit page loading JS
        if obitPageLink:
            self.logger.info('Obituary page URL found: ' + obitPageLink)
            yield scrapy.Request(url=obitPageLink, callback=self.getObitCount, headers=self.headers, meta={'playwright': True})
        else:
            #Can't find the obituary page link, try the new layout
            self.logger.info("No obituary page URL found")
            #Pulls all the scripts from the page
            pageScripts = response.css('script::text').getall()
            fhID = None

            #Iterates through to find where the fhID is stored
            for script in pageScripts:
                if "var fhID =" in script:
                    fhID = script.split('var fhID = "')[1].split('"')[0]
                    break
            
            if not fhID:
                self.logger.error("fhID not found, can't proceed.")
                yield {
                    'url': url,
                    'obitCount': "Can't find fhID"
                }
                return

            self.logger.info(f"fhID: {fhID}")
            pageNumber = 1
            newObitPageLink = f"{url}/obituaries/paging?fh_id={fhID}&sort_by=all&page_number={pageNumber}"

            #Sends scrapy requests to each page until we get the last page that has less than 20 obits
            yield scrapy.Request(url=newObitPageLink, 
                                 callback=self.findBounds, 
                                 headers=self.headers, 
                                 cb_kwargs={'pageNumber': pageNumber, 
                                            'fhID': fhID,
                                            'firstObitSlug': None,
                                            'url': url})
            

    #Everything below is for the new Batesville layout
    #Finds the bounds of the last page by doubling the iteration each time
    #For example page 1, then 2, 4, 8, 16...
    #Until it goes past the last page and uses the iteration before as the lowerBound
    #and the latest iteration as the upperBound and passes it to findLastPage
    def findBounds(self, response, pageNumber, fhID, firstObitSlug, url):
        #First checks page number to see if we need to pull the first obit slug
        if pageNumber == 1:
            #Check if first page has less than 20 obits then yield count if so
            pageObitCount = len(response.css(".obit-item").getall())
            if pageObitCount < 20:
                self.logger.info(f"Last page found: {pageNumber}")
                yield {
                    'url': url,
                    'obitCount': pageObitCount
                }
                return

            firstObitSlug = response.css(".sitelink::attr(href)").get()

            #Continue looking, call findLastPage again after doubling the page number
            pageNumber *= 2
            obitPageLink = f"{url}/obituaries/paging?fh_id={fhID}&sort_by=all&page_number={pageNumber}"
            yield scrapy.Request(url=obitPageLink, 
                                 callback=self.findBounds, 
                                 headers=self.headers, 
                                 cb_kwargs={'pageNumber': pageNumber, 
                                            'fhID': fhID, 
                                            'firstObitSlug': firstObitSlug,
                                            'url': url})
        else:
            #Gets slug of first obit on page and compares it to the original firstObitSlug
            pageFirstObitSlug = response.css(".sitelink::attr(href)").get()
            if firstObitSlug == pageFirstObitSlug:
                #If they're equal we've passed the last page
                self.logger.info(f"Went too far page: {pageNumber}")

                #Sets bounds and finds middle page
                lowerBound = pageNumber // 2
                upperBound = pageNumber
                middlePageNumber = (lowerBound + upperBound) // 2
                
                #Creates the link for the middle page and sends a request to findLastPage which is a binary search
                middlePageLink = f"{url}/obituaries/paging?fh_id={fhID}&sort_by=all&page_number={middlePageNumber}"
                yield scrapy.Request(url=middlePageLink, 
                                     callback=self.findLastPage, 
                                     headers=self.headers, 
                                     cb_kwargs={'lowerBound': lowerBound, 
                                                'upperBound': upperBound, 
                                                'middlePageNumber': middlePageNumber, 
                                                'firstObitSlug': firstObitSlug, 
                                                'fhID': fhID,
                                                'url': url})
                
            #If they're not equal we need to keep looking
            else:
                pageNumber *= 2
                obitPageLink = f"{url}/obituaries/paging?fh_id={fhID}&sort_by=all&page_number={pageNumber}"
                yield scrapy.Request(url=obitPageLink, 
                                     callback=self.findBounds, 
                                     headers=self.headers, 
                                     cb_kwargs={'pageNumber': pageNumber, 
                                                'fhID': fhID, 
                                                'firstObitSlug': firstObitSlug,
                                                'url': url})

    #Does a binary search on the bounds that were sent from findBouds to find
    #what the last page is. Know's it's the last page if there are < 20 obits on the page
    #or when bounds converge (assuming last page has 20 obits)
    def findLastPage(self, response, lowerBound, upperBound, middlePageNumber, firstObitSlug, fhID, url):
        pageFirstObitSlug = response.css(".sitelink::attr(href)").get()

        # Debug log
        self.logger.info(f"Checking page {middlePageNumber}, bounds: ({lowerBound}, {upperBound})")

        # If the obit slug is the same as the first, we've gone too far -> Adjust upperBound
        if firstObitSlug == pageFirstObitSlug:
            self.logger.info(f"Went too far at {middlePageNumber}, adjusting upperBound")
            upperBound = middlePageNumber  # Adjust upper bound
        else:
            # First check if this is the last page (less than 20 obits)
            pageObitCount = len(response.css(".obit-item").getall())
            if pageObitCount < 20:
                self.logger.info(f"Last page found: {middlePageNumber}")
                finalObitCount = ((middlePageNumber - 1) * 20) + pageObitCount
                yield {
                    'url': url,
                    'obitCount': finalObitCount
                }
                return  # Stop further execution
            
            # Otherwise, update lowerBound
            self.logger.info(f"Page {middlePageNumber} is valid, adjusting lowerBound")
            lowerBound = middlePageNumber

        # Stop when bounds converge
        if upperBound - lowerBound == 1:
            self.logger.info(f"Final last page: {lowerBound}")
            yield {
                'url': url,
                'obitCount': lowerBound * 20
            }
            return  # Stop further execution

        # Continue binary search
        middlePageNumber = (lowerBound + upperBound) // 2
        middlePageLink = f"{url}/obituaries/paging?fh_id={fhID}&sort_by=all&page_number={middlePageNumber}"
        
        self.logger.info(f"Next request: Page {middlePageNumber} (bounds: {lowerBound}, {upperBound})")
        
        yield scrapy.Request(
            url=middlePageLink, 
            callback=self.findLastPage, 
            headers=self.headers, 
            cb_kwargs={
                'lowerBound': lowerBound,
                'upperBound': upperBound,
                'middlePageNumber': middlePageNumber,
                'firstObitSlug': firstObitSlug,
                'fhID': fhID,
                'url': url
            })