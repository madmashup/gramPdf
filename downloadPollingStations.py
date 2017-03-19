import confPolling as conf
import datetime, time
import string

from scraper import Scraper
from bs4 import BeautifulSoup as BS



def main():

  DEBUG = True
#  while datetime.datetime.now().time() < datetime.time(2, 30):
#    print "Sleeping for 300 secs"
#    time.sleep(300)
  print( "== Starting Download ==")
  startTime = datetime.datetime.now()
  

  # baseUrl = "https://web.archive.org/web/20111116000710/http://www.ceo.kerala.gov.in"
  # baseLink = "https://web.archive.org/web/20111116000710/http://www.ceo.kerala.gov.in/pdf/POLLINGSTATION/"
  # downloadDir = "pollingStations2011"
  # baseUrl = "http://www.ceo.kerala.gov.in"

  # Setup the session
  scp = Scraper(conf.sessionHeaders, conf.searchHeaders, [conf.baseUrl])
  scp.setup_session()
  resp = scp.get_response(conf.pollingStationsUrl, '', 1)
  # print(resp.text.encode('utf8'))
  
  page = resp.text
  # page = open('detailedResults.html', 'r')

  # Parse the html with bs4 using the "html.parser"
  soup = BS(page, 'html.parser')
  

  pdfNames = [("AC%03d.pdf" % num) for num in range(27,39)]

##  Process the HTML to find the District dropdown list
#  options = soup.find_all("a")
#  for tag in options:
#    
#    if hasattr(tag, "href"):
#      href = tag.get("href", "None")
#    else:
#      continue
#      
#    # If the href contains the string that says it's the pdf 
#    if href.find("POLLINGSTATION/AC") != -1:

  for fn in pdfNames:
    
    downLink = conf.baseLink + fn

    # Download the links that have polling station pdfs
    downFileName = conf.downloadDir + "/" + fn
    #      keyf.write("{},{}{}".format(lacName, downFileName, "\n"))
    if DEBUG:
      print("Downloading file %s from link: %s" % (downFileName, downLink))
    scp.downloadFile(downLink, downFileName)
    time.sleep(2)

    
  endtime = datetime.datetime.now()
  
  print("Script running time : %f seconds" % (endtime - startTime).total_seconds())

  
if __name__ == "__main__":
  # execute only if run as a script
  main()

