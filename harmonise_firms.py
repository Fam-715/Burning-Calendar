# ============================================================
# Zero Gravity, Zero Sleep - MODIS / VIIRS hotspot harmonisation
# NASA Space Apps 2026: Harmonization of MODIS and VIIRS Hot Spots
#
# Input : firms_clean/modis_MY_ID.csv, viirs-snpp_MY_ID.csv, viirs-jpss1_MY_ID.csv
#         (optional) firms_2026/*.csv  - FIRMS archive-request files for 2026
# Output: firms_harmonised/harmonised_grid_monthly.csv
#         firms_harmonised/scaling_factors.csv
#         firms_harmonised/validation.csv
#
# Note: this script was written with AI assistance (declare it in the
#       "Use of SI" field of the project page).
# ============================================================
import os, glob
import numpy as np
import pandas as pd

try:                                    # running in Google Colab
    from google.colab import drive
    drive.mount('/content/drive')
    BASE = "/content/drive/MyDrive"
except ImportError:                     # running anywhere else
    BASE = os.environ.get("FIRMS_BASE", ".")

IN_DIR  = f"{BASE}/firms_clean"
NEW_DIR = f"{BASE}/firms_2026"          # optional, may not exist
OUT_DIR = f"{BASE}/firms_harmonised"
os.makedirs(OUT_DIR, exist_ok=True)

# ---------------- settings ----------------
CELL       = 0.25        # grid cell size in degrees (about 28 km)
BLOCK      = 2.0         # scaling factors are learned per 2-degree block
SHRINK     = 200         # pulls blocks with little data towards the regional factor
MODIS_MIN_CONF = 30      # drop MODIS detections below 30% confidence
TRAIN_END  = 2021        # factors learned on 2012-2021, 2022 onwards is a held-out test
VIIRS_START   = "2012-02"   # first full month of S-NPP
N20_START     = "2018-04"   # first full month of NOAA-20
TERRA_ONLY_TO = "2002-07"   # Aqua data begins 4 July 2002

USE = ["latitude", "longitude", "acq_date", "satellite", "instrument",
       "confidence", "daynight", "type"]

# ---------------- 1. load and clean ----------------
def clean(df):
    """Keep vegetation fires with nominal or high confidence."""
    if "type" in df.columns:                       # 0 = vegetation fire
        df = df[df["type"].fillna(0).astype(int) == 0]
    is_modis = df["instrument"].astype(str).str.upper().eq("MODIS")
    conf = df["confidence"].astype(str).str.strip().str.lower()
    conf_num = pd.to_numeric(conf, errors="coerce")
    keep = np.where(is_modis, conf_num >= MODIS_MIN_CONF, ~conf.isin(["l", "low"]))
    return df[keep]

def sensor_of(df):
    sat = df["satellite"].astype(str).str.strip().str.upper()
    return np.select(
        [sat.eq("TERRA") | sat.eq("T"), sat.eq("AQUA") | sat.eq("A"),
         sat.isin(["N", "SNPP", "SUOMI NPP"]), sat.isin(["N20", "NOAA-20", "1"]),
         sat.isin(["N21", "NOAA-21", "2"])],
        ["terra", "aqua", "snpp", "n20", "n21"], default="other")

def load(path):
    head = pd.read_csv(path, nrows=0).columns
    df = pd.read_csv(path, usecols=[c for c in USE if c in head],
                     dtype={"confidence": str}, low_memory=False)
    n0 = len(df)
    df = clean(df)
    df["sensor"] = sensor_of(df)
    print(f"  {os.path.basename(path):32s} {n0:>9,} rows -> {len(df):>9,} kept")
    return df[["latitude", "longitude", "acq_date", "daynight", "sensor"]]

print("Loading and cleaning")
parts = [load(f"{IN_DIR}/{n}_MY_ID.csv") for n in ["modis", "viirs-snpp", "viirs-jpss1"]]
last_yearly = max(p["acq_date"].max() for p in parts)
for p in sorted(glob.glob(f"{NEW_DIR}/*.csv")):     # optional 2026 request files
    extra = load(p)
    parts.append(extra[extra["acq_date"] > last_yearly])   # avoid double counting
pts = pd.concat(parts, ignore_index=True)
pts = pts[pts["sensor"].isin(["terra", "aqua", "snpp", "n20"])]
pts = pts.drop_duplicates()

# ---------------- 2. grid: cell x month x day/night ----------------
pts["ym"] = pts["acq_date"].str[:7]
pts["gy"] = np.floor(pts["latitude"] / CELL).astype(int)
pts["gx"] = np.floor(pts["longitude"] / CELL).astype(int)
key = ["ym", "gy", "gx", "daynight"]
grid = (pts.groupby(key + ["sensor"]).size().unstack("sensor", fill_value=0)
           .reindex(columns=["terra", "aqua", "snpp", "n20"], fill_value=0)
           .reset_index())
grid["modis"] = grid["terra"] + grid["aqua"]
grid["year"]  = grid["ym"].str[:4].astype(int)
grid["by"] = np.floor(grid["gy"] * CELL / BLOCK).astype(int)
grid["bx"] = np.floor(grid["gx"] * CELL / BLOCK).astype(int)

# VIIRS reference: S-NPP until March 2018, NOAA-20 afterwards
# (S-NPP has outages, e.g. Aug 2022 and Jul 2024, and stopped in Nov 2026)
grid["viirs"] = np.where(grid["ym"] < N20_START, grid["snpp"], grid["n20"])
print(f"\nGrid: {len(grid):,} cell-months, {grid.groupby(['gy','gx']).ngroups:,} cells, "
      f"{grid['ym'].min()} to {grid['ym'].max()}")

both = grid[(grid["ym"] >= N20_START) & (grid["year"] <= 2025)].groupby("ym")[["snpp", "n20"]].sum()
print(f"S-NPP vs NOAA-20 monthly: correlation {np.corrcoef(both.snpp, both.n20)[0,1]:.4f}, "
      f"NOAA-20/S-NPP = {both.n20.sum()/both.snpp.sum():.3f}")

# ---------------- 3. learn the scaling factors ----------------
def fit(train, col):
    """VIIRS-per-MODIS factor for each day/night x 2-degree block."""
    r0 = train.groupby("daynight")["viirs"].sum() / train.groupby("daynight")[col].sum()
    f = train.groupby(["daynight", "by", "bx"])[["viirs", col]].sum()
    f["r0"] = f.index.get_level_values("daynight").map(r0)
    f["factor"] = (f["viirs"] + SHRINK * f["r0"]) / (f[col] + SHRINK)
    return r0, f[["factor"]]

def predict(df, col, r0, f):
    fac = df.merge(f, left_on=["daynight", "by", "bx"], right_index=True, how="left")["factor"]
    fac.index = df.index
    return df[col] * fac.fillna(df["daynight"].map(r0))

overlap = grid[(grid["ym"] >= VIIRS_START) & (grid["year"] <= 2025)]
train   = overlap[overlap["year"] <= TRAIN_END]
test    = overlap[overlap["year"] >  TRAIN_END]

# ---------------- 4. validate ----------------
def wape(df, pred, keys):
    a = df.groupby(keys)["viirs"].sum()
    p = df.assign(p=pred).groupby(keys)["p"].sum()
    return float(np.abs(a - p).sum() / a.sum())

LEVELS = {"whole region, monthly": ["ym"], "whole region, yearly": ["year"],
          "2-degree block, monthly": ["ym", "by", "bx"],
          "0.25-degree cell, monthly": ["ym", "gy", "gx"]}
rows = []
for col, label in [("modis", "Terra+Aqua"), ("terra", "Terra only")]:
    cv = pd.Series(0.0, index=train.index)          # leave one year out
    for y in sorted(train["year"].unique()):
        r0, f = fit(train[train["year"] != y], col)
        cv.loc[train["year"] == y] = predict(train[train["year"] == y], col, r0, f)
    r0, f = fit(train, col)
    ho = predict(test, col, r0, f)
    m = train.assign(p=cv).groupby("ym")[["viirs", "p"]].sum()
    for lvl, keys in LEVELS.items():
        rows.append({"input": label, "level": lvl,
                     f"error_leave_one_year_out_2012_{TRAIN_END}": round(wape(train, cv, keys), 3),
                     f"error_holdout_{TRAIN_END+1}_2025": round(wape(test, ho, keys), 3)})
    print(f"\n{label}: monthly R2 = {np.corrcoef(m.viirs, m.p)[0,1]**2:.3f}")
    yr = pd.concat([train.assign(p=cv), test.assign(p=ho)]).groupby("year")[["viirs", "p"]].sum()
    print("  predicted / actual by year:", (yr.p / yr.viirs).round(2).to_dict())
val = pd.DataFrame(rows)
val.to_csv(f"{OUT_DIR}/validation.csv", index=False)
print("\nError = sum of absolute errors / total hotspots (0.10 means 10% off)")
print(val.to_string(index=False))

# ---------------- 5. build the harmonised series ----------------
r0_m, f_m = fit(train, "modis")
r0_t, f_t = fit(train, "terra")
grid["hotspots"] = np.select(
    [grid["ym"] <= TERRA_ONLY_TO, grid["ym"] < VIIRS_START],
    [predict(grid, "terra", r0_t, f_t), predict(grid, "modis", r0_m, f_m)],
    default=grid["viirs"]).round(2)
grid["source"] = np.select(
    [grid["ym"] <= TERRA_ONLY_TO, grid["ym"] < VIIRS_START, grid["ym"] < N20_START],
    ["MODIS Terra scaled", "MODIS scaled", "VIIRS S-NPP"], default="VIIRS NOAA-20")

out = grid.assign(lat=(grid["gy"] + 0.5) * CELL, lon=(grid["gx"] + 0.5) * CELL,
                  month=grid["ym"].str[5:].astype(int))
out = out[["ym", "year", "month", "lat", "lon", "daynight", "hotspots", "source",
           "modis", "snpp", "n20"]].rename(
           columns={"modis": "modis_raw", "snpp": "snpp_raw", "n20": "n20_raw"})
out.to_csv(f"{OUT_DIR}/harmonised_grid_monthly.csv", index=False)

fac = (f_m.rename(columns={"factor": "factor_terra_aqua"})
          .join(f_t.rename(columns={"factor": "factor_terra_only"})).reset_index())
fac["lat_from"] = fac["by"] * BLOCK; fac["lon_from"] = fac["bx"] * BLOCK
fac.drop(columns=["by", "bx"]).round(3).to_csv(f"{OUT_DIR}/scaling_factors.csv", index=False)

print("\nRegional factors (VIIRS-equivalent hotspots per MODIS hotspot):")
print("  Terra+Aqua:", r0_m.round(2).to_dict(), "| Terra only:", r0_t.round(2).to_dict())
yearly = out.groupby("year")[["modis_raw", "snpp_raw", "n20_raw", "hotspots"]].sum().round(0).astype(int)
print("\nYearly totals, raw vs harmonised:")
print(yearly.to_string())
print(f"\nSaved {len(out):,} rows to {OUT_DIR}/harmonised_grid_monthly.csv")
