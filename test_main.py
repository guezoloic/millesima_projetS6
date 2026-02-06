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
            text="<html><body><h1>MILLESIMA</h1></body></html>",
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
                                "longdesc": "<h2>Caractéristiques et conseils de dégustation du 5 Stelle Sfursat 2022 de Nino Negri</h2><p><strong>Dégustation</strong></p><p><em>Robe</em></p><p>La robe dévoile une couleur grenat d'intensité moyenne.</p><p><em>Nez</em></p><p>Le nez révèle des arômes singuliers de fruits mûrs accompagnés de notes d'épices douces.</p><p><em>Bouche</em></p><p>En bouche, ce vin séduit par son équilibre remarquable, sa richesse et son caractère corsé. La dégustation dévoile une concentration intense et vigoureuse, portée par un fond aristocratique de mûre bien mûre et d'épices. La finale se distingue par sa longueur et sa persistance.</p><p><strong>Accords mets et vins</strong></p><p>Ce vin de caractère accompagne parfaitement les viandes rouges braisées, le gibier en sauce ou encore les fromages affinés à pâte dure.</p><p><strong>Service et garde</strong></p><p>Le 5 Stelle Sfursat 2022 gagnera à être servi à une température comprise entre 16 et 18°C.</p><h2>Un Sforzato di Valtellina d'exception élaboré par la Maison Nino Negri</h2><p><strong>La propriété</strong></p><p>Fondée en 1897 par Nino Negri à Chiuro en Valteline, cette Maison lombarde représente aujourd'hui la plus importante cave de la région. Propriété du Gruppo Italiano Vini depuis 1986, elle cultive 38 hectares de vignobles en terrasses sur des pentes alpines aux sols granitiques et calcaires. Sous la houlette de l'œnologue Danilo Drocco, <a href=\"/producteur-nino-negri.html\">Nino Negri</a> perpétue l'excellence du nebbiolo valtelin, notamment à travers son emblématique Sforzato élaboré selon la méthode traditionnelle d'appassimento.</p><p><strong>Le vignoble</strong></p><p>Le 5 Stelle Sfursat est issu de l'appellation <a href=\"/sforzato-di-valtellina.html\">Sforzato di Valtellina</a> DOCG, territoire d'exception où le nebbiolo s'épanouit sur des terrasses alpines escarpées. Les raisins proviennent de vignobles implantés sur des pentes granitiques et calcaires, bénéficiant d'une exposition optimale permettant une maturation idéale du nebbiolo.</p><p><strong>Vinification et élevage</strong></p><p>Le 5 Stelle Sfursat 2022 est produit uniquement lors des saisons les plus favorables. Les raisins sont récoltés manuellement et disposés en couche unique dans des caisses de 4 kg. Ils sont ensuite soumis à un séchage naturel dans un grenier pendant environ trois mois avant la vinification, selon la méthode traditionnelle de l'appassimento. Ce processus permet aux baies de perdre près de 30 % de leur poids, concentrant ainsi les arômes et les sucres naturels.</p><p><strong>Cépage</strong></p><p>Ce <a href=\"/lombardie.html\">vin de Lombardie</a> est un 100 % nebbiolo</p>", 
                                "image": "J4131_2022NM_c.png",
                                "seoKeyword": "nino-negri-5-stelle-sfursat-2022.html",
                                "title": "Nino Negri : 5 Stelle Sfursat 2022",
                                "metaDesc": "Nino Negri : 5 Stelle Sfursat 2022 : Vente en ligne, Grand vin d'origine garantie en provenance directe de la propriété - ✅ Qualité de stockage",
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
                                                "displayable": "false",
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
                            }
                        }
                    }
                }
            }
        }

        html_product = f"""
        <html>
            <script id="__NEXT_DATA__" type="application/json">
                {dumps(json_data)}
            </script>
        </body>
        </html>
        """
        m.get("https://www.millesima.fr/nino-negri-5-stelle-sfursat-2022.html", text=html_product)

        # on return m sans fermer le server qui simule la page
        yield m


@pytest.fixture
def scraper() -> Scraper:
    return Scraper()


def test_soup(scraper: Scraper):
    h1: Tag | None = scraper.getsoup().find("h1")

    assert isinstance(h1, Tag)
    assert h1.text == "MILLESIMA"


def test_getProductName(scraper: Scraper):
    jsondata = scraper.getjsondata("nino-negri-5-stelle-sfursat-2022.html")
    assert jsondata["productName"] == "Nino Negri : 5 Stelle Sfursat 2022"
    assert len(jsondata["items"]) > 0
    assert jsondata["items"][0]["offerPrice"] == 390