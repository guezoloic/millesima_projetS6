from sys import stderr
from typing import cast
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
        """
        Initialise la session de scraping.
        """
        self._url: str = "https://www.millesima.fr/"
        # Très utile pour éviter de renvoyer toujours les mêmes handshake
        # TCP et d'avoir toujours une connexion constante avec le server
        self._session: Session = Session()
        # Système de cache pour éviter de solliciter le serveur inutilement
        self._latest_request: tuple[(str, Response | None)] = ("", None)

    def _request(self, subdir: str) -> Response:
        """
        Effectue une requête GET sur le serveur Millesima.

        Args:
            subdir (str): Le sous-répertoire ou chemin de l'URL (ex: "/vins").

        Returns:
            Response: L'objet réponse de la requête.

        Raise:
            HTTPError: Si le serveur renvoie un code d'erreur (4xx, 5xx).
        """
        target_url: str = self._url + subdir.lstrip("/")
        response: Response = self._session.get(url=target_url, timeout=10)
        response.raise_for_status()
        return response

    def getresponse(self, subdir: str = "") -> Response:
        """
        Récupère la réponse d'une page, en utilisant le cache si possible.

        Args:
            subdir (str, optional): Le chemin de la page.

        Returns:
            Response: L'objet réponse (cache ou nouvelle requête).

        Raise:
            HTTPError: Si le serveur renvoie un code d'erreur (4xx, 5xx).
        """
        rq_subdir, rq_response = self._latest_request

        if rq_response is None or subdir != rq_subdir:
            request: Response = self._request(subdir)
            self._latest_request = (subdir, request)
            return request

        return rq_response

    def getsoup(self, subdir: str = "") -> BeautifulSoup:
        """
        Récupère le contenu HTML d'une page et le transforme en objet BeautifulSoup.

        Args:
            subdir (str, optional): Le chemin de la page.

        Returns:
            BeautifulSoup: L'objet parsé pour extraction de données.

        Raise:
            HTTPError: Si le serveur renvoie un code d'erreur (4xx, 5xx).
        """
        markup: str = self.getresponse(subdir).text
        return BeautifulSoup(markup, features="html.parser")

    def getjsondata(
        self, subdir: str = "", id: str = "__NEXT_DATA__"
    ) -> dict[str, object]:
        """
        Extrait les données JSON contenues dans la balise __NEXT_DATA__ du site.
        Beaucoup de sites modernes (Next.js) stockent leur état initial dans
        une balise <script> pour l'hydratation côté client.

        Args:
            subdir (str, optional): Le chemin de la page.
            id (str, optional): L'identifiant de la balise script (par défaut __NEXT_DATA__).

        Raises:
            HTTPError: Soulevée par `getresponse` si le serveur renvoie un code d'erreur (4xx, 5xx).
            JSONDecodeError: Soulevée par `loads` si le contenu de la balise n'est pas un JSON valide.
            ValueError: Soulevée manuellement si l'une des clés attendues (props, pageProps, etc.) 
                        est absente de la structure JSON.

        Returns:
            dict[str, object]: Un dictionnaire contenant les données utiles
                                 ou un dictionnaire vide en cas d'erreur.
        """
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
