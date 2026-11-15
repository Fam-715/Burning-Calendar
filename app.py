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

import importlib

import space_ui as ui

ui = importlib.reload(ui)   # pick up design changes without rebooting the app
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
    # MODIS scaled with the 2-degree block factors for every month, so that in the years both
    # sensors flew it can be checked against what VIIRS actually recorded
    fac = pd.read_csv(DATA / "scaling_factors.csv")[["daynight", "lat_from", "lon_from", "factor_terra_aqua"]]
    df["lat_from"] = np.floor(df["lat"] / 2) * 2
    df["lon_from"] = np.floor(df["lon"] / 2) * 2
    df = df.merge(fac, on=["daynight", "lat_from", "lon_from"], how="left")
    typical = df.groupby("daynight")["factor_terra_aqua"].transform("median")
    df["factor_terra_aqua"] = df["factor_terra_aqua"].fillna(typical).fillna(0.0)
    df["modis_scaled"] = df["modis_raw"] * df["factor_terra_aqua"]
    return df.drop(columns=["lat_from", "lon_from"])


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
all_months = list(pd.period_range(first_ym, last_ym, freq="M").strftime("%Y-%m"))


def month_name(ym):
    return f"{MONTHS[int(ym[5:]) - 1]} {ym[:4]}"


start_default = "2001-01" if "2001-01" in all_months else all_months[0]
ym0, ym1 = st.sidebar.select_slider("From / to (month)", options=all_months,
                                    value=(start_default, all_months[-1]), format_func=month_name)
y0, y1 = int(ym0[:4]), int(ym1[:4])
period = f"{month_name(ym0)} to {month_name(ym1)}"
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
m = (sel.groupby("ym")[["hotspots", "modis_raw", "viirs_raw", "modis_scaled"]].sum()
        .reindex(all_months, fill_value=0).rename_axis("ym").reset_index())
m["year"] = m["ym"].str[:4].astype(int)
m["month"] = m["ym"].str[5:].astype(int)
m["mon"] = m["month"].map(lambda i: MONTHS[i - 1])
m["source"] = m["ym"].map(source_of)
m["usual"] = m.groupby("month")["hotspots"].transform("median")      # median of that calendar month
m["times_usual"] = (m["hotspots"] + 1) / (m["usual"] + 1)
m["log_ratio"] = np.log2(m["times_usual"]).clip(-3, 3)
m["label"] = m["mon"] + " " + m["year"].astype(str)
view = m[m["ym"].between(ym0, ym1)]

months_per_year = view.groupby("year")["month"].count()
full_years = months_per_year[months_per_year == 12].index
annual = view[view["year"].isin(full_years)].groupby("year")[["hotspots", "modis_raw"]].sum()
season = m.groupby("month")["hotspots"].median()
latest = m.iloc[-1]

# ---------------- headline numbers ----------------
k1, k2, k3, k4 = st.columns(4)
total = view["hotspots"].sum()
# the note under each number sits inside its card as a grey pill, like the "vs usual" pill
k1.metric("Total hotspots", f"{total / 1e6:.2f}M" if total >= 1e6 else f"{total:,.0f}",
          period, delta_color="off", delta_arrow="off")
if len(annual):
    worst = int(annual["hotspots"].idxmax())
    note = " (est. from MODIS)" if worst < 2012 else ""
    k2.metric("Worst year", str(worst),
              f"{annual['hotspots'].max():,.0f} hotspots{note}", delta_color="off", delta_arrow="off")
k3.metric("Usual peak month", MONTHS[int(season.idxmax()) - 1],
          f"median {season.max():,.0f} hotspots", delta_color="off", delta_arrow="off")
change = (latest["hotspots"] - latest["usual"]) / latest["usual"] * 100 if latest["usual"] else 0.0
k4.metric(f"Latest: {latest['label']}", f"{latest['hotspots']:,.0f}",
          f"{change:+.0f}% vs usual", delta_color="inverse")

if (north - south) * (east - west) < SMALL_AREA_DEG2:
    st.warning("This is a small area. Before 2012 the counts are estimated from MODIS, and "
               "for areas this small a single month can be off by 30% or more. "
               "Read the pattern, not the exact number.", icon="⚠️")

tab_cal, tab_trend, tab_month, tab_map, tab_method = st.tabs(
    ["Burning calendar", "Harmonisation", "A month against its history", "Map", "Method and data"])

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
    cal_html = ui.calendar_html(view, by_count=(mode == "Number of hotspots"))
    st.html(cal_html)
    st.caption("Each square is one month. Hover over a square to lift it and see the figures. Before February 2012 the counts are "
               "MODIS detections scaled to VIIRS-equivalent; from then on they are VIIRS observations. "
               "\"Usual\" is the median for that calendar month across the whole record.")

    with st.expander("Show as a table"):
        table = view.pivot(index="year", columns="mon", values="hotspots").reindex(columns=MONTHS)
        st.dataframe(table.round(0), width="stretch")

    st.markdown("**Download this search**")
    d1, d2 = st.columns(2)
    cal_csv = view[["ym", "year", "month", "hotspots", "usual", "times_usual",
                    "modis_raw", "viirs_raw", "source"]].round(2)
    d1.download_button("Calendar, month by month (CSV)", cal_csv.to_csv(index=False),
                       "burning_calendar.csv", "text/csv")
    cells = (sel[sel["ym"].between(ym0, ym1)]
             .drop(columns=["snpp_raw", "n20_raw", "factor_terra_aqua", "modis_scaled"]))
    d2.download_button("Gridded hotspots, 0.25° cells (CSV)", cells.to_csv(index=False),
                       "hotspots_grid.csv", "text/csv")
    d3, d4 = st.columns(2)
    yearly = (view.groupby("year")
                  .agg(months=("month", "count"), hotspots=("hotspots", "sum"), modis_raw=("modis_raw", "sum"),
                       busiest_month=("hotspots", "idxmax"))
                  .reset_index())
    yearly["busiest_month"] = yearly["busiest_month"].map(view["mon"])
    d3.download_button("Yearly summary (CSV)", yearly.round(0).to_csv(index=False),
                       "burning_calendar_yearly.csv", "text/csv")
    d4.download_button("Calendar picture (HTML, opens in any browser)",
                       ui.standalone(f"Burning calendar: {area_name}, {period}", cal_html),
                       "burning_calendar.html", "text/html")

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
    c.metric("Difference", f"{diff:+.0f}%",
             f"{row['times_usual']:.1f} times the usual", delta_color="off", delta_arrow="off")

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
    if season.max() > 0:
        busy = [i for i in range(1, 13) if season.get(i, 0) >= 0.5 * season.max()]
        share = sum(season.get(i, 0) for i in busy) / season.sum() * 100
        st.markdown(f"**Critical period: {', '.join(MONTHS[i - 1] for i in busy)}.** In a typical year these "
                    f"months hold about {share:.0f}% of the area's hotspots.")

    st.subheader("The most unusual months in the selected period")
    odd = (view[view["hotspots"] > 0].nlargest(10, "times_usual")
           [["label", "hotspots", "usual", "times_usual", "source"]]
           .rename(columns={"label": "Month", "hotspots": "Hotspots", "usual": "Usual for that month",
                            "times_usual": "Times the usual", "source": "Source"}))
    odd["Hotspots"] = odd["Hotspots"].round(0)
    odd["Usual for that month"] = odd["Usual for that month"].round(0)
    odd["Times the usual"] = odd["Times the usual"].round(1)
    st.dataframe(odd, hide_index=True, width="stretch")
    st.caption("Months ranked by how far they were above the median for the same calendar month.")

# ---------------- 3. trend and sensors ----------------
with tab_trend:
    st.subheader("Does it still matter which sensor saw the fire?")
    st.markdown(
        "MODIS and VIIRS have flown together since February 2012. That overlap is the test: scale the MODIS "
        "counts with the harmonisation factors, then see how close they come to what VIIRS actually recorded "
        f"in this area. All figures below are for {area_name}, {month_name('2012-02')} to {month_name(last_ym)}.")
    ov = m[m["ym"] >= "2012-02"].copy()
    raw_m, obs_v = float(ov["modis_raw"].sum()), float(ov["viirs_raw"].sum())
    if raw_m <= 0 or obs_v <= 0:
        st.info("Not enough MODIS and VIIRS detections in this area to compare the two sensors.")
    else:
        unseen = ov[ov["year"] >= 2022]
        unseen_total = float(unseen["viirs_raw"].sum())
        err = ((unseen["modis_scaled"] - unseen["viirs_raw"]).abs().sum() / unseen_total
               if unseen_total > 0 else None)
        spread = ov["modis_scaled"].std() > 0 and ov["viirs_raw"].std() > 0
        r2 = float(np.corrcoef(ov["modis_scaled"], ov["viirs_raw"])[0, 1] ** 2) if spread else None

        h1, h2, h3, h4 = st.columns(4)
        h1.metric("MODIS, as recorded", f"{raw_m:,.0f}", "1 km pixels", delta_color="off", delta_arrow="off")
        h2.metric("VIIRS, as recorded", f"{obs_v:,.0f}", "375 m pixels", delta_color="off", delta_arrow="off")
        h3.metric("VIIRS hotspots per MODIS hotspot", f"{obs_v / raw_m:.1f}×", "before harmonising",
                  delta_color="off", delta_arrow="off")
        h4.metric("Monthly match after scaling (R²)", "n/a" if r2 is None else f"{r2:.2f}",
                  "no unseen years" if err is None else f"{err * 100:.0f}% error, 2022–{last_year}",
                  delta_color="off", delta_arrow="off")

        st.subheader("Scaled MODIS against real VIIRS, month by month")
        ov["period"] = np.where(ov["year"] <= 2021, "2012–2021, used to learn the factors",
                                f"2022–{last_year}, never seen by the method")
        top_axis = float(max(ov["modis_scaled"].max(), ov["viirs_raw"].max()))
        x_enc = alt.X("modis_scaled:Q", title="MODIS scaled to VIIRS-equivalent (hotspots in the month)",
                      axis=alt.Axis(format="~s"))
        y_enc = alt.Y("viirs_raw:Q", title="VIIRS observed (hotspots in the month)", axis=alt.Axis(format="~s"))
        diagonal = (alt.Chart(pd.DataFrame({"modis_scaled": [0.0, top_axis], "viirs_raw": [0.0, top_axis]}))
                    .mark_line(color=GREY, strokeDash=[6, 4]).encode(x=x_enc, y=y_enc))
        dots = (alt.Chart(ov).mark_circle(size=60, opacity=0.85)
                .encode(x=x_enc, y=y_enc,
                        color=alt.Color("period:N",
                                        scale=alt.Scale(domain=["2012–2021, used to learn the factors",
                                                                f"2022–{last_year}, never seen by the method"],
                                                        range=[BLUE, ORANGE]),
                                        legend=alt.Legend(title=None, orient="top")),
                        tooltip=[alt.Tooltip("label:N", title="Month"),
                                 alt.Tooltip("modis_scaled:Q", title="MODIS scaled", format=",.0f"),
                                 alt.Tooltip("viirs_raw:Q", title="VIIRS observed", format=",.0f"),
                                 alt.Tooltip("modis_raw:Q", title="MODIS as recorded", format=",.0f")]))
        st.altair_chart((diagonal + dots).properties(height=380), width="stretch")
        st.caption("Each dot is one month. A dot on the dashed line means scaled MODIS matched VIIRS exactly. "
                   "Orange dots are months the method never saw when the factors were learned.")

        st.subheader("Year by year in the overlap")
        by_year = (ov.groupby("year")[["viirs_raw", "modis_scaled", "modis_raw"]].sum()
                     .rename(columns={"viirs_raw": "VIIRS observed", "modis_scaled": "MODIS scaled",
                                      "modis_raw": "MODIS as recorded"})
                     .reset_index().melt("year", var_name="series", value_name="count"))
        overlap = (alt.Chart(by_year).mark_line(strokeWidth=2, point=alt.OverlayMarkDef(size=45))
                   .encode(x=alt.X("year:O", title=None, axis=alt.Axis(labelAngle=0)),
                           y=alt.Y("count:Q", title="Hotspots per year", axis=alt.Axis(format="~s")),
                           color=alt.Color("series:N",
                                           scale=alt.Scale(domain=["VIIRS observed", "MODIS scaled",
                                                                   "MODIS as recorded"],
                                                           range=[BLUE, "#f2c14e", ORANGE]),
                                           legend=alt.Legend(title=None, orient="top")),
                           tooltip=[alt.Tooltip("year:O", title="Year"), alt.Tooltip("series:N", title="Series"),
                                    alt.Tooltip("count:Q", title="Hotspots", format=",.0f")]))
        st.altair_chart(overlap.properties(height=300), width="stretch")
        st.caption("If harmonisation works, the yellow line (MODIS after scaling) follows the blue line "
                   "(VIIRS) and leaves the orange line (MODIS as recorded) far below. 2012 covers February "
                   "to December only.")

    st.subheader("The whole record, before and after")
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
    st.subheader(f"Where the hotspots were, {period}")
    cells_sum = (sel[sel["ym"].between(ym0, ym1)].groupby(["lat", "lon"], as_index=False)["hotspots"].sum())
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
- The record ends in October 2026, the last complete month in the data. January to October 2026 come from a FIRMS archive request rather than the yearly country files.
- August to October 2026 are near-real-time data, not final science quality. Those files do not say what kind of source each detection is, so volcanoes and gas flares could not be removed for those three months. In the first seven months of 2026 such sources were about 1,700 detections a month, small next to the 140,000 to 213,000 hotspots a month recorded from August to October.

**Data.** NASA FIRMS active fire products: MODIS Collection 6.1 (MCD14ML) and VIIRS 375 m (S-NPP and NOAA-20), for Malaysia and Indonesia.
""")
