from json import dumps
from bs4 import Tag
import pytest
from requests_mock import Mocker
from main import Scraper


@pytest.fixture(autouse=True)
def mock_site():
    with Mocker() as m:
        m.get(
            "https://www.millesima.fr/",
            text=f"""
            <html>
                <body>
                    <script id="__NEXT_DATA__" type="application/json">
                    {dumps({
                        "props": {
                            "pageProps": {
                                "initialReduxState": {
                                    "product": {
                                        "content": {
                                            "items": [],
                                            "attributes": {}
                                        }
                                    }
                                }
                            }
                        }
                    })}
                    </script>
                </body>
            </html>
            """,
        )

        m.get(
            "https://www.millesima.fr/poubelle",
            text=f"""
            <html>
                <body>
                    <h1>POUBELLE</h1>
                    <script id="__NEXT_DATA__" type="application/json">
                    {dumps({
                        "props": {
                            "pageProps": {
                            }
                        }
                    })}
                    </script>
                </body>
            </html>
            """,
        )

        json_data = {
            "props": {
                "pageProps": {
                    "initialReduxState": {
                        "product": {
                            "content": {
                                "_id": "J4131/22-11652",
                                "partnumber": "J4131/22",
                                "productName": "Nino Negri : 5 Stelle Sfursat 2022",
                                "productNameForSearch": "Nino Negri : 5 Stelle Sfursat 2022",
                                "storeId": "11652",
                                "seoKeyword": "nino-negri-5-stelle-sfursat-2022.html",
                                "title": "Nino Negri : 5 Stelle Sfursat 2022",
                                "items": [
                                    {
                                        "_id": "J4131/22/C/CC/6-11652",
                                        "partnumber": "J4131/22/C/CC/6",
                                        "taxRate": "H",
                                        "listPrice": 390,
                                        "offerPrice": 390,
                                        "seoKeyword": "nino-negri-5-stelle-sfursat-2022-c-cc-6.html",
                                        "shortdesc": "Un carton de 6 Bouteilles (75cl)",
                                        "attributes": {
                                            "promotion_o_n": {
                                                "valueId": "0",
                                                "name": "En promotion",
                                                "value": "Non",
                                                "sequence": 80,
                                                "displayable": "False",
                                                "type": "CHECKBOX",
                                                "isSpirit": False,
                                            },
                                            "in_stock": {
                                                "valueId": "L",
                                                "name": "En stock",
                                                "value": "Livrable",
                                                "sequence": 65,
                                                "displayable": "true",
                                                "type": "CHECKBOX",
                                                "isSpirit": False,
                                            },
                                            "equivbtl": {
                                                "valueId": "1",
                                                "name": "equivbtl",
                                                "value": "1",
                                                "isSpirit": False,
                                            },
                                            "nbunit": {
                                                "valueId": "6",
                                                "name": "nbunit",
                                                "value": "6",
                                                "isSpirit": False,
                                            },
                                        },
                                        "stock": 12,
                                        "availability": "2026-02-05",
                                        "isCustomizable": False,
                                        "gtin_cond": "",
                                        "gtin_unit": "",
                                        "stockOrigin": "EUR",
                                        "isPrevSale": False,
                                    }
                                ],
                                "attributes": {
                                    "appellation": {
                                        "valueId": "433",
                                        "name": "Appellation",
                                        "value": "Sforzato di Valtellina",
                                        "url": "sforzato-di-valtellina.html",
                                        "isSpirit": False,
                                        "groupIdentifier": "appellation_433",
                                    },
                                    "note_rp": {
                                        "valueId": "91",
                                        "name": "Parker",
                                        "value": "91",
                                        "isSpirit": False,
                                    },
                                    "note_jr": {
                                        "valueId": "17+",
                                        "name": "J. Robinson",
                                        "value": "17+",
                                        "isSpirit": False,
                                    },
                                    "note_js": {
                                        "valueId": "93-94",
                                        "name": "J. Suckling",
                                        "value": "93-94",
                                        "isSpirit": False,
                                    },
                                },
                            }
                        }
                    }
                }
            }
        }

        html_product = f"""
        <html>
            <body>    
                <h1>MILLESIMA</h1>
                <script id="__NEXT_DATA__" type="application/json">
                    {dumps(json_data)}
                </script>
            </body>
        </html>
        """
        m.get(
            "https://www.millesima.fr/nino-negri-5-stelle-sfursat-2022.html",
            text=html_product,
        )

        # on return m sans fermer le server qui simule la page
        yield m


@pytest.fixture
def scraper() -> Scraper:
    return Scraper()


def test_soup(scraper: Scraper):
    vide = scraper.getsoup("")
    poubelle = scraper.getsoup("poubelle")
    contenu = scraper.getsoup("nino-negri-5-stelle-sfursat-2022.html")
    assert vide.find("h1") is None
    assert str(poubelle.find("h1")) == "<h1>POUBELLE</h1>"
    assert str(contenu.find("h1")) == "<h1>MILLESIMA</h1>"


def test_appellation(scraper: Scraper):
    vide = scraper.getjsondata("")
    poubelle = scraper.getjsondata("poubelle")
    contenu = scraper.getjsondata("nino-negri-5-stelle-sfursat-2022.html")
    assert vide.appellation() is None
    assert poubelle.appellation() is None
    assert contenu.appellation() == "Sforzato di Valtellina"


def test_fonctionprivee(scraper: Scraper):
    vide = scraper.getjsondata("")
    poubelle = scraper.getjsondata("poubelle")
    contenu = scraper.getjsondata("nino-negri-5-stelle-sfursat-2022.html")
    assert vide._getattributes() is not None
    assert vide._getattributes() == {}
    assert vide._getcontent() is not None
    assert vide._getcontent() == {"items": [], "attributes": {}}
    assert poubelle._getattributes() is None
    assert poubelle._getcontent() is None
    assert contenu._getcontent() is not None
    assert contenu._getattributes() is not None



def test_critiques(scraper: Scraper):
    vide = scraper.getjsondata("")
    poubelle = scraper.getjsondata("poubelle")
    contenu = scraper.getjsondata("nino-negri-5-stelle-sfursat-2022.html")
    assert vide.parker() is None
    assert vide.robinson() is None
    assert vide.suckling() is None
    assert vide._getcritiques("test_ts") is None
    assert poubelle.parker() is None
    assert poubelle.robinson() is None
    assert poubelle.suckling() is None
    assert poubelle._getcritiques("test_ts") is None
    assert contenu.parker() == "91"
    assert contenu.robinson() == "17"
    assert contenu.suckling() == "93.5"
    assert contenu._getcritiques("test_ts") is None

def test_prix(scraper: Scraper):
    vide = scraper.getjsondata("")
    poubelle = scraper.getjsondata("poubelle")
    contenu = scraper.getjsondata("nino-negri-5-stelle-sfursat-2022.html")

    # Cas vide : items == [] -> on ne peut pas calculer -> ValueError
    with pytest.raises(ValueError):
        _ = vide.prix()

    # Cas poubelle : JSON incomplet -> _getcontent() None -> ValueError
    with pytest.raises(ValueError):
        _ = poubelle.prix()

    assert contenu.prix() == 65.0

