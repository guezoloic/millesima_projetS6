import pytest
from unittest.mock import patch, mock_open
from cleaning import Cleaning


@pytest.fixture
def cleaning_raw() -> Cleaning:
    """
    "Appellation": ["Pauillac", "Pauillac ", "Margaux", None  , "Pomerol", "Pomerol"],
    "Robert":      ["95"      , None       , "bad"    , 90    , None     , None     ],
    "Robinson":    [None      , "93"       , 18       , None  , None     , None     ],
    "Suckling":    [96        , None       , None     , None  , 91       , None     ],
    "Prix":        ["10.0"    , "11.0"     , "20.0"   , "30.0", "40.0"   , "50.0"   ],
    """
    csv_content = """Appellation,Robert,Robinson,Suckling,Prix
Pauillac,95,,96,10.0
Pauillac ,,93,,11.0
Margaux,bad,18,,20.0
,90,,,30.0
Pomerol,,,91,40.0
Pomerol,,,,50.0
"""
    m = mock_open(read_data=csv_content)
    with patch("builtins.open", m):
        return Cleaning("donnee.csv")


def test_drop_empty_appellation(cleaning_raw: Cleaning) -> None:
    out = cleaning_raw.drop_empty_appellation().getVins()
    assert out["Appellation"].isna().sum() == 0
    assert len(out) == 5


def test_mean_score_zero_when_no_scores(cleaning_raw: Cleaning) -> None:
    out = cleaning_raw.drop_empty_appellation()
    m = out._mean_score("Robert")
    assert list(m.columns) == ["Appellation", "mean_Robert"]
    pomerol_mean = m.loc[m["Appellation"].str.strip() == "Pomerol", "mean_Robert"].iloc[
        0
    ]
    assert pomerol_mean == 0


def test_fill_missing_scores(cleaning_raw: Cleaning):
    cleaning_raw._vins["Appellation"] = cleaning_raw._vins["Appellation"].str.strip()

    cleaning_raw.drop_empty_appellation()
    filled = cleaning_raw.fill_missing_scores().getVins()
    for col in cleaning_raw.SCORE_COLS:
        assert filled[col].isna().sum() == 0

    pauillac_robert = filled[filled["Appellation"] == "Pauillac"]["Robert"]
    assert (pauillac_robert == 95.0).all()


def test_encode_appellation(cleaning_raw: Cleaning):
    cleaning_raw._vins["Appellation"] = cleaning_raw._vins["Appellation"].str.strip()

    out = (
        cleaning_raw.drop_empty_appellation()
        .fill_missing_scores()
        .encode_appellation()
        .getVins()
    )
    assert "Appellation" not in out.columns
    assert "Pauillac" in out.columns
    assert int(out.loc[0, "Pauillac"]) == 1
