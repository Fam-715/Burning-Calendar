# Burning Calendar

**Team Zero Gravity, Zero Sleep · NASA Space Apps Challenge 2026 · Kuala Lumpur**
Challenge: *Harmonization of MODIS and VIIRS Hot Spots*

Burning Calendar turns 26 years of NASA fire detections (November 2000 to October 2026) into one consistent record for Malaysia and Indonesia. Pick an area and a period, and it shows when fires usually peak, which years were worst, and whether a given month is unusual.

**Live app:** [burning-calendar-app.streamlit.app](https://burning-calendar-app.streamlit.app/)

## Why it is needed

NASA has tracked fire hotspots since 2000 with MODIS (1 km pixels) and since 2012 with VIIRS (375 m pixels). VIIRS sees about five times as many hotspots in this region, so the two records cannot simply be joined. MODIS is also near the end of its life. We scale the MODIS record into VIIRS-equivalent hotspots so the whole series can be read as one.

## What the app does

- Area of interest: preset regions or a custom latitude/longitude box, and any range of months
- Burning calendar: months by years, coloured by hotspot count or by how unusual the month was
- Harmonisation check: scaled MODIS against real VIIRS for every month since 2012, for the chosen area
- Any month compared with its historical median, the usual fire season, and the most unusual months
- Map of where hotspots were detected
- Downloads: the calendar, a yearly summary and the gridded hotspots (CSV), and the calendar as a picture (HTML)

**Demo video (30 s):** https://drive.google.com/file/d/11hv_G4Eg5E2QxGkeHOhgcJkLvsAbswwB/view

## How the harmonisation works

1. Remove low-confidence detections and non-vegetation sources (volcanoes, gas flares, offshore).
2. Count hotspots per 0.25° cell, per month, separately for day and night.
3. For 2012–2021, when both sensors flew, learn how many VIIRS hotspots match one MODIS hotspot for each 2° block and for day and night.
4. Multiply MODIS counts before February 2012 by that factor.
5. Join: scaled MODIS (Nov 2000 – Jan 2012), VIIRS S-NPP (Feb 2012 – Mar 2018), VIIRS NOAA-20 (Apr 2018 onwards).

## Accuracy

Factors were learned on 2012–2021 and tested on 2022–2025, which the model never saw.

| Level | Error, each year left out in turn (2012–2021) | Error on unseen years (2022–2025) |
|---|---|---|
| Whole region, yearly | 6.1% | 8.9% |
| Whole region, monthly | 8.5% | 12.5% |
| 2° block, monthly | 22.3% | 32.4% |
| 0.25° cell, monthly | 49.6% | 69.9% |

Limits: the record is reliable for islands, provinces and countries, not for single 28 km cells. Quiet fire years are underestimated by roughly 10–25%. November 2000 to July 2002 relies on the Terra satellite alone and is less certain.

## Files

| File | What it is |
|---|---|
| `app.py` | The Streamlit web app |
| `space_ui.py` | The app's look: space theme, animations and the burning calendar |
| `harmonise_firms.py` | Cleans, grids and harmonises the FIRMS data and writes the files in `data/` |
| `add_2026.ps1` | Adds January to October 2026 from FIRMS archive-request files, using the same cleaning and grid |
| `data/harmonised_grid_monthly.csv.gz` | Harmonised monthly hotspots per 0.25° cell, November 2000 to October 2026 |
| `data/scaling_factors.csv` | MODIS-to-VIIRS factors per 2° block |
| `data/validation.csv` | Accuracy results |
| `requirements.txt` | Python packages needed to run the app |
| `Burning_Calendar_demo.webm` | Copy of the 30-second demo video |

## Run it yourself

```
pip install -r requirements.txt
streamlit run app.py
```

## Data

NASA FIRMS (Fire Information for Resource Management System) active fire products: MODIS Collection 6.1 and VIIRS 375 m (S-NPP and NOAA-20), yearly country files for Malaysia and Indonesia (2000–2025), plus FIRMS archive-request files for January to October 2026. https://www.earthdata.nasa.gov/data/tools/firms

August to October 2026 are near-real-time data. Those files carry no source type, so non-vegetation sources (volcanoes, gas flares) could not be removed for those three months.

## Use of AI

The data pipeline, the web app and this README were written with AI assistance (Claude, by Anthropic) and checked by the team. This is noted at the top of each code file and declared in the "Use of SI" section of our Space Apps project page. No AI-generated images, video or audio are used; the demo video is built from screenshots of the app.
