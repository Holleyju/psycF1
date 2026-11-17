"""
Compute step: make drivers comparable across different races.

Each driver is compared to the median driver in the SAME race, so track
length and pit lane length no longer matter.
    negative value = faster than the typical driver in that race
    positive value = slower than the typical driver in that race
"""


def relative_to_race(table, column):
    """
    Subtract the race median from a column.

    :param table: driver-race table with a raceId column
    :param column: name of the column to normalize (e.g. "mean_pit_s")
    :return: Series of differences from the race median (same units)
    """
    race_median = table.groupby("raceId")[column].transform("median")
    return table[column] - race_median


def add_race_relative_columns(table):
    """
    Add normalized pit time and lap time columns to the driver-race table.

    New columns:
        pit_vs_race_s: pit time minus race median pit time (seconds)
        lap_vs_race_s: lap time minus race median lap time (seconds)

    :param table: combined driver-race table (from combine.py)
    :return: copy of the table with the two new columns
    """
    out = table.copy()
    out["pit_vs_race_s"] = relative_to_race(out, "mean_pit_s")
    out["lap_vs_race_s"] = relative_to_race(out, "median_lap_s")
    return out