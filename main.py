from typing import cast
from requests import HTTPError, Response, Session
from bs4 import BeautifulSoup, Tag
from collections import OrderedDict
from json import JSONDecodeError, loads


class _ScraperData:
    """_summary_
    """
    def __init__(self, data: dict[str, object]) -> None:
        """_summary_

        Args:
            data (dict[str, object]): _description_
        """
        self._data: dict[str, object] = data

    def _getcontent(self) -> dict[str, object] | None:
        """_summary_

        Returns:
            dict[str, object]: _description_
        """
        current_data: dict[str, object] = self._data
        for key in ["initialReduxState", "product", "content"]:
            new_data: object | None = current_data.get(key)
            if new_data is None:
                return None
            current_data: dict[str, object] = cast(dict[str, object], new_data)

        return current_data

    def _getattributes(self) -> dict[str, object] | None:
        """_summary_

        Returns:
            dict[str, object]: _description_
        """
        current_data: object = self._getcontent()
        if current_data is None:
            return None
        return cast(dict[str, object], current_data.get("attributes"))

    def prix(self) -> float | None:
        """
        Retourne le prix unitaire d'une bouteille (75cl).

        Si aucun prix n'est disponible, retourne None.
        """

        content = self._getcontent()
        if content is None:
            return None

        items = content.get("items")

        # Vérifie que items existe et n'est pas vide
        if not isinstance(items, list) or len(items) == 0:
            return None

        prix_calcule: float | None = None

        for item in items:
            if not isinstance(item, dict):
                continue

            p = item.get("offerPrice")
            attrs = item.get("attributes", {})

            nbunit = attrs.get("nbunit", {}).get("value")
            equivbtl = attrs.get("equivbtl", {}).get("value")

            if not isinstance(p, (int, float)) or not nbunit or not equivbtl:
                continue

            nb = float(nbunit)
            eq = float(equivbtl)

            if nb <= 0 or eq <= 0:
                continue

            if nb == 1 and eq == 1:
                return float(p)

            prix_calcule = round(float(p) / (nb * eq), 2)

        return prix_calcule

    def appellation(self) -> str | None:
        """_summary_

        Returns:
            str: _description_
        """
        attrs: dict[str, object] | None = self._getattributes()

        if attrs is not None:
            app_dict: object | None = attrs.get("appellation")
            if isinstance(app_dict, dict):
                return cast(str, app_dict.get("value"))
        return None

    def _getcritiques(self, name: str) -> str | None:
        """_summary_

        Args:
            name (str): _description_

        Returns:
            str | None: _description_
        """

        current_value: dict[str, object] | None = self._getattributes()
        if current_value is not None:
            app_dict: dict[str, object] = cast(
                dict[str, object], current_value.get(name)
            )
            if not app_dict:
                return None

            val = cast(str, app_dict.get("value")).rstrip("+").split("-")
            if len(val) > 1 and val[1] != "":
                val[0] = str((int(val[0]) + int(val[1])) / 2)

            return val[0]
        return None

    def parker(self) -> str | None:
        return self._getcritiques("note_rp")

    def robinson(self) -> str | None:
        return self._getcritiques("note_jr")

    def suckling(self) -> str | None:
        return self._getcritiques("note_js")

    def getdata(self) -> dict[str, object]:
        return self._data

    def informations(self) -> str:
        """
        Retourne toutes les informations sous la forme :
        "Appelation,Parker,J.Robinson,J.Suckling,Prix"
        """

        appellation = self.appellation()
        parker = self.parker()
        robinson = self.robinson()
        suckling = self.suckling()
        try:
            prix = self.prix()
        except ValueError:
            prix = None

        return f"{appellation},{parker},{robinson},{suckling},{prix}"


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
        self._latest_request: tuple[(str, Response)] | None = None
        self._latest_soups: OrderedDict[str, BeautifulSoup] = OrderedDict[
            str, BeautifulSoup
        ]()

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

    def getresponse(self, subdir: str = "", use_cache: bool = True) -> Response:
        """
        Récupère la réponse d'une page, en utilisant le cache si possible.

        Args:
            subdir (str, optional): Le chemin de la page.
            use_cache (bool, optional): Utilise la donnée deja sauvegarder ou
                                    écrase la donnée utilisé avec la nouvelle

        Returns:
            Response: L'objet réponse (cache ou nouvelle requête).

        Raise:
            HTTPError: Si le serveur renvoie un code d'erreur (4xx, 5xx).
        """

        # si dans le cache, latest_request existe
        if use_cache and self._latest_request is not None:
            rq_subdir, rq_response = self._latest_request

            # si c'est la meme requete et que use_cache est true,
            # on renvoie celle enregistrer
            if subdir == rq_subdir:
                return rq_response

        request: Response = self._request(subdir)
        # on recrée la structure pour le systeme de cache si activer
        if use_cache:
            self._latest_request = (subdir, request)

        return request

    def getsoup(self, subdir: str, use_cache: bool = True) -> BeautifulSoup:
        """
        Récupère le contenu HTML d'une page et le transforme en objet BeautifulSoup.

        Args:
            subdir (str, optional): Le chemin de la page.

        Returns:
            BeautifulSoup: L'objet parsé pour extraction de données.

        Raise:
            HTTPError: Si le serveur renvoie un code d'erreur (4xx, 5xx).
        """

        if use_cache and subdir in self._latest_soups:
            return self._latest_soups[subdir]

        markup: str = self.getresponse(subdir).text
        soup: BeautifulSoup = BeautifulSoup(markup, features="html.parser")

        if use_cache:
            self._latest_soups[subdir] = soup

            if len(self._latest_soups) > 10:
                _ = self._latest_soups.popitem(last=False)

        return soup

    def getjsondata(self, subdir: str, id: str = "__NEXT_DATA__") -> _ScraperData:
        """
        Extrait les données JSON contenues dans la balise __NEXT_DATA__ du site.
        Beaucoup de sites modernes (Next.js) stockent leur état initial dans
        une balise <script> pour l'hydratation côté client.

        Args:
            subdir (str): Le chemin de la page.
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

        if script is None or not script.string:
            raise ValueError(f"le script id={id} est introuvable")

        current_data: object = cast(object, loads(script.string))

        for key in ["props", "pageProps"]:
            if isinstance(current_data, dict) and key in current_data:
                current_data = cast(object, current_data[key])
                continue
            raise ValueError(f"Clé manquante dans le JSON : {key}")

        return _ScraperData(cast(dict[str, object], current_data))

    def _geturlproductslist(self, subdir: str):
        """_summary_

        Args:
            subdir (str): _description_

        Returns:
            _type_: _description_
        """
        try:
            data: dict[str, object] = self.getjsondata(subdir).getdata()

            for element in ["initialReduxState", "categ", "content"]:
                data: dict[str, object] = cast(dict[str, object], data.get(element))
                if not isinstance(data, dict):
                    return None

            products: list[str] = cast(list[str], data.get("products"))
            if isinstance(products, list):
                return products

        except (JSONDecodeError, HTTPError):
            return None

    def getvins(self, subdir: str, filename: str):
        """_summary_

        Args:
            subdir (str): _description_
            filename (str): _description_
        """
        with open(filename, "a") as f:
            cache: set[str] = set[str]()
            page = 0

            while True:
                page += 1
                products_list = self._geturlproductslist(f"{subdir}?page={page}")

                if not products_list:
                    break

                products_list_length = len(products_list)
                for i, product in enumerate(products_list):
                    if not isinstance(product, dict):
                        continue

                    link = product.get("seoKeyword")

                    if link and link not in cache:
                        try:
                            infos = self.getjsondata(link).informations()
                            _ = f.write(infos + "\n")
                            print(
                                f"page: {page} | {i + 1}/{products_list_length} {link}"
                            )
                            cache.add(link)
                        except (JSONDecodeError, HTTPError) as e:
                            print(f"Erreur sur le produit {link}: {e}")
                f.flush()


if __name__ == "__main__":
    Scraper().getvins("bordeaux.html", "donnee.csv")
