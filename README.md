# AI-Driven Multi-Season Agricultural Optimization System

The AI-Driven Multi-Season Agricultural Optimization System is a Streamlit planning prototype. It combines live NASA POWER daily climate values with clearly labeled, user-entered field notes and editable crop-rotation scenarios. Its recommendations are rule-based; it does not connect to physical sensors and does not use a trained AI model.

## Project files

- app.py — Streamlit pages, farm inputs, climate display, source status, and crop rotation interface.
- nasa_api.py — NASA POWER Daily Point API client and missing-value handling.
- data_sources.py — live NASA CMR granule discovery, Sentinel-2 STAC scene discovery, public endpoint reachability probes, and credential/coverage status. Metadata discovery is not science-pixel extraction.
- crop_rotation.py — transparent arithmetic for user-entered multi-season scenarios.
- irrigation_plans.py — estimated weekly irrigation comparison from the user's reference depth.
- recommendations.py — evidence-based rule triggers with supporting and missing data.
- visualizations.py — Plotly charts.
- requirements.txt — the existing application dependencies.

## Data and limitations

NASA POWER is queried from its official [Daily Point API](https://power.larc.nasa.gov/api/temporal/daily/point) for T2M, PRECTOTCORR, RH2M, and WS2M. Failures and missing NASA sentinels are not filled with demo weather.

NASA GPM discovery uses the [IMERG Final Daily V07 product](https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary), globally gridded at 0.1 degrees. NASA SMAP uses [SPL3SMP Version 9](https://nsidc.org/data/spl3smp/versions/9), global daily surface soil moisture at 36 km. The current integration searches NASA CMR granule metadata only. It does not download or decode GPM/SMAP pixel values. An Earthdata Login and scientific-format reader are needed for that next step. SMAP moisture is never treated as salinity or EC.

CoCoRaHS, USGS, and LANDFIRE availability checks only test their documented public service endpoints; they do not claim a farm-specific observation. GEDI checks sparse footprint granule discovery. Sentinel-2 checks STAC scene metadata, not raster pixels. USDA AMS, USDA NASS, OpenET, and ERA5 show missing credentials when their configured environment variables are absent; authenticated retrieval is not implemented by this status probe. Coverage indicators include source limitations and do not infer observations from endpoint reachability.

Farm soil EC, irrigation-water EC, and optional soil moisture are user-entered manual values. No sensor is connected. Soil EC and water EC are separate. Crop rotation rows start as **editable demo planning assumptions** for water and crop-family categories. Replace them with locally validated information. The sustainability score is a heuristic based on family diversity and legumes, not a measured soil-health outcome. Irrigation plans are scenarios, not validated crop prescriptions or measured savings.

## Accounts and credentials

Do not put secrets in Python files or commit them. Configure credentials locally through environment variables or Streamlit secrets:

- NASA GPM/SMAP/GEDI data download: free NASA Earthdata Login; EARTHDATA_USERNAME, EARTHDATA_PASSWORD (not currently used to download pixels).
- USDA AMS: USDA_MMN_API_KEY.
- USDA NASS QuickStats: USDA_NASS_API_KEY.
- OpenET: OPENET_API_KEY.
- ERA5 CDS: CDS account, accepted dataset terms, CDS_API_KEY, and the documented CDS client configuration.

This environment currently has no Python interpreter discoverable on PATH, so the live probes and Streamlit launch have not been executed from this session. No package installation was performed.

## Run locally

From PowerShell in the project directory, after Python 3.10+ is available:

    py -3 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt
    python -m streamlit run app.py

The package installation step is intentionally listed for the operator; it was not run. Existing NASA POWER code disables inherited proxy variables for the individual request only, addressing the local 127.0.0.1:9 proxy without changing system settings.
