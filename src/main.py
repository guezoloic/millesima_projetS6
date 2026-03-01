#!/usr/bin/env python3

from os import getcwd
from os.path import normpath, join
from sys import argv
from pandas import read_csv, DataFrame

def main() -> None:
    if len(argv) != 2:
        raise ValueError(f"{argv[0]} <filename.csv>")

    path: str = normpath(join(getcwd(), argv[1]))
    db: DataFrame = read_csv(path)
    print(db.all())

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERREUR: {e}")