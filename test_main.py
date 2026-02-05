from main import Scraper


def test_soup():
    assert Scraper().getsoup().find('h1')\
        .text[3:12] == "MILLESIMA"


def test_getProductName():
    assert Scraper("chateau-gloria-2016.html").get_json_data()['productName']\
        == "Château Gloria 2016"
