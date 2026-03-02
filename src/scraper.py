#!/usr/bin/env python3

from io import SEEK_END, SEEK_SET, BufferedWriter, BufferedReader
from os.path import exists, normpath, realpath, dirname, join
from os import makedirs
from pickle import dump, load, UnpicklingError
from sys import argv
from typing import Any, Callable, Literal, cast
from requests import HTTPError, Response, Session
from bs4 import BeautifulSoup, Tag
from collections import OrderedDict
from json import JSONDecodeError, loads

_dir: str = dirname(realpath(__name__))


def _getcache[T](mode: Literal["rb", "wb"], fn: Callable[[Any], T]) -> T | None:
    """_summary_

    Returns:
        _type_: _description_
    """
    cache_dirname = normpath(join(_dir, ".cache"))
    save_path = normpath(join(cache_dirname, "save"))

    if not exists(cache_dirname):
        makedirs(cache_dirname)

    try:
        with open(save_path, mode) as f:
            return fn(f)
    except (FileNotFoundError, EOFError, UnpicklingError):
        return None


def savestate(data: tuple[int, set[str]]) -> None:
    def save(f: BufferedWriter) -> None:
        _ = f.seek(0)
        _ = f.truncate()
        dump(data, f)
        f.flush()
    _getcache("wb", save)

def loadstate() -> tuple[int, set[str]] | None:
    return _getcache("rb", lambda f: load(f))


class _ScraperData:
    """
    Conteneur de données spécialisé pour extraire les informations des dictionnaires JSON.

    Cette classe agit comme une interface simplifiée au-dessus du dictionnaire brut
    renvoyé par la balise __NEXT_DATA__ du site Millesima.
    """

    def __init__(self, data: dict[str, object]) -> None:
        """
        Initialise le conteneur avec un dictionnaire de données.

        Args:
            data (dict[str, object]): Le dictionnaire JSON brut extrait de la page.
        """
        self._data: dict[str, object] = data

    def _getcontent(self) -> dict[str, object] | None:
        """
        Navigue dans l'arborescence Redux pour atteindre le contenu du produit.

        Returns:
            dict[str, object] | None: Le dictionnaire du produit ou None si la structure diffère.
        """
        current_data: dict[str, object] = self._data
        for key in ["initialReduxState", "product", "content"]:
            new_data: object | None = current_data.get(key)
            if new_data is None:
                return None
            current_data: dict[str, object] = cast(dict[str, object], new_data)

        return current_data

    def _getattributes(self) -> dict[str, object] | None:
        """
        Extrait les attributs techniques (notes, appellations, etc.) du produit.

        Returns:
            dict[str, object] | None: Les attributs du vin ou None.
        """
        current_data: object = self._getcontent()
        if current_data is None:
            return None
        return cast(dict[str, object], current_data.get("attributes"))

    def prix(self) -> float | None:
        """
        Calcule le prix unitaire d'une bouteille (standardisée à 75cl).

        Le site vend souvent par caisses (6, 12 bouteilles) ou formats (Magnum).
        Cette méthode normalise le prix pour obtenir celui d'une seule unité.

        Returns:
            float | None: Le prix calculé arrondi à 2 décimales, ou None.
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
        """
        Extrait le nom de l'appellation du vin.

        Returns:
            str | None: Le nom (ex: 'Pauillac') ou None.
        """
        attrs: dict[str, object] | None = self._getattributes()

        if attrs is not None:
            app_dict: object | None = attrs.get("appellation")
            if isinstance(app_dict, dict):
                return cast(str, app_dict.get("value"))
        return None

    def _getcritiques(self, name: str) -> str | None:
        """
        Méthode générique pour parser les notes des critiques (Parker, Suckling, etc.).

        Gère les notes simples ("95") et les plages de notes ("95-97") en faisant la moyenne.

        Args:
            name (str): La clé de l'attribut dans le JSON (ex: 'note_rp').

        Returns:
            str | None: La note formatée en chaîne de caractères ou None.
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
                val[0] = str(round((float(val[0]) + float(val[1])) / 2, 1))

            return val[0]
        return None

    def parker(self) -> str | None:
        """Note Robert Parker."""
        return self._getcritiques("note_rp")

    def robinson(self) -> str | None:
        """Note Jancis Robinson."""
        return self._getcritiques("note_jr")

    def suckling(self) -> str | None:
        """Note James Suckling."""
        return self._getcritiques("note_js")

    def getdata(self) -> dict[str, object]:
        """Retourne le dictionnaire de données complet."""
        return self._data

    def informations(self) -> str:
        """
        Agrège les données clés pour l'export CSV.

        Returns:
            str: Ligne formatée : "Appellation,Parker,Robinson,Suckling,Prix".
        """

        appellation = self.appellation()
        parker = self.parker()
        robinson = self.robinson()
        suckling = self.suckling()
        prix = self.prix()

        return f"{appellation},{parker},{robinson},{suckling},{prix}"


class Scraper:
    """
    Client HTTP optimisé pour le scraping de millesima.fr.

    Gère la session persistante, les headers de navigation et un cache double
    pour optimiser les performances et la discrétion.
    """

    def __init__(self) -> None:
        """
        Initialise l'infrastructure de navigation:

         - créer une session pour éviter de faire un handshake pour chaque requête
         - ajout d'un header pour éviter le blocage de l'accès au site
         - ajout d'un système de cache
        """
        self._url: str = "https://www.millesima.fr/"
        # Très utile pour éviter de renvoyer toujours les mêmes handshake
        # TCP et d'avoir toujours une connexion constante avec le server
        self._session: Session = Session()
        # Crée une "fausse carte d'identité" pour éviter que le site nous
        # bloque car on serait des robots
        self._session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
                     AppleWebKit/537.36 (KHTML, like Gecko) \
                     Chrome/122.0.0.0 Safari/537.36",
                "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            }
        )
        # Système de cache pour éviter de solliciter le serveur inutilement
        # utilise pour _request
        self._latest_request: tuple[(str, Response)] | None = None
        # utilise pour getsoup
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

        Raises:
            HTTPError: Si le serveur renvoie un code d'erreur (4xx, 5xx).
        """
        target_url: str = self._url + subdir.lstrip("/")
        # envoyer une requête GET sur la page si erreur, renvoie un raise
        response: Response = self._session.get(url=target_url, timeout=30)
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

        Raises:
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

        Raises:
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

        Args:
            subdir (str): Le chemin de la page.
            id (str, optional): L'identifiant de la balise script.

        Raises:
            HTTPError: Erreur renvoyée par le serveur (4xx, 5xx).
            JSONDecodeError: Si le contenu de la balise n'est pas un JSON valide.
            ValueError: Si les clés 'props' ou 'pageProps' sont absentes.

        Returns:
            _ScraperData: Instance contenant les données extraites.
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

    def _geturlproductslist(self, subdir: str) -> list[str] | None:
        """
        Récupère la liste des produits d'une page de catégorie.
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

    def getvins(self, subdir: str, filename: str, reset: bool = False) -> None:
        """
        Scrape récursivement toutes les pages d'une catégorie et sauvegarde en CSV.

        Args:
            subdir (str): La catégorie (ex: '/vins-rouges').
            filename (str): Nom du fichier de sortie (ex: 'vins.csv').
            reset (bool): (Optionnel) pour réinitialiser le processus.
        """
        mode: Literal["w", "a+"] = "w" if reset else "a+"
        title: str = "Appellation,Robert,Robinson,Suckling,Prix\n"
        page: int = 1
        cache: set[str] = set[str]()

        if not reset:
            serializable: tuple[int, set[str]] | None = loadstate()
            if isinstance(serializable, tuple):
                page, cache = serializable
        try:
            with open(filename, mode) as f:
                # check si le titre est bien présent au début du buffer
                # sinon il l'ecrit, petit bug potentiel, a+ ecrit tout le
                # temps a la fin du buffer, si on a ecrit des choses avant
                # le titre sera apres ces données mais on part du principe
                # que personne va toucher le fichier.
                _ = f.seek(0, SEEK_SET)
                if not (f.read(len(title)) == title):
                    _ = f.write(title)
                else:
                    _ = f.seek(0, SEEK_END)

                while True:
                    products_list: list[str] | None = self._geturlproductslist(
                        f"{subdir}?page={page}"
                    )

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
                    page += 1
        except:
            if not reset:
                savestate((page, cache))


def main() -> None:
    if len(argv) != 3:
        raise ValueError(f"{argv[0]} <filename> <sous-url>")
    scraper: Scraper = Scraper()
    scraper.getvins(argv[2], argv[1])


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERREUR: {e}")
