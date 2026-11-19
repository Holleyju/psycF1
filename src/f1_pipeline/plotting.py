"""
Report step: plotting functions for the F1 pit stop project.

Plot 3: plot_team_boxplot   -> which team is fastest and most consistent?
Plot 4: plot_pace_control   -> is it the pit crew, or just the fast car?

Every plot function:
    - takes standardized inputs (data, title, labels)
    - has a save_path option: saves the figure as PDF AND the plotted data as CSV
"""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

# Save text in PDFs as editable text (for Illustrator), as in the Week 6 slides
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42


def save_figure(fig, data, save_path):
    """
    Save a figure as PDF and the data that went into it as CSV.

    :param fig: matplotlib Figure
    :param data: DataFrame used to make the plot
    :param save_path: path without extension, e.g. "../figures/plot3_team_box"
    """
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path.with_suffix(".pdf"), bbox_inches="tight")
    data.to_csv(save_path.with_suffix(".csv"), index=False)
    print(f"Saved {save_path.with_suffix('.pdf')} and {save_path.with_suffix('.csv')}")



def prepare_team_stops(pit_stops_clean, results_clean, constructors, good_race_ids, season, races):
    """
    One row per pit stop for one season, with team name and normalized time.

    :param pit_stops_clean: cleaned pit stops (raceId, driverId, milliseconds)
    :param results_clean: cleaned results (raceId, driverId, constructorId)
    :param constructors: constructors table (constructorId, name)
    :param good_race_ids: raceId values kept by the race filter
    :param season: year to plot, e.g. 2023
    :param races: races table (raceId, year)
    :return: DataFrame with team, pit_s, pit_vs_race_s
    """
    season_ids = races.loc[races["year"] == season, "raceId"]
    stops = pit_stops_clean[pit_stops_clean["raceId"].isin(good_race_ids)
                            & pit_stops_clean["raceId"].isin(season_ids)].copy()

    # Attach team to each stop (pit_stops has no team column)
    stops = stops.merge(results_clean[["raceId", "driverId", "constructorId"]],
                        on=["raceId", "driverId"], how="inner")
    stops = stops.merge(constructors[["constructorId", "name"]], on="constructorId")
    stops = stops.rename(columns={"name": "team"})

    # Compare each stop to the median stop of the same race
    stops["pit_s"] = stops["milliseconds"] / 1000
    stops["pit_vs_race_s"] = stops["pit_s"] - stops.groupby("raceId")["pit_s"].transform("median")
    return stops[["raceId", "driverId", "team", "pit_s", "pit_vs_race_s"]]


def plot_team_boxplot(stops, title,
                      xlabel="Pit stop time vs race median (s)\n(left = faster, narrow box = more consistent)",
                      save_path=None):
    """
    Box plot of normalized pit stop times per team, fastest team at the top.

    Box position = how fast the team is. Box width = how consistent it is.

    :param stops: output of prepare_team_stops
    :param title: plot title (state the message)
    :param xlabel: x-axis label
    :param save_path: optional path without extension to save PDF + CSV
    :return: matplotlib Figure
    """
    order = stops.groupby("team")["pit_vs_race_s"].median().sort_values().index
    groups = [stops.loc[stops["team"] == t, "pit_vs_race_s"] for t in order]

    fig, ax = plt.subplots(figsize=(8, 0.45 * len(order) + 1.5))
    ax.boxplot(groups, vert=False, showfliers=False, widths=0.6,
               patch_artist=True, boxprops=dict(facecolor="#9ecae1"),
               medianprops=dict(color="black"))
    ax.set_yticks(range(1, len(order) + 1))
    ax.set_yticklabels(order)
    ax.invert_yaxis()                      # fastest team at the top
    ax.axvline(0, color="grey", linestyle="--", linewidth=1)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    fig.tight_layout()

    if save_path:
        save_figure(fig, stops, save_path)
    return fig



def remove_effect(y, x):
    """
    Remove the linear effect of x from y (regression residuals).

    :param y: values to adjust (Series)
    :param x: values whose effect is removed (Series)
    :return: residuals of y after fitting y = a + b * x
    """
    slope, intercept = np.polyfit(x, y, 1)
    return y - (intercept + slope * x)


def _scatter_with_fit(ax, x, y, title, xlabel, ylabel):
    """Scatter plot with a regression line and slope / correlation in the corner."""
    ax.scatter(x, y, s=6, alpha=0.15, color="#3182bd")
    slope, intercept = np.polyfit(x, y, 1)
    xs = np.linspace(x.min(), x.max(), 100)
    ax.plot(xs, intercept + slope * xs, color="#de2d26", linewidth=2)
    r, p = stats.pearsonr(x, y)
    ax.text(0.03, 0.97, f"slope = {slope:.2f} positions / s\nr = {r:.2f}, p = {p:.3g}",
            transform=ax.transAxes, va="top", fontsize=9,
            bbox=dict(facecolor="white", alpha=0.8, edgecolor="none"))
    ax.axhline(0, color="grey", linewidth=0.8)
    ax.axvline(0, color="grey", linewidth=0.8)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)


def plot_pace_control(table, title, save_path=None):
    """
    Two panels: pit time vs positions gained, before and after removing car pace.

    Right panel removes the effect of lap_vs_race_s from BOTH pit time and
    positions gained, so it shows the pit stop effect at equal car pace.
    Its slope equals the pit coefficient in a regression with both predictors.

    :param table: driver-race table with pit_vs_race_s, lap_vs_race_s, positions_gained
    :param title: overall figure title (state the message)
    :param save_path: optional path without extension to save PDF + CSV
    :return: matplotlib Figure
    """
    df = table.dropna(subset=["pit_vs_race_s", "lap_vs_race_s", "positions_gained"]).copy()
    df["pit_adjusted"] = remove_effect(df["pit_vs_race_s"], df["lap_vs_race_s"])
    df["gained_adjusted"] = remove_effect(df["positions_gained"], df["lap_vs_race_s"])

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=False)
    _scatter_with_fit(axes[0], df["pit_vs_race_s"], df["positions_gained"],
                      "Before: raw relationship",
                      "Pit stop time vs race median (s)", "Positions gained")
    _scatter_with_fit(axes[1], df["pit_adjusted"], df["gained_adjusted"],
                      "After: car pace removed",
                      "Pit stop time, adjusted for pace (s)", "Positions gained, adjusted for pace")
    fig.suptitle(title)
    fig.tight_layout()

    if save_path:
        cols = ["raceId", "driverId", "pit_vs_race_s", "lap_vs_race_s",
                "positions_gained", "pit_adjusted", "gained_adjusted"]
        save_figure(fig, df[[c for c in cols if c in df.columns]], save_path)
    return fig