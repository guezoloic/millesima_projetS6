#!/usr/bin/env python3

from os import getcwd
from os.path import normpath, join
from sys import argv
from pandas import read_csv, DataFrame

from cleaning import (display_info,
                      drop_empty_appellation,
                      mean_robert,
                      mean_robinson,
                      mean_suckling,
                      fill_missing_scores,
                      encode_appellation)


def load_csv(filename: str) -> DataFrame:
    path: str = normpath(join(getcwd(), filename))
    return read_csv(path)


def save_csv(df: DataFrame, out_filename: str) -> None:
    df.to_csv(out_filename, index=False)


def main() -> None:
    if len(argv) != 2:
        raise ValueError(f"Usage: {argv[0]} <filename.csv>")

    df = load_csv(argv[1])

    display_info(df, "Avant le nettoyage")

    df = drop_empty_appellation(df)
    save_csv(df, "donnee_clean.csv")
    display_info(df, "Après nettoyage d'appellations manquantes")
    
    #la moyenne des notes des vins pour chaque appellation
    robert_means = mean_robert(df)
    save_csv(robert_means, "mean_robert_by_appellation.csv")
    display_info(robert_means, "Moyennes Robert par appellation")

    robinson_means = mean_robinson(df)
    save_csv(robinson_means, "mean_robinson_by_appellation.csv")
    display_info(robinson_means, "Moyennes Robinson par appellation")
  
    suckling_means = mean_suckling(df)
    save_csv(suckling_means, "mean_suckling_by_appellation.csv")
    display_info(suckling_means, "Moyennes Suckling par appellation")
    
    df_missing_scores = fill_missing_scores(df)
    save_csv(df_missing_scores, "donnee_filled.csv")
    display_info(df_missing_scores, "Après remplissage des notes manquantes par la moyenne de l'appellation")
     
    df_ready = encode_appellation(df_missing_scores)
    save_csv(df_ready, "donnee_ready.csv")
    display_info(df_ready, "Après remplacer la colonne 'Appellation' par des colonnes indicatrices")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERREUR: {e}")