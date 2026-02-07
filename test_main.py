import json
from main import Scraper


def test_json():
    scraper = Scraper()

    data = scraper.getjsondata("/chateau-gloria-2016.html")

    print("JSON récupéré :")
    print(json.dumps(data, indent=4, ensure_ascii=False))

    assert isinstance(data, dict)
    assert "items" in data


def test_prix():
    scraper = Scraper()

    try:
        p = scraper.prix("/chateau-saint-pierre-2011.html")
        print("Prix unitaire =", p)

        assert isinstance(p, float)
        assert p > 0

    except ValueError:
        # le vin n'est pas disponible à la vente
        print("OK : aucun prix (vin indisponible, items vide)")


if __name__ == "__main__":
    test_json()
    test_prix()
    print("\nTous les tests terminés")
