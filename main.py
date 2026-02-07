from sys import stderr
from typing import cast, Any, Dict, Optional
from requests import Response, Session
from bs4 import BeautifulSoup, Tag
from json import JSONDecodeError, loads


class Scraper:
    """
    Scraper est une classe qui permet de gerer
    de façon dynamique des requetes uniquement
    sur le serveur https de Millesima
    """

    def __init__(self) -> None:
        self._url: str = "https://www.millesima.fr/"
        self._session: Session = Session()
        self._latest_request: tuple[(str, Response | None)] = ("", None)

    def _request(self, subdir: str) -> Response:
        target_url: str = self._url + subdir.lstrip("/")
        response: Response = self._session.get(url=target_url, timeout=10)
        response.raise_for_status()
        return response

    def getresponse(self, subdir: str = "") -> Response:
        rq_subdir, rq_response = self._latest_request
        if rq_response is None or subdir != rq_subdir:
            request: Response = self._request(subdir)
            self._latest_request = (subdir, request)
            return request
        return rq_response

    def getsoup(self, subdir: str = "") -> BeautifulSoup:
        markup: str = self.getresponse(subdir).text
        return BeautifulSoup(markup, features="html.parser")

    def getjsondata(self, subdir: str = "", id: str = "__NEXT_DATA__") -> dict[str, object]:
        soup: BeautifulSoup = self.getsoup(subdir)
        script: Tag | None = soup.find("script", id=id)

        if isinstance(script, Tag) and script.string:
            try:
                current_data: object = loads(script.string)
                keys: list[str] = ["props", "pageProps", "initialReduxState", "product", "content"]
                for key in keys:
                    if isinstance(current_data, dict) and key in current_data:
                        current_data = current_data[key]
                    else:
                        raise ValueError(f"Clé manquante dans le JSON : {key}")

                if isinstance(current_data, dict):
                    return cast(dict[str, object], current_data)

            except (JSONDecodeError, ValueError) as e:
                print(f"Erreur lors de l'extraction JSON : {e}", file=stderr)
        return {}

    def prix(self, subdir: str) -> float:
        """
            Retourne le prix d'une bouteille (75cl).
            Les données récupérées depuis le site contiennent plusieurs formats
            de vente dans la liste "items" :
            - bouteille seule si nbunit=1 et equivbtl=1 
                -> prix direct (format vendu à l'unité).
            - caisse de plusieurs bouteilles si nbunit=1
                -> prix direct (format vendu à l'unité).
            - formats spéciaux (magnum, impériale, etc.)sinon 
                -> calcul du prix unitaire :  offerPrice / (nbunit * equivbtl)

            Chaque item possède notamment :
                - offerPrice : prix total du format proposé
                - nbunit : nombre d'unités dans le format
                - equivbtl : équivalent en nombre de bouteilles standard (75cl)
                            
        """
        data = self.getjsondata(subdir)

        items = data.get("items")
        if not isinstance(items, list) or len(items) == 0:
            raise ValueError("Aucun prix disponible (items vide).")

        # 1) bouteille 75cl (nbunit=1 et equivbtl=1)
        for item in items:
            if not isinstance(item, dict):
                continue
            attrs = item.get("attributes", {})
            nbunit = attrs.get("nbunit", {}).get("value")
            equivbtl = attrs.get("equivbtl", {}).get("value")

            if nbunit == "1" and equivbtl == "1":
                p = item.get("offerPrice")
                if isinstance(p, (int, float)):
                    return float(p)

        # 2) calcul depuis caisse
        for item in items:
            if not isinstance(item, dict):
                continue
            p = item.get("offerPrice")
            attrs = item.get("attributes", {})
            nbunit = attrs.get("nbunit", {}).get("value")
            equivbtl = attrs.get("equivbtl", {}).get("value")

            if isinstance(p, (int, float)) and nbunit and equivbtl:
                denom = float(nbunit) * float(equivbtl)
                if denom > 0:
                    return round(float(p) / denom, 2)

        raise ValueError("Impossible de trouver le prix unitaire.")
