# ============================================================
# Burning Calendar - Zero Gravity, Zero Sleep
# NASA Space Apps 2026: Harmonization of MODIS and VIIRS Hot Spots
#
# Reads data/harmonised_grid_monthly.csv.gz (built by harmonise_firms.py)
# Run locally:  streamlit run app.py
# Note: written with AI assistance (declared on the project page).
# ============================================================
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

import space_ui as ui
from space_ui import BLUE, ORANGE, GREY, INK2

st.set_page_config(page_title="Burning Calendar", page_icon="🔥", layout="wide")

DATA = Path(__file__).parent / "data"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
SMALL_AREA_DEG2 = 4          # below this the estimate gets noticeably less reliable

# name -> (country filter, south, north, west, east)
AREAS = {
    "Malaysia and Indonesia": (None, -11.0, 7.5, 95.0, 141.0),
    "Malaysia": ("Malaysia", 0.5, 7.5, 99.5, 119.5),
    "Indonesia": ("Indonesia", -11.0, 6.0, 95.0, 141.0),
    "Peninsular Malaysia": ("Malaysia", 1.0, 7.0, 99.5, 104.75),
    "Sabah and Sarawak": ("Malaysia", 0.75, 7.5, 109.5, 119.5),
    "Sumatra": ("Indonesia", -6.0, 6.0, 95.0, 106.75),
    "Kalimantan": ("Indonesia", -4.5, 4.5, 108.5, 119.0),
    "Papua": ("Indonesia", -9.5, 0.0, 130.5, 141.0),
}


@st.cache_data(show_spinner="Loading 25 years of hotspots…")
def load_grid():
    df = pd.read_csv(DATA / "harmonised_grid_monthly.csv.gz")
    df["viirs_raw"] = np.where(df["ym"] < "2018-04", df["snpp_raw"], df["n20_raw"])
    return df


@st.cache_data
def load_validation():
    return pd.read_csv(DATA / "validation.csv")


def source_of(ym):
    if ym <= "2002-07":
        return "MODIS Terra, scaled to VIIRS"
    if ym < "2012-02":
        return "MODIS Terra + Aqua, scaled to VIIRS"
    if ym < "2018-04":
        return "VIIRS S-NPP, observed"
    return "VIIRS NOAA-20, observed"


grid = load_grid()
first_ym, last_ym = grid["ym"].min(), grid["ym"].max()
first_year, last_year = int(first_ym[:4]), int(last_ym[:4])

# ---------------- sidebar: area and period ----------------
st.sidebar.header("Area of interest")
choice = st.sidebar.selectbox("Region", list(AREAS) + ["Custom box (latitude / longitude)"])
if choice in AREAS:
    country, south, north, west, east = AREAS[choice]
    area_name = choice
else:
    pick = st.sidebar.selectbox("Country", ["Both", "Malaysia", "Indonesia"])
    country = None if pick == "Both" else pick
    c1, c2 = st.sidebar.columns(2)
    north = c1.number_input("North", -11.0, 7.5, 3.0, 0.25)
    south = c2.number_input("South", -11.0, 7.5, -3.0, 0.25)
    west = c1.number_input("West", 95.0, 141.0, 100.0, 0.25)
    east = c2.number_input("East", 95.0, 141.0, 105.0, 0.25)
    area_name = f"Custom box {south:g} to {north:g}°N, {west:g} to {east:g}°E"
    if south >= north or west >= east:
        st.sidebar.error("North must be above South, and East must be right of West.")
        st.stop()

st.sidebar.header("Period")
y0, y1 = st.sidebar.slider("Years", first_year, last_year, (min(2001, last_year), last_year))
dn_label = st.sidebar.radio("Time of detection", ["Day and night", "Day only", "Night only"])

sel = grid[grid["lat"].between(south, north) & grid["lon"].between(west, east)]
if country:
    sel = sel[sel["country"] == country]
if dn_label != "Day and night":
    sel = sel[sel["daynight"] == dn_label[0]]

ui.inject_css()
ui.hero(first_year, last_year)
st.caption("All counts are in VIIRS-equivalent hotspots, from NASA FIRMS active-fire data.")

if sel.empty:
    st.info("No hotspots were recorded in this area. Try a larger box or another region.")
    st.stop()

# ---------------- monthly series for the area ----------------
all_months = pd.period_range(first_ym, last_ym, freq="M").strftime("%Y-%m")
m = (sel.groupby("ym")[["hotspots", "modis_raw", "viirs_raw"]].sum()
        .reindex(all_months, fill_value=0).rename_axis("ym").reset_index())
m["year"] = m["ym"].str[:4].astype(int)
m["month"] = m["ym"].str[5:].astype(int)
m["mon"] = m["month"].map(lambda i: MONTHS[i - 1])
m["source"] = m["ym"].map(source_of)
m["usual"] = m.groupby("month")["hotspots"].transform("median")      # median of that calendar month
m["times_usual"] = (m["hotspots"] + 1) / (m["usual"] + 1)
m["log_ratio"] = np.log2(m["times_usual"]).clip(-3, 3)
m["label"] = m["mon"] + " " + m["year"].astype(str)
view = m[m["year"].between(y0, y1)]

months_per_year = view.groupby("year")["month"].count()
full_years = months_per_year[months_per_year == 12].index
annual = view[view["year"].isin(full_years)].groupby("year")[["hotspots", "modis_raw"]].sum()
season = m.groupby("month")["hotspots"].median()
latest = m.iloc[-1]

# ---------------- headline numbers ----------------
k1, k2, k3, k4 = st.columns(4)
total = view["hotspots"].sum()
k1.metric("Total hotspots", f"{total / 1e6:.2f}M" if total >= 1e6 else f"{total:,.0f}")
k1.caption(f"{y0} to {y1}")
if len(annual):
    worst = int(annual["hotspots"].idxmax())
    note = " (estimated from MODIS)" if worst < 2012 else ""
    k2.metric("Worst year", str(worst))
    k2.caption(f"{annual['hotspots'].max():,.0f} hotspots{note}")
k3.metric("Usual peak month", MONTHS[int(season.idxmax()) - 1])
k3.caption(f"median {season.max():,.0f} hotspots")
change = (latest["hotspots"] - latest["usual"]) / latest["usual"] * 100 if latest["usual"] else 0.0
k4.metric(f"Latest: {latest['label']}", f"{latest['hotspots']:,.0f}",
          f"{change:+.0f}% vs usual", delta_color="inverse")

if (north - south) * (east - west) < SMALL_AREA_DEG2:
    st.warning("This is a small area. Before 2012 the counts are estimated from MODIS, and "
               "for areas this small a single month can be off by 30% or more. "
               "Read the pattern, not the exact number.", icon="⚠️")

tab_cal, tab_month, tab_trend, tab_map, tab_method = st.tabs(
    ["Burning calendar", "A month against its history", "Trend and sensors", "Map", "Method and data"])

TIP = [alt.Tooltip("label:N", title="Month"),
       alt.Tooltip("hotspots:Q", title="Hotspots", format=",.0f"),
       alt.Tooltip("usual:Q", title="Usual for this month", format=",.0f"),
       alt.Tooltip("times_usual:Q", title="Times the usual", format=".1f"),
       alt.Tooltip("source:N", title="Source")]

# ---------------- 1. burning calendar ----------------
with tab_cal:
    st.subheader(f"{area_name}: hotspots by month")
    mode = st.radio("Colour shows", ["Number of hotspots", "Compared with the usual for that month"],
                    horizontal=True, label_visibility="collapsed")
    ui.calendar(view, by_count=(mode == "Number of hotspots"))
    st.caption("Each square is one month. Hover over a square to lift it and see the figures. Before February 2012 the counts are "
               "MODIS detections scaled to VIIRS-equivalent; from then on they are VIIRS observations. "
               "\"Usual\" is the median for that calendar month across the whole record.")

    with st.expander("Show as a table"):
        table = view.pivot(index="year", columns="mon", values="hotspots").reindex(columns=MONTHS)
        st.dataframe(table.round(0), width="stretch")

    d1, d2 = st.columns(2)
    cal_csv = view[["ym", "year", "month", "hotspots", "usual", "times_usual",
                    "modis_raw", "viirs_raw", "source"]].round(2)
    d1.download_button("Download this calendar (CSV)", cal_csv.to_csv(index=False),
                       "burning_calendar.csv", "text/csv")
    cells = sel[sel["year"].between(y0, y1)].drop(columns=["snpp_raw", "n20_raw"])
    d2.download_button("Download gridded hotspots for this search (CSV)", cells.to_csv(index=False),
                       "hotspots_grid.csv", "text/csv")

# ---------------- 2. one month against its history ----------------
with tab_month:
    s1, s2, _ = st.columns([1, 1, 3])
    pick_month = s1.selectbox("Month", MONTHS, index=int(latest["month"]) - 1)
    years_with = m[m["mon"] == pick_month]["year"].tolist()
    pick_year = s2.selectbox("Year", years_with[::-1])
    hist = m[m["mon"] == pick_month].copy()
    row = hist[hist["year"] == pick_year].iloc[0]
    hist["which"] = np.where(hist["year"] == pick_year, str(pick_year), "Other years")

    a, b, c = st.columns(3)
    a.metric(f"{pick_month} {pick_year}", f"{row['hotspots']:,.0f}")
    b.metric(f"Usual {pick_month} (median, {first_year}–{last_year})", f"{row['usual']:,.0f}")
    diff = (row["hotspots"] - row["usual"]) / row["usual"] * 100 if row["usual"] else 0.0
    c.metric("Difference", f"{diff:+.0f}%")
    c.caption(f"{row['times_usual']:.1f} times the usual")

    st.subheader(f"Every {pick_month} since {hist['year'].min()}")
    bars = (alt.Chart(hist).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(x=alt.X("year:O", title=None, axis=alt.Axis(labelAngle=0, labelOverlap=True)),
                    y=alt.Y("hotspots:Q", title="Hotspots", axis=alt.Axis(format="~s")),
                    color=alt.Color("which:N", scale=alt.Scale(domain=[str(pick_year), "Other years"],
                                                               range=[BLUE, GREY]),
                                    legend=alt.Legend(title=None, orient="top")),
                    tooltip=TIP))
    med = pd.DataFrame({"usual": [row["usual"]]})
    rule = alt.Chart(med).mark_rule(color=INK2, strokeWidth=1.5).encode(y="usual:Q")
    st.altair_chart((bars + rule).properties(height=320), width="stretch")
    st.caption(f"The horizontal line is the median {pick_month} ({row['usual']:,.0f} hotspots).")

    st.subheader("When the fire season usually falls")
    seas = pd.DataFrame({"mon": MONTHS, "median": season.reindex(range(1, 13)).values})
    seas_chart = (alt.Chart(seas).mark_bar(color=BLUE, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                  .encode(x=alt.X("mon:O", sort=MONTHS, title=None, axis=alt.Axis(labelAngle=0)),
                          y=alt.Y("median:Q", title="Median hotspots", axis=alt.Axis(format="~s")),
                          tooltip=[alt.Tooltip("mon:N", title="Month"),
                                   alt.Tooltip("median:Q", title="Median hotspots", format=",.0f")])
                  .properties(height=240))
    st.altair_chart(seas_chart, width="stretch")

# ---------------- 3. trend and sensors ----------------
with tab_trend:
    st.subheader("Why the two sensors cannot simply be joined")
    if len(annual) < 2:
        st.info("Choose at least two full years to see the trend.")
    else:
        long = (annual.rename(columns={"hotspots": "Harmonised", "modis_raw": "Raw MODIS"})
                      .reset_index().melt("year", var_name="series", value_name="count"))
        scale = alt.Scale(domain=["Harmonised", "Raw MODIS"], range=[BLUE, ORANGE])
        lines = (alt.Chart(long).mark_line(strokeWidth=2, point=alt.OverlayMarkDef(size=45))
                 .encode(x=alt.X("year:O", title=None, axis=alt.Axis(labelAngle=0, labelOverlap=True)),
                         y=alt.Y("count:Q", title="Hotspots per year", axis=alt.Axis(format="~s")),
                         color=alt.Color("series:N", scale=scale, legend=alt.Legend(title=None, orient="top")),
                         tooltip=[alt.Tooltip("year:O", title="Year"), alt.Tooltip("series:N", title="Series"),
                                  alt.Tooltip("count:Q", title="Hotspots", format=",.0f")]))
        ends = (alt.Chart(long[long["year"] == long["year"].max()])
                .mark_text(align="left", dx=8, color=INK2)
                .encode(x="year:O", y="count:Q", text="series:N"))
        st.altair_chart((lines + ends).properties(height=360, padding={"right": 80}), width="stretch")
        ratio = annual["hotspots"].sum() / max(annual["modis_raw"].sum(), 1)
        st.markdown(
            f"In this area VIIRS records about **{ratio:.1f} times** as many hotspots as MODIS, because its "
            "375 m pixels catch small fires that MODIS's 1 km pixels miss. Switching sensors in 2012 without "
            "correction would look like a sudden jump in burning. The harmonised line removes that jump, so "
            "years before and after 2012 can be compared directly.")

# ---------------- 4. map ----------------
with tab_map:
    st.subheader(f"Where the hotspots were, {y0} to {y1}")
    cells_sum = (sel[sel["year"].between(y0, y1)].groupby(["lat", "lon"], as_index=False)["hotspots"].sum())
    top = cells_sum["hotspots"].max()
    cells_sum["radius"] = 3000 + 10000 * np.sqrt(cells_sum["hotspots"] / top)
    cells_sum["text"] = cells_sum["hotspots"].map(lambda v: f"{v:,.0f} hotspots")
    # darker = more hotspots, so the pattern still shows when zoomed far out
    cells_sum["colour"] = [[255, 138, 61, int(a)] for a in 45 + 200 * np.sqrt(cells_sum["hotspots"] / top)]
    box = pd.DataFrame({"path": [[[west, south], [east, south], [east, north], [west, north], [west, south]]]})
    layers = [
        pdk.Layer("ScatterplotLayer", cells_sum, get_position="[lon, lat]", get_radius="radius",
                  get_fill_color="colour", radius_min_pixels=2, pickable=True),
        pdk.Layer("PathLayer", box, get_path="path", get_color=[79, 157, 255], width_min_pixels=2),
    ]
    span = max(north - south, (east - west) / 2)
    zoom = float(np.clip(8.0 - np.log2(max(span, 0.5)), 3, 9))
    st.pydeck_chart(pdk.Deck(layers=layers, map_style="dark",
                             initial_view_state=pdk.ViewState(latitude=(south + north) / 2,
                                                              longitude=(west + east) / 2, zoom=zoom),
                             tooltip={"text": "{text}"}))
    st.caption("Each circle is one 0.25° grid cell (about 28 km). Bigger, brighter circles mean more hotspots. "
               "The blue outline is the selected area.")

# ---------------- 5. method ----------------
with tab_method:
    st.subheader("How the record was harmonised")
    st.markdown("""
- **The problem.** MODIS (1 km pixels, from 2000) and VIIRS (375 m pixels, from 2012) count fires differently, so their records cannot be compared directly.
- **Cleaning.** Low-confidence detections and non-vegetation sources (volcanoes, gas flares, offshore) are removed from both sensors.
- **Gridding.** Hotspots are counted per 0.25° cell, per month, separately for day and night.
- **Scaling.** For the years both sensors flew, we learned how many VIIRS hotspots correspond to one MODIS hotspot, for each 2° block and for day and night. MODIS counts before February 2012 are multiplied by that factor.
- **The joined record.** MODIS scaled (Nov 2000 to Jan 2012), then VIIRS S-NPP (to Mar 2018), then VIIRS NOAA-20. The two VIIRS satellites agree to within 1%.
""")
    st.subheader("How accurate it is")
    val = load_validation()
    val.columns = ["MODIS input", "Level", "Error, each year left out in turn (2012–2021)",
                   "Error on unseen years (2022–2025)"]
    for col in val.columns[2:]:
        val[col] = (val[col] * 100).map("{:.1f}%".format)
    st.dataframe(val, hide_index=True, width="stretch")
    st.markdown("""
Error is the total absolute difference between scaled MODIS and actual VIIRS, as a share of actual VIIRS hotspots.

**Limits**
- Reliable for islands, provinces and countries. Not reliable for a single 28 km cell.
- Quiet fire years are underestimated by roughly 10 to 25%, because MODIS misses more of the small fires.
- November 2000 to July 2002 uses the Terra satellite alone and is less certain. (The Terra-only factor is applied to those months only. Its error on 2022–2025 is high because Terra's detections fell away in those years.)
- The most recent months of any update are near-real-time data, not final science quality.

**Data.** NASA FIRMS active fire products: MODIS Collection 6.1 (MCD14ML) and VIIRS 375 m (S-NPP and NOAA-20), for Malaysia and Indonesia.
""")
