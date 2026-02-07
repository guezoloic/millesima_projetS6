from sys import stderr
from typing import cast
from requests import Response, Session
from bs4 import BeautifulSoup, Tag
from json import JSONDecodeError, loads

class ScraperData:
    def __init__(self, data: dict[str, object]) -> None:
        if not data:
            raise ValueError("Données insuffisantes pour créer un ScraperData.")
        self._data: dict[str, object] = data

    def _getattributes(self) -> dict[str, object] | None:
        current_data: object = self._data.get("attributes")
        if isinstance(current_data, dict):
            return cast(dict[str, object], current_data)
        return None

    def appellation(self) -> str | None:
        current_value: dict[str, object] | None = self._getattributes()
        if current_value is not None:
            app_dict: dict[str, object] = cast(
                dict[str, object], current_value.get("appellation")
            )
            if app_dict:
                return cast(str, app_dict.get("value"))
        return None

    def _getvin(self, name: str) -> str | None:
        current_value: dict[str, object] | None = self._getattributes()
        if current_value is not None:
            app_dict: dict[str, object] = cast(
                dict[str, object], current_value.get(name)
            )
            if app_dict:
                return cast(str, app_dict.get("valueId")).rstrip("+")
        return None

    def parker(self) -> str | None:
        return self._getvin("note_rp")

    def robinson(self) -> str | None:
        return self._getvin("note_jr")

    def suckling(self) -> str | None:
        return self._getvin("note_js")

    def getdata(self) -> dict[str, object]:
        return self._data

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
        self._latest_soup: tuple[(str, BeautifulSoup | None)] = ("", None)

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

        if rq_response is not None and subdir == rq_subdir:
            return rq_response

        request: Response = self._request(subdir)
        self._latest_request = (subdir, request)
        return request

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
        rq_subdir, rq_soup = self._latest_soup

        if rq_soup is not None and subdir == rq_subdir:
            return rq_soup

        soup: BeautifulSoup = BeautifulSoup(
            markup=self.getresponse(subdir).text, features="html.parser"
        )

        self._latest_soup = (subdir, soup)
        return soup

    def getjsondata(self, subdir: str = "", id: str = "__NEXT_DATA__") -> ScraperData:
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
                        current_data: object = current_data[key]
                    else:
                        raise ValueError(f"Clé manquante dans le JSON : {key}")

                if isinstance(current_data, dict):
                    return ScraperData(data=cast(dict[str, object], current_data))

            except (JSONDecodeError, ValueError) as e:
                print(f"Erreur lors de l'extraction JSON : {e}", file=stderr)
        return ScraperData({})

# file = Scraper().getjsondata("/chateau-gloria-2016.html")
# print("parker:   ", file.parker())
# print("robinson: ", file.robinson())
# print("suckling: ", file.suckling())