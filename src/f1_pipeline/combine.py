"""
Combine the separately cleaned tables into one table:
one row per driver per race.

Combining standard: a driver-race is kept only if it passes EVERY filter.
    1. The race is in good_races (race-level filter: 2011+, no short races)
    2. The driver is in results_clean (finished the race)
    3. The driver has at least one stop in pit_stops_clean (no outlier stops)
This is done with inner joins on raceId + driverId.

Each table is summarized to one row per driver per race BEFORE joining,
so no rows get repeated (every lap x every pit stop).
"""

import pandas as pd

KEYS = ["raceId", "driverId"]


def summarize_lap_times(lap_times):
    """
    Typical lap time per driver per race.

    Uses the median, because pit laps and safety car laps are much slower
    and would pull an average up.

    :param lap_times: lap_times DataFrame (raceId, driverId, lap, milliseconds)
    :return: DataFrame with raceId, driverId, median_lap_s, laps_completed
    """
    out = lap_times.groupby(KEYS).agg(
        median_lap_s=("milliseconds", "median"),
        laps_completed=("lap", "max"),
    ).reset_index()
    out["median_lap_s"] = out["median_lap_s"] / 1000
    return out


def summarize_pit_stops(pit_stops):
    """
    Pit stop summary per driver per race.

    :param pit_stops: cleaned pit_stops DataFrame (raceId, driverId, milliseconds)
    :return: DataFrame with raceId, driverId, mean_pit_s, n_stops
    """
    out = pit_stops.groupby(KEYS).agg(
        mean_pit_s=("milliseconds", "mean"),
        n_stops=("milliseconds", "size"),
    ).reset_index()
    out["mean_pit_s"] = out["mean_pit_s"] / 1000
    return out


def _join_and_report(left, right, step_name):
    """Inner join on raceId + driverId and print how many rows were dropped."""
    before = len(left)
    out = left.merge(right, on=KEYS, how="inner")
    print(f"{step_name}: {before} -> {len(out)} rows ({before - len(out)} dropped)")
    return out


def build_driver_race_table(good_races, results_clean, pit_stops_clean, lap_times):
    """
    Combine all cleaned data into one table, one row per driver per race.

    :param good_races: races kept by the race-level filter (raceId, year, round, name)
    :param results_clean: results of finishers only
    :param pit_stops_clean: pit stops without outliers
    :param lap_times: raw lap_times (only rows matching kept driver-races survive)
    :return: combined DataFrame sorted by year, round and finishing position
    """
    races = good_races[["raceId", "year", "round", "name"]]
    results = results_clean[KEYS + ["constructorId", "grid", "positionOrder"]]

    # Step 1: results only from good races
    before = len(results)
    table = results.merge(races, on="raceId", how="inner")
    print(f"Good races only: {before} -> {len(table)} rows ({before - len(table)} dropped)")

    # Step 2 and 3: must also have clean pit stops and lap times
    table = _join_and_report(table, summarize_pit_stops(pit_stops_clean), "Has clean pit stops")
    table = _join_and_report(table, summarize_lap_times(lap_times), "Has lap times")

    # Safety check: each driver should appear only once per race
    n_dupes = table.duplicated(subset=KEYS).sum()
    if n_dupes > 0:
        raise ValueError(f"{n_dupes} repeated driver-race rows found")

    # Readable column order, sorted in time order
    cols = ["raceId", "year", "round", "name", "driverId", "constructorId",
            "grid", "positionOrder", "median_lap_s", "laps_completed",
            "mean_pit_s", "n_stops"]
    table = table[cols].sort_values(["year", "round", "positionOrder"]).reset_index(drop=True)

    print(f"Final: {len(table)} driver-race rows from {table['raceId'].nunique()} races")
    return table
