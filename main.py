from sys import stderr
from typing import cast
from requests import Response, Session
from bs4 import BeautifulSoup, Tag
from json import JSONDecodeError, loads


class Scraper:
    def __init__(self, subdir: str = "") -> None:
        self._url: str = "https://www.millemisa.fr/"
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

    # def getjsondata(self, subdir: str = "", id: str = "__NEXT_DATA__") -> dict[str, object]:
    # soup: BeautifulSoup = self.getsoup(subdir)
    # # On s'assure que c'est bien un Tag pour avoir accès à .string
    # script = soup.find("script", id=id)

    # if isinstance(script, Tag) and script.string:
    #     try:
    #         # On commence avec le dictionnaire complet
    #         current_data: Any = loads(script.string)

    #         # Parcours de la structure imbriquée
    #         keys = ['props', 'pageProps', 'initialReduxState', 'product', 'content']
    #         for key in keys:
    #             if isinstance(current_data, dict) and key in current_data:
    #                 current_data = current_data[key]
    #             else:
    #                 # Si une clé manque, on lève une erreur explicite
    #                 raise ValueError(f"Clé manquante dans le JSON : {key}")

    #         # On garantit à Pyright que le résultat final est un dictionnaire
    #         if isinstance(current_data, dict):
    #             return cast(dict[str, object], current_data)

    #     except (decoder.JSONDecodeError, ValueError) as e:
    #         print(f"Erreur lors de l'extraction JSON : {e}", file=stderr)

    # return {}

    def getjsondata(
        self, subdir: str = "", id: str = "__NEXT_DATA__"
    ) -> dict[str, object]:
        soup: BeautifulSoup = self.getsoup(subdir)
        script: Tag | None = soup.find("script", id=id)

        if isinstance(script, Tag) and script.string:
            try:
                current_data: object = loads(script.string)
                # tout le chemin à parcourir pour arriver au données 
                # (plein d'information inutile)
                keys: list[str] = [
                    "props",
                    "pageProps",
                    "initialReduxState",
                    "product",
                    "content",
                ]
                for key in keys:
                    # si current_data est bien un dictionnaire et que la clé 
                    # est bien dedans
                    if isinstance(current_data, dict) and key in current_data:
                        current_data = current_data[key]
                    else:
                        raise ValueError(f"Clé manquante dans le JSON : {key}")

                if isinstance(current_data, dict):
                    return cast(dict[str, object], current_data)

            except (JSONDecodeError, ValueError) as e:
                print(f"Erreur lors de l'extraction JSON : {e}", file=stderr)
        return {}