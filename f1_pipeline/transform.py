"""Row-level cleaning steps for the F1 pipeline."""

import pandas as pd

# Default settings live here so they are changed in one place
FINISHED_STATUS_ID = 1      # statusId 1 = "Finished"
OUTLIER_MULTIPLE = 2        # drop stops longer than this x the race median
MAX_STOP_MS = 120000        # hard ceiling: 2 minutes, longer means a stoppage wait


def build_results_table(results, status, finished_status_id=FINISHED_STATUS_ID, verbose=True):
    """Join results with status and keep finishers only."""
    # Count the rows going in so we can report what changed
    rows_in = len(results)

    # Attach the status text to each result row, matching on statusId
    # validate="many_to_one" raises an error if status has duplicate IDs
    merged = results.merge(status, on="statusId", how="left", validate="many_to_one")

    # A join that only adds a column should not change the row count
    if len(merged) != rows_in:
        raise ValueError("Join changed the row count: check for duplicate keys")

    # Keep only finishers (written the plain way, as a True/False column)
    is_finisher = (merged["statusId"] == finished_status_id)
    clean = merged[is_finisher].copy()

    # Print a summary of what happened
    if verbose:
        print("rows in:     ", rows_in)
        print("rows dropped:", rows_in - len(clean))
        print("rows out:    ", len(clean))
        print("share kept:  ", round(len(clean) / rows_in, 3))

    return clean


def build_pit_stops_table(pit_stops, time_col="milliseconds", multiple=OUTLIER_MULTIPLE,
                          max_stop_ms=MAX_STOP_MS, verbose=True):
    """Drop stoppage waits over a ceiling, then stops over `multiple` x their race median."""
    # Work on a copy so the table passed in is never changed
    stops = pit_stops.copy()
    rows_in = len(stops)

    # Pass 1: flag stops longer than the ceiling (red flags and similar waits)
    over_ceiling = (stops[time_col] > max_stop_ms)
    under_ceiling = (over_ceiling == False)

    # Pass 2: each race's median, calculated from the stops under the ceiling only
    # Otherwise a race full of stoppage waits would have an inflated median
    race_median = stops[under_ceiling].groupby("raceId")[time_col].median()

    # Give every stop its own race's median (a race with no stops under the ceiling gets NaN)
    stops["race_median"] = stops["raceId"].map(race_median)
    cutoff = multiple * stops["race_median"]

    # Is the stop at or below its race's cutoff?
    within_cutoff = (stops[time_col] <= cutoff)

    # Keep a stop only if it passes both rules
    is_normal = (under_ceiling & within_cutoff)

    # Remove the helper column so the output has the same columns as the raw table
    clean = stops[is_normal].drop(columns=["race_median"]).copy()

    # Print a summary, split by the reason a stop was dropped
    if verbose:
        n_ceiling = over_ceiling.sum()
        n_multiple = (under_ceiling & (within_cutoff == False)).sum()
        print("rows in:              ", rows_in)
        print("dropped over ceiling: ", n_ceiling)
        print("dropped by median x", multiple, ":", n_multiple)
        print("rows out:             ", len(clean))
        print("share kept:           ", round(len(clean) / rows_in, 3))

    return clean