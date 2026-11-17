"""
Race-level filters:

By using the races and lap_times tables, decide which races to keep for pit stop analysis.
keep races from 2011 onward and remove abnormal races that completed far fewer laps than usual
"""

import pandas as pd


def keep_modern_races(races, first_year=2011):
    """
    Keep only races from first_year onward.

    Uses the year column, not raceId, because raceId is not in time order.

    :param races: races DataFrame with raceId and year columns
    :param first_year: first season to keep (default 2011, first year of pit data)
    :return: races DataFrame with only the kept seasons
    """
    kept = races[races["year"] >= first_year].copy()
    print(f"Step 1: kept {len(kept)} of {len(races)} races (year >= {first_year})")
    return kept


def count_laps_per_race(lap_times):
    """
    Count how many laps were completed in each race.

    :param lap_times: lap_times DataFrame with raceId and lap columns
    :return: Series indexed by raceId with the number of laps completed
    """
    return lap_times.groupby("raceId")["lap"].max().rename("laps_completed")


def remove_short_races(races, lap_times, min_fraction=0.5):
    """
    Remove races that completed far fewer laps than usual at that circuit.

    The usual number of laps is the median laps completed at the same circuit
    across all kept seasons. A race is removed if it completed less than
    min_fraction of that number (e.g. 2021 Belgian GP).

    :param races: races DataFrame with raceId and circuitId columns
    :param lap_times: lap_times DataFrame with raceId and lap columns
    :param min_fraction: minimum share of usual laps to keep a race (default 0.5)
    :return: races DataFrame without abnormal races, with lap count columns added
    """
    laps = count_laps_per_race(lap_times)
    df = races.merge(laps, on="raceId", how="left")

    # Races with no lap data cannot be checked, so they are removed
    missing = df["laps_completed"].isna()
    if missing.any():
        print(f"Step 2: removed {missing.sum()} races with no lap time data")
    df = df[~missing].copy()

    # Usual laps at each circuit, and how much of it each race completed
    df["usual_laps"] = df.groupby("circuitId")["laps_completed"].transform("median")
    df["lap_fraction"] = df["laps_completed"] / df["usual_laps"]

    short = df["lap_fraction"] < min_fraction
    print(f"Step 2: removed {short.sum()} short races (< {min_fraction:.0%} of usual laps):")
    print(df.loc[short, ["raceId", "year", "name", "laps_completed", "usual_laps"]]
          .to_string(index=False))

    return df[~short]


def get_good_race_ids(races, lap_times, first_year=2011, min_fraction=0.5):
    """
    Run Step 1 and Step 2 and return the race IDs to keep.

    :param races: races DataFrame
    :param lap_times: lap_times DataFrame
    :param first_year: first season to keep
    :param min_fraction: minimum share of usual laps to keep a race
    :return: list of raceId values that passed both filters
    """
    modern = keep_modern_races(races, first_year)
    good = remove_short_races(modern, lap_times, min_fraction)
    print(f"Final: {len(good)} races kept")
    return good["raceId"].tolist()
