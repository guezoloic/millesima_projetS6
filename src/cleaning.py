#!/usr/bin/env python3

from os import getcwd
from os.path import normpath, join
from typing import cast
from pandas import DataFrame, read_csv, to_numeric, get_dummies
from sys import argv


def path_filename(filename: str) -> str:
    return normpath(join(getcwd(), filename))


class Cleaning:
    def __init__(self, filename) -> None:
        self._vins: DataFrame = read_csv(filename)
        #
        self.SCORE_COLS: list[str] = [
            c for c in self._vins.columns if c not in ["Appellation", "Prix"]
        ]
        #
        for col in self.SCORE_COLS:
            self._vins[col] = to_numeric(self._vins[col], errors="coerce")

    def getVins(self) -> DataFrame:
        return self._vins.copy(deep=True)

    def __str__(self) -> str:
        """
        Affiche un résumé du DataFrame
            - la taille
            - types des colonnes
            - valeurs manquantes
            - statistiques numériques
        """
        return (
            f"Shape : {self._vins.shape[0]} lignes x {self._vins.shape[1]} colonnes\n\n"
            f"Types des colonnes :\n{self._vins.dtypes}\n\n"
            f"Valeurs manquantes :\n{self._vins.isna().sum()}\n\n"
            f"Statistiques numériques :\n{self._vins.describe().round(2)}\n\n"
        )

    def drop_empty_appellation(self) -> "Cleaning":
        self._vins = self._vins.dropna(subset=["Appellation"])
        return self

    def _mean_score(self, col: str) -> DataFrame:
        """
        Calcule la moyenne d'une colonne de score par appellation.
            - Convertit les valeurs en numériques, en remplaçant les non-convertibles par NaN
            - Calcule la moyenne par appellation
            - Remplace les NaN résultants par 0

        """
        means = self._vins.groupby("Appellation", as_index=False)[col].mean()
        means = means.rename(
            columns={col: f"mean_{col}"}
        )  # pyright: ignore[reportCallIssue]
        return cast(DataFrame, means.fillna(0))

    def _mean_robert(self) -> DataFrame:
        return self._mean_score("Robert")

    def _mean_robinson(self) -> DataFrame:
        return self._mean_score("Robinson")

    def _mean_suckling(self) -> DataFrame:
        return self._mean_score("Suckling")

    def fill_missing_scores(self) -> "Cleaning":
        """
        Remplacer les notes manquantes par la moyenne
        des vins de la même appellation.
        """
        for element in self.SCORE_COLS:
            means = self._mean_score(element)
            self._vins = self._vins.merge(means, on="Appellation", how="left")

            mean_col = f"mean_{element}"
            self._vins[element] = self._vins[element].fillna(self._vins[mean_col])

            self._vins = self._vins.drop(columns=["mean_" + element])
        return self

    def encode_appellation(self, column: str = "Appellation") -> "Cleaning":
        """
        Remplace la colonne 'Appellation' par des colonnes indicatrices
        """
        appellations = self._vins[column].astype(str).str.strip()
        appellation_dummies = get_dummies(appellations)
        self._vins = self._vins.drop(columns=[column])
        self._vins = self._vins.join(appellation_dummies)
        return self


def main() -> None:
    if len(argv) != 2:
        raise ValueError(f"Usage: {argv[0]} <filename.csv>")

    filename = argv[1]
    cleaning: Cleaning = Cleaning(filename)
    _ = cleaning.drop_empty_appellation().fill_missing_scores().encode_appellation()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERREUR: {e}")
