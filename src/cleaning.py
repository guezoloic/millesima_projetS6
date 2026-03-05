#!/usr/bin/env python3
from pandas import DataFrame, to_numeric
import pandas as pd

SCORE_COLS = ["Robert", "Robinson", "Suckling"]


def display_info(df: DataFrame, name: str = "DataFrame") -> None:
    """
    Affiche un résumé du DataFrame
        -la taille
        -types des colonnes
        -valeurs manquantes
        -statistiques numériques
    """
    print(f"\n===== {name} =====")

    print(f"Shape : {df.shape[0]} lignes × {df.shape[1]} colonnes")

    print("\nTypes des colonnes :")
    print(df.dtypes)

    print("\nValeurs manquantes :")
    print(df.isna().sum())

    print("\nStatistiques numériques :")
    print(df.describe().round(2))


def drop_empty_appellation(df: DataFrame) -> DataFrame:

    return df.dropna(subset=["Appellation"])


def mean_score(df: DataFrame, col: str) -> DataFrame:
    """
    Calcule la moyenne d'une colonne de score par appellation.
        - Convertit les valeurs en numériques, en remplaçant les non-convertibles par NaN
        - Calcule la moyenne par appellation
        - Remplace les NaN résultants par 0 

    """
    tmp = df[["Appellation", col]].copy()

    tmp[col] = to_numeric(tmp[col], errors="coerce")

    # moyenne par appellation
    means = tmp.groupby("Appellation", as_index=False)[col].mean()
    
    means[col] = means[col].fillna(0)
    
    means = means.rename(columns={col: f"mean_{col}"})
    
    return means


def mean_robert(df: DataFrame) -> DataFrame:
    return mean_score(df, "Robert")


def mean_robinson(df: DataFrame) -> DataFrame:
    return mean_score(df, "Robinson")


def mean_suckling(df: DataFrame) -> DataFrame:
    return mean_score(df, "Suckling")


def fill_missing_scores(df: DataFrame) -> DataFrame:
    """
    Remplacer les notes manquantes par la moyenne
    des vins de la même appellation.
    """
    df_copy = df.copy()
    df_copy["Appellation"] = df_copy["Appellation"].astype(str).str.strip()

    for score in SCORE_COLS:
        df_copy[score] = to_numeric(df_copy[score], errors="coerce")

    temp_cols: list[str] = []

    for score in SCORE_COLS:
        mean_df = mean_score(df_copy, score)
        mean_name = f"mean_{score}"
        temp_cols.append(mean_name)

        df_copy = df_copy.merge(mean_df, on="Appellation", how="left")
        df_copy[score] = df_copy[score].fillna(df_copy[mean_name])

    df_copy = df_copy.drop(columns=temp_cols)
    return df_copy


def encode_appellation(df: DataFrame, column: str = "Appellation") -> DataFrame:
    """
    Remplace la colonne 'Appellation' par des colonnes indicatrices
    """
    df_copy = df.copy()
    
    appellations = df_copy[column].astype(str).str.strip()

    appellation_dummies = pd.get_dummies(appellations)

    df_copy = df_copy.drop(columns=[column])

    return df_copy.join(appellation_dummies)
