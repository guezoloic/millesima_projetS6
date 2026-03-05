import pandas as pd
import pytest
from pandas import DataFrame

from cleaning import (
    SCORE_COLS,
    drop_empty_appellation,
    mean_score,
    fill_missing_scores,
    encode_appellation,
)


@pytest.fixture
def df_raw() -> DataFrame:
    return pd.DataFrame({
        "Appellation": ["Pauillac", "Pauillac ", "Margaux", None, "Pomerol", "Pomerol"],
        "Robert":      ["95", None, "bad", 90, None, None],
        "Robinson":    [None, "93", 18, None, None, None],
        "Suckling":    [96, None, None, None, 91, None],
        "Prix":        ["10.0", "11.0", "20.0", "30.0", "40.0", "50.0"],
    })


def test_drop_empty_appellation(df_raw: DataFrame):
    out = drop_empty_appellation(df_raw)
    assert out["Appellation"].isna().sum() == 0
    assert len(out) == 5 


def test_mean_score_zero_when_no_scores(df_raw: DataFrame):
    out = drop_empty_appellation(df_raw)
    m = mean_score(out, "Robert")
    assert list(m.columns) == ["Appellation", "mean_Robert"]

    # Pomerol n'a aucune note Robert => moyenne doit être 0
    pomerol_mean = m.loc[m["Appellation"].str.strip() == "Pomerol", "mean_Robert"].iloc[0]
    assert pomerol_mean == 0


def test_fill_missing_scores(df_raw: DataFrame):
    out = drop_empty_appellation(df_raw)
    filled = fill_missing_scores(out)

    # plus de NaN dans les colonnes de scores
    for col in SCORE_COLS:
        assert filled[col].isna().sum() == 0

    assert filled.loc[1, "Robert"] == 95.0

    # pas de colonnes temporaires mean_*
    for col in SCORE_COLS:
        assert f"mean_{col}" not in filled.columns


def test_encode_appellation(df_raw: DataFrame):
    out = drop_empty_appellation(df_raw)
    filled = fill_missing_scores(out)
    encoded = encode_appellation(filled)

    # la colonne texte disparaît
    assert "Appellation" not in encoded.columns
    assert "Pauillac" in encoded.columns
    assert encoded.loc[0, "Pauillac"] == 1