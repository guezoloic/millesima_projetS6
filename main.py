from bs4 import BeautifulSoup
import requests as rq

def getsoup(s: str) -> BeautifulSoup:
    return BeautifulSoup(rq.get(s).text, 'html.parser')

def test_soup():
    assert getsoup("https://example.com").find('h1').text == "Example Domain" 

soup = getsoup("https://www.millesima.fr/")

def nimportequoi() :
    links = soup.find_all('a')
    for link in links:
        print(link.get('href'))         