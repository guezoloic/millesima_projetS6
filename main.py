import requests
from typing import Any, Dict
from bs4 import BeautifulSoup
import json


class Scraper:
    """
    Scraper est une classe qui permet de gerer
    de façon dynamique des requetes uniquement
    sur le serveur https de Millesina
    """

    def __init__(self, subdir: str = None):
        """
        Initialise la session de scraping et récupère la page d'accueil.
        """
        # Très utile pour éviter de renvoyer toujours les mêmes handshake
        # TCP et d'avoir toujours une connexion constante avec le server
        self._session: requests.Session = requests.Session()
        self._url: str = "https://www.millesima.fr/"
        self._soup = self.getsoup(subdir)

    def _request(
            self, subdir: str, use_cache: bool = True
    ) -> requests.Response | requests.HTTPError:
        """
        Effectue une requête GET sur le serveur Millesima.
        :param subdir: Le sous-répertoire ou chemin de l'URL (ex: "/vins").
        :param use_cache: Si True, retourne la réponse précédente si l'URL est
        identique.
        :return: requests.Response: L'objet réponse de la requête.
        :rtype: requests.HTTPError: Si le serveur renvoie un code d'erreur
        (4xx, 5xx).
        """

        target_url: str = f"{self._url}{subdir.lstrip('/')}" if subdir is \
            not None else self._url
        # Éviter un max possible de faire des requetes au servers même
        # en ayant un tunnel tcp avec le paramètre `use_cache` que si
        # activer, va comparer l'url avec l'url précédant
        if use_cache and hasattr(self, "_response") \
                and self._response is not None:
            if self._response.url == target_url:
                return self._response

        self._response: requests.Response = self._session.get(
            target_url, timeout=10)
        self._response.raise_for_status()

        return self._response

    def getsoup(self, subdir: str = None
                ) -> BeautifulSoup | requests.HTTPError:
        """
        Récupère le contenu HTML d'une page et le transforme en objet
        BeautifulSoup.

        :param subdir: Le chemin de la page. Si None, retourne la soupe
        actuelle.
        :return: BeautifulSoup: L'objet parsé pour extraction de données.
        :rtype: BeautifulSoup
        """
        if not hasattr(self, "_soup") or subdir is not None:
            self._request(subdir)
            self._soup = BeautifulSoup(self._response.text, "html.parser")
        return self._soup

    def get_json_data(self) -> Dict[str, Any]:
        """
        Extrait les données JSON contenues dans la balise __NEXT_DATA__ du
        site.
        Beaucoup de sites modernes (Next.js) stockent leur état initial dans
        une balise <script> pour l'hydratation côté client.

        :return Dict[str, Any]: Un dictionnaire contenant les props de la page,
                           ou un dictionnaire vide en cas d'erreur ou
                           d'absence.
        """
        script = self._soup.find("script", id="__NEXT_DATA__")
        if script and script.string:
            try:
                data: dict[str, Any] = json.loads(script.string)
                for element in ['props', 'pageProps', 'initialReduxState',
                                'product', 'content']:
                    data = data[element]
                return data
            except json.decoder.JSONDecodeError:
                pass
        return {}
