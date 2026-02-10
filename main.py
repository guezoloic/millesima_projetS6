from typing import cast
from requests import Response, Session
from bs4 import BeautifulSoup, Tag
from collections import OrderedDict
from json import loads


class _ScraperData:
    def __init__(self, data: dict[str, object]) -> None:
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

    def prix(self) -> float:
        """
            Retourne le prix unitaire d'une bouteille (75cl).

            Le JSON contient plusieurs formats de vente dans content["items"] :
            - bouteille seule : nbunit = 1 et equivbtl = 1 -> prix direct
            - caisse de plusieurs bouteilles : nbunit > 1 -> on divise le prix total
            - formats spéciaux (magnum etc.) : equivbtl > 1 -> même calcul

            Formule générale :
                prix_unitaire = offerPrice / (nbunit * equivbtl)

            """

        content = self._getcontent()  

        # si content n'existe pas -> erreur
        if content is None:
            raise ValueError("Contenu introuvable")

        # On récupère la liste des formats disponibles (bouteille, carton...)
        items = content.get("items")

        # Vérification que items est bien une liste non vide
        if not isinstance(items, list) or len(items) == 0:
            raise ValueError("Aucun prix disponible (items vide)")

        # --------------------------
        # CAS 1 : bouteille unitaire
        # --------------------------
        # On cherche un format où nbunit=1 et equivbtl=1 ->bouteille standard 75cl 
        for item in items:
            
            if not isinstance(item, dict):
                continue

            # On récupère les attributs du format
            attrs = item.get("attributes", {})

            # On récupère nbunit et equivbtl
            nbunit = attrs.get("nbunit", {}).get("value")
            equivbtl = attrs.get("equivbtl", {}).get("value")

            # Si c'est une bouteille unitaire
            if nbunit == "1" and equivbtl == "1":

                p = item.get("offerPrice")

                # Vérification que c'est bien un nombre
                if isinstance(p, (int, float)):
                    return float(p)

        # --------------------------
        # CAS 2 : caisse ou autre format
        # --------------------------
        # On calcule le prix unitaire à partir du prix total
        for item in items:

            if not isinstance(item, dict):
                continue

            p = item.get("offerPrice")
            attrs = item.get("attributes", {})

            nbunit = attrs.get("nbunit", {}).get("value")
            equivbtl = attrs.get("equivbtl", {}).get("value")

            # Vérification que toutes les valeurs existent
            if isinstance(p, (int, float)) and nbunit and equivbtl:

                # Calcul du nombre total de bouteilles équivalentes
                denom = float(nbunit) * float(equivbtl)

                # Évite division par zéro
                if denom > 0:

                    # Calcul du prix unitaire
                    prix_unitaire = float(p) / denom

                    # Arrondi à 2 décimales
                    return round(prix_unitaire, 2)

        # Si aucun prix trouvé
        raise ValueError("Impossible de trouver le prix unitaire.")

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
            if len(val) > 1:
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

