# psycF1: Do Faster Pit Stops Win the Race?

Collaboration project for **PSYC 40650: Principles of Data Science and Engineering for Laboratory Research**.

We use Formula 1 data from 2011 to 2024 to ask two questions:

1. Which teams have the **fastest and most consistent** pit stops?
2. Do **faster pit stops lead to better results**, even after accounting for car pace?

**Hypothesis:** pit stop speed has little to no effect on results.

---

## Quick start

```bash
# 1. Clone the repo
git clone git@github.com:Holleyju/psycF1.git
cd psycF1

# 2. Create and activate the conda environment
conda env create -f environment.yml
conda activate f1_pipeline

# 3. Install the project package (editable, so code changes apply immediately)
pip install -e .
```

Then open the notebooks in `notebooks/` with the **f1_pipeline** kernel and run them in the order listed in [Pipeline](#pipeline).

If you pull changes that update `environment.yml`, run:

```bash
conda env update -f environment.yml --prune
```

---

## Data

**Source:** [Formula 1 World Championship (1950–2024)](https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020) on Kaggle (Ergast database).

The raw CSVs are included in `data/raw/`, so no download is needed. The files we use:

| File | Used for |
|---|---|
| `races.csv` | Year, round and race name; filtering to 2011+ |
| `lap_times.csv` | Laps completed per race; typical lap time (car pace) |
| `results.csv` | Start position, finish position, team |
| `status.csv` | Finished vs. not finished |
| `pit_stops.csv` | Pit stop times (the main variable) |
| `constructors.csv` | Team names for plots |
| `drivers.csv` | Driver names for plots |

**Note:** missing values in the raw files are stored as the text `\N`. Always read them with:

```python
pd.read_csv(path, na_values="\\N")
```

---

## Repository structure

```
psycF1/
├── data/
│   ├── raw/                  # original Kaggle CSVs
│   └── processed/            # cleaned outputs from the pipeline
├── figures/                  # saved plots (PDF) + the data behind each plot (CSV)
├── notebooks/                # one notebook per pipeline step
├── src/f1_pipeline/          # installable package: all reusable functions
│   ├── __init__.py
│   ├── filter_races.py       # race-level filters
│   ├── transform.py          # row-level cleaning helpers
│   ├── combine.py            # combine cleaned tables into one table
│   ├── normalization.py      # compare each driver to the race median
│   └── plotting.py           # plotting functions (save PDF + CSV)
├── environment.yml           # conda environment
├── setup.py                  # package installation
└── README.md
```

**Design rule:** functions live in `src/f1_pipeline/`, and notebooks only load data, call those functions, check the results and save outputs.

---

## Pipeline

Run the notebooks in this order. Each step reads from `data/raw/` or `data/processed/` and writes its output to `data/processed/` or `figures/`.

| Step | Notebook | Output |
|---|---|---|
| 1. Filter races | `filter_race_laptime.ipynb` | `good_races.csv` |
| 2. Clean results and pit stops | `clean_resultspitstops.ipynb` | `results_clean.csv`, `pit_stops_clean.csv` |
| 3. Combine | `combine_newdata.ipynb` | `driver_race_table.csv` |
| 4. Normalize | `normalization_average.ipynb` | `driver_race_table.csv` (adds 2 columns) |
| 5. Plots 3 and 4 | `plot34.ipynb` | `figures/plot3_*`, `figures/plot4_*` |

### Step 1: Race-level filters (`filter_races.py`)

- **Keep 2011 onward**, because pit stop data starts in 2011. We filter by `year`, not `raceId`, because `raceId` is not in time order. (1,125 → 286 races)
- **Remove abnormal races** that completed less than 50% of the usual laps at that circuit (usual = median laps at the same circuit, 2011+). Only the 2021 Belgian GP was removed (1 of 44 laps).
- **Result: 285 races.**

### Step 2: Row-level filters

- **Results:** joined with `status`, kept finishers only (`statusId = 1`, "Finished"). 26,759 → 7,674 rows.
- **Pit stops:** used the `milliseconds` column. Dropped stops over 2 minutes (red-flag waits), recomputed each race's median, then dropped stops over 2× the race median. 11,371 → 10,816 stops (4.9% dropped).

### Step 3: Combine (`combine.py`)

**Combining standard:** a driver-race is kept only if it passes **every** filter. Tables are summarized to one row per driver per race first, then joined with **inner joins on `raceId` + `driverId`**. The code raises an error if any driver appears twice in the same race.

### Step 4: Normalize (`normalization.py`)

Pit lane length differs by circuit, so raw pit times can't be compared across races. Each driver is compared to the **median driver in the same race**:

```
pit_vs_race_s = driver's mean pit time − race median pit time
lap_vs_race_s = driver's median lap time − race median lap time
```

Negative = faster than the typical driver in that race. Positive = slower.

---

## Final dataset: `data/processed/driver_race_table.csv`

One row per driver per race: **3,023 rows from 285 races.**

| Column | Meaning |
|---|---|
| `raceId`, `year`, `round`, `race_name` | Which race |
| `driverId`, `team_id` | Which driver and team |
| `start_position` | Grid position |
| `final_rank` | Finishing position |
| `positions_gained` | `start_position − final_rank` (positive = moved forward) |
| `median_lap_s` | Driver's typical lap time in the race (s) |
| `laps_completed` | Laps completed |
| `mean_pit_s` | Average pit lane time per stop (s) |
| `n_stops` | Number of pit stops |
| `pit_vs_race_s` | Pit time minus race median (s); negative = faster |
| `lap_vs_race_s` | Lap time minus race median (s); negative = faster car pace |

All analysis and plots read from this file only.

---

## Plots

All plot functions take standardized inputs (data, title, labels) and have a `save_path` option that saves both the **PDF** and the **CSV of the plotted data** to `figures/`.

| Plot | Question | Function |
|---|---|---|
| Plot 1 | What does one race look like? (2024 Miami GP) | — |
| Plot 2 | Do faster pit stop groups gain more positions? | — |
| Plot 3 | Which team was fastest and most consistent in 2023? | `plot_team_boxplot` |
| Plot 4 | Does pit speed still matter at equal car pace? | `plot_pace_control` |

Example:

```python
from f1_pipeline.plotting import prepare_team_stops, plot_team_boxplot

stops = prepare_team_stops(pits_clean, results_clean, constructors, good_ids, 2023, races)
plot_team_boxplot(stops, "2023: pit stop speed and consistency by team",