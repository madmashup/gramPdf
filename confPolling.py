from urllib.parse import urljoin

baseUrl = 'http://www.ceo.kerala.gov.in'
# baseUrl = "https://web.archive.org/web/20141218145328/http://www.ceo.kerala.gov.in"
pollingStationsUrl = urljoin(baseUrl,'pollingstations.html')
baseLink = "http://www.ceo.kerala.gov.in/pdf/POLLINGSTATION/"

downloadDir = "pollingStations2017"

searchHeaders = {
  'Accept': 'application/json, text/javascript, */*',
  'Accept-Encoding': 'gzip, deflate, sdch',
  'Accept-Language': 'en-US,en;q=0.5',
  'Connection': 'keep-alive',
  'Content-Type': 'application/x-www-form-urlencoded',
  'DNT': '1',
  'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0'
}

sessionHeaders = {
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
  'Accept-Encoding': 'gzip, deflate',
  'Accept-Language': 'en-US,en;q=0.5',
  'Connection': 'keep-alive',
  'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0'
}
