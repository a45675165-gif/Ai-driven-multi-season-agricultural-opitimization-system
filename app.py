"""AI-Driven Multi-Season Agricultural Optimization System dashboard."""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from irrigation_plans import compare_plans
from nasa_api import NASAAPIError, fetch_daily_weather
from recommendations import build_recommendations
from data_sources import check_sources
from crop_rotation import compare_rotations
from visualizations import (
    ec_chart,
    irrigation_chart,
    weather_chart,
)


st.set_page_config(
    page_title="AI-Driven Multi-Season Agricultural Optimization System",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');
    :root { --forest:#173f35; --leaf:#4f8a62; --mint:#e9f2e8; --sand:#f5f1e8; --ink:#20312c; }
    html, body, [class*="css"] { font-family:'DM Sans', sans-serif; color:var(--ink); }
    .stApp { background:linear-gradient(140deg,#f8faf6 0%,#f2f5ee 65%,#eef3e9 100%); }
    h1,h2,h3 { font-family:'Manrope',sans-serif; color:var(--forest); letter-spacing:-.035em; }
    [data-testid="stSidebar"] { background:#173f35; }
    [data-testid="stSidebar"] * { color:#f4f8f2 !important; }
    [data-testid="stMetric"] { background:white; border:1px solid #e1e9df; padding:18px 20px; border-radius:16px; box-shadow:0 5px 18px #20312c0a; }
    [data-testid="stMetricLabel"] { color:#64756a; }
    .hero { padding:28px 32px; border-radius:22px; background:linear-gradient(115deg,#173f35,#2f6a4b); color:#f5f7ef; margin:8px 0 22px; }
    .hero h1 { color:#fff; margin:0 0 5px; }
    .hero h1 { font-size:clamp(1.55rem,3vw,2.5rem); line-height:1.12; }
    .hero p { color:#e1eddf; margin:0; }
    .eyebrow { font-size:.75rem; text-transform:uppercase; letter-spacing:.14em; color:#a9d2a5; font-weight:700; }
    .panel { background:white; border:1px solid #e2e9df; border-radius:18px; padding:20px 22px; margin-bottom:14px; }
    .muted { color:#68776e; }
    .tag { display:inline-block; padding:4px 10px; background:#e9f2e8; border-radius:99px; color:#2d6445; font-size:.8rem; font-weight:600; }
    div.stButton > button[kind="primary"] { background:#2f6a4b; border-color:#2f6a4b; border-radius:10px; }
    .stApp input, .stApp textarea { color:#2f6a4b !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


def show_value(value, unit="", digits=1):
    if value is None or pd.isna(value):
        return "Unavailable"
    return f"{value:.{digits}f}{unit}"


@st.cache_data(ttl=3600, show_spinner=False)
def load_weather(latitude, longitude, start_date, end_date):
    """Cache identical requests so page navigation does not repeat API calls."""
    return fetch_daily_weather(latitude, longitude, start_date, end_date)


def main():
    st.sidebar.markdown("# 🌱 AI-Driven Multi-Season Agricultural Optimization System")
    st.sidebar.caption("Explainable rule-based planning · no trained AI model")
    st.sidebar.divider()
    page = st.sidebar.radio(
        "Navigate", ["Overview", "Climate data", "Irrigation & EC", "Crop rotation", "Data sources", "Recommendations"]
    )

    with st.sidebar.form("farm_inputs"):
        st.subheader("Farm profile")
        farm_name = st.text_input("Farm name / location", "My farm")
        latitude = st.number_input("Latitude", min_value=-90.0, max_value=90.0, value=30.0444, format="%.4f")
        longitude = st.number_input("Longitude", min_value=-180.0, max_value=180.0, value=31.2357, format="%.4f")
        crop = st.selectbox("Crop type", ["Wheat", "Maize", "Rice", "Tomato", "Citrus", "Other / not specified"])
        area_m2 = st.number_input("Farm area (m²)", min_value=1.0, value=1000.0, step=100.0)
        st.caption("Manual reference for plan estimates; use your usual weekly irrigation depth.")
        baseline_mm = st.number_input("Reference irrigation (mm/week)", min_value=0.1, value=35.0, step=1.0)
        soil_ec = st.number_input("Soil EC (dS/m), optional", min_value=0.0, value=0.0, step=0.1, help="Enter 0 if not measured. Interpretation depends on the sampling and lab method.")
        water_ec = st.number_input("Irrigation-water EC (dS/m), optional", min_value=0.0, value=0.0, step=0.1, help="Manually measured value; no sensor is connected.")
        soil_moisture = st.number_input("Soil moisture (%), manual entry, optional", min_value=0.0, max_value=100.0, value=0.0, step=1.0, help="User-entered value only. No physical sensor is connected; NASA soil moisture is a separate satellite product.")
        today = date.today()
        default_start = today - timedelta(days=13)
        start_date = st.date_input("Climate start date", value=default_start, max_value=today)
        end_date = st.date_input("Climate end date", value=today, max_value=today)
        submitted = st.form_submit_button("Update farm dashboard", type="primary", width="stretch")

    # Keep the submitted profile stable across page navigation.
    if submitted or "farm_profile" not in st.session_state:
        st.session_state.farm_profile = {
            "farm_name": farm_name.strip() or "My farm",
            "latitude": latitude,
            "longitude": longitude,
            "crop": crop,
            "area_m2": area_m2,
            "baseline_mm": baseline_mm,
            "soil_ec": soil_ec if soil_ec > 0 else None,
            "water_ec": water_ec if water_ec > 0 else None,
            "soil_moisture": soil_moisture if soil_moisture > 0 else None,
            "start_date": start_date,
            "end_date": end_date,
        }
    profile = st.session_state.farm_profile

    st.markdown(
        f'<div class="hero"><div class="eyebrow">NASA climate + your field notes · rule-based guidance</div>'
        f'<h1>AI-Driven Multi-Season Agricultural Optimization System</h1><p>Decision support for <b>{profile["farm_name"]}</b> · '
        f'{profile["latitude"]:.4f}, {profile["longitude"]:.4f} · {profile["crop"]}</p></div>',
        unsafe_allow_html=True,
    )

    weather = pd.DataFrame()
    error = None
    if profile["start_date"] > profile["end_date"]:
        error = "Start date must be on or before end date."
    else:
        with st.spinner("Retrieving daily climate data from NASA POWER…"):
            try:
                weather = load_weather(
                    profile["latitude"], profile["longitude"],
                    profile["start_date"], profile["end_date"],
                )
            except NASAAPIError as exc:
                error = str(exc)
    if error:
        st.error(f"NASA POWER data unavailable: {error}")
        st.info("Check your connection, coordinates, and date range, then try again. No sample climate data is substituted.")

    if weather.empty:
        climate_summary = {}
    else:
        climate_summary = {
            "temperature_mean": weather["temperature_c"].mean(),
            "rainfall_total": weather["rainfall_mm"].sum(min_count=1),
            "humidity_mean": weather["humidity_pct"].mean(),
            "wind_mean": weather["wind_speed_ms"].mean(),
        }
    plans = compare_plans(
        area_m2=profile["area_m2"], baseline_mm_week=profile["baseline_mm"],
        climate_summary=climate_summary, soil_ec=profile["soil_ec"],
        water_ec=profile["water_ec"],
    )
    recommendations = build_recommendations(profile, climate_summary)

    if page == "Data sources":
        st.subheader("Data source availability")
        st.caption("A reachable API or discovered scene is not automatically a farm measurement. Statuses are checked only when you press the button.")
        if st.button("Check sources for this farm and date range", type="primary"):
            with st.spinner("Checking official source endpoints…"):
                st.session_state.source_checks = check_sources(
                    profile["latitude"], profile["longitude"], profile["start_date"],
                    profile["end_date"], len(weather),
                )
        if "source_checks" not in st.session_state:
            st.info("Run a check to see live availability. No source is marked successful before the endpoint responds.")
        else:
            source_rows = st.session_state.source_checks
            st.dataframe(pd.DataFrame(source_rows)[["source", "status", "records", "coverage", "quality", "detail", "checked_at"]],
                         width="stretch", hide_index=True, alt="Live data-source availability, record counts, coverage, and quality notes.")
            st.caption("NASA POWER provides numeric weather values in the dashboard. NASA GPM/SMAP and GEDI currently report NASA CMR granule discovery; retrieving and decoding science pixels needs Earthdata credentials and scientific-format support. STAC scenes are metadata until raster values are processed.")
            with st.expander("Official source endpoints and access notes"):
                st.markdown("""
                - [NASA POWER Daily Point API](https://power.larc.nasa.gov/api/temporal/daily/point)
                - [NASA GPM IMERG Final Daily V07](https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary) — global 0.1° daily precipitation; Earthdata Login for granule data.
                - [NASA SMAP SPL3SMP V9](https://nsidc.org/data/spl3smp/versions/9) — global daily 36 km surface soil moisture; Earthdata Login. This is moisture, not soil salinity/EC.
                - [NASA GEDI CMR](https://cmr.earthdata.nasa.gov/search/granules.umm_json) — footprint sampling, not wall-to-wall coverage.
                - [CoCoRaHS API](https://api2.cocorahs.org/Help) · [USGS Water Data API](https://api.waterdata.usgs.gov/docs/)
                - [USDA AMS API](https://mymarketnews.ams.usda.gov/mymarketnews-api) · [USDA NASS API](https://quickstats.nass.usda.gov/api/)
                - [OpenET API](https://etdata.org/api/api-documentation/) · [LANDFIRE REST](https://lfps.usgs.gov/)
                - [Copernicus STAC](https://documentation.dataspace.copernicus.eu/APIs/STAC.html) · [ERA5 CDS dataset](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels)
                """)

    elif page == "Crop rotation":
        st.subheader("Multi-season crop rotation planner")
        st.warning("Editable example rows are scenario inputs only. They are not NASA values, farm measurements, local crop prescriptions, or validated yield/salinity outcomes.")
        st.write("Edit the crop, family, weekly irrigation estimate, salt-tolerance reference, and legume flag for each season. Use matching soil EC test methods before interpreting salinity fit.")
        rotation_input = pd.DataFrame([
            {"Plan": plan, "Season": season, "Crop": crop_name, "Family": family,
             "Water mm/week (assumption)": water, "Soil tolerance EC dS/m (optional)": None,
             "Legume (assumption)": legume}
            for plan, crops in {
                "Diverse rotation": [("Wheat", "Grass", 35, False), ("Faba bean", "Legume", 30, True), ("Tomato", "Nightshade", 32, False)],
                "Water priority": [("Barley", "Grass", 28, False), ("Chickpea", "Legume", 25, True), ("Sorghum", "Grass", 34, False)],
                "Salinity review": [("Barley", "Grass", 28, False), ("Cotton", "Malvaceae", 38, False), ("Faba bean", "Legume", 30, True)],
            }.items() for season, (crop_name, family, water, legume) in enumerate(crops, 1)
        ])
        rotation_input["Soil tolerance EC dS/m (optional)"] = pd.to_numeric(
            rotation_input["Soil tolerance EC dS/m (optional)"], errors="coerce"
        )
        st.caption("The initial rows are illustrative DEMO PLANNING ASSUMPTIONS and must be replaced with locally approved crop-water data. Optional EC tolerance is left blank because a valid comparison depends on reference method/crop context.")
        edited = st.data_editor(rotation_input, width="stretch", hide_index=True, num_rows="dynamic", key="rotation_editor",
                                alt="Editable crop rotation plans and clearly labeled planning assumptions.",
                                column_config={"Water mm/week (assumption)": st.column_config.NumberColumn(min_value=0, step=1),
                                               "Soil tolerance EC dS/m (optional)": st.column_config.NumberColumn(min_value=0, step=0.1)})
        valid = edited.dropna(subset=["Plan", "Crop", "Water mm/week (assumption)"])
        valid = valid[(valid["Plan"].astype(str).str.strip() != "") & (valid["Crop"].astype(str).str.strip() != "")]
        sequences = []
        for plan_name, group in valid.groupby("Plan", sort=False):
            crops = []
            for _, row in group.iterrows():
                family = "Unspecified" if pd.isna(row["Family"]) or not str(row["Family"]).strip() else str(row["Family"])
                tolerance = row["Soil tolerance EC dS/m (optional)"]
                legume = row["Legume (assumption)"]
                crops.append({"name": str(row["Crop"]), "family": family,
                              "water_mm_week": float(row["Water mm/week (assumption)"]),
                              "salt_tolerance_ds_m": None if pd.isna(tolerance) else float(tolerance),
                              "legume": False if pd.isna(legume) else bool(legume)})
            sequences.append({"name": plan_name, "crops": crops})
        if sequences:
            results = pd.DataFrame(compare_rotations(sequences, profile["soil_ec"]))
            st.plotly_chart(irrigation_chart([{"name": row["name"], "depth_mm_week": row["water_mean_mm_week"]} for row in results.to_dict("records")]), width="stretch", theme=None, alt="Average weekly irrigation scenario estimates for each crop rotation.")
            st.dataframe(results[["name", "seasons", "water_total_mm_week", "water_mean_mm_week", "sustainability_score", "salinity_fit_pct", "families", "crops"]], width="stretch", hide_index=True,
                         alt="Comparison of crop rotation water assumptions, crop diversity heuristic, and optional salinity fit.")
            for row in results.to_dict("records"):
                st.caption(f"{row['name']}: {row['assumption']} {row['ec_note']}")
        st.info("Long-term sustainability score is a transparent heuristic for family diversity and inclusion of a legume. It is not a measured soil-health outcome. No root depth, residue, cover, drainage, local weather by season, yield, or FAO crop-water database is included yet.")

    elif page == "Overview":
        st.subheader("Field conditions")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Mean temperature", show_value(climate_summary.get("temperature_mean"), " °C"))
        c2.metric("Rainfall in period", show_value(climate_summary.get("rainfall_total"), " mm"))
        c3.metric("Mean relative humidity", show_value(climate_summary.get("humidity_mean"), "%"))
        c4.metric("Mean wind speed", show_value(climate_summary.get("wind_mean"), " m/s"))
        st.caption("Climate observations are retrieved for the selected point and dates from NASA POWER. Daily values may include missing days.")
        left, right = st.columns([1.3, 1])
        with left:
            st.plotly_chart(weather_chart(weather), width="stretch", theme=None, alt="Daily NASA POWER temperature, rainfall, and relative humidity.")
        with right:
            st.markdown("<div class='panel'><h3>Field notes</h3>", unsafe_allow_html=True)
            st.plotly_chart(ec_chart(profile["soil_ec"], profile["water_ec"]), width="stretch", theme=None, alt="Manually entered soil and irrigation-water electrical conductivity readings.")
            st.markdown("<p class='muted'>EC values are manual inputs in dS/m. Measurement method affects interpretation.</p></div>", unsafe_allow_html=True)
        st.markdown("<div class='panel'><h3>At a glance</h3><span class='tag'>Rule-based guidance</span>", unsafe_allow_html=True)
        st.write(recommendations[0]["action"] if recommendations else "Add farm observations to receive guidance.")
        st.markdown("</div>", unsafe_allow_html=True)

    elif page == "Climate data":
        st.subheader("NASA POWER daily climate")
        st.caption(f"{profile['start_date']} to {profile['end_date']} · {profile['latitude']:.4f}, {profile['longitude']:.4f}")
        if not weather.empty:
            st.plotly_chart(weather_chart(weather), width="stretch", theme=None, alt="Daily NASA POWER temperature, rainfall, and relative humidity.")
            with st.expander("View retrieved values"):
                st.dataframe(weather, width="stretch", hide_index=True, alt="Daily climate values returned by NASA POWER.")
                st.download_button("Download climate CSV", weather.to_csv(index=False), "agricultural_optimization_nasa_power.csv", "text/csv")
        else:
            st.info("No climate table to display until NASA POWER returns data.")

    elif page == "Irrigation & EC":
        st.subheader("Compare irrigation scenarios")
        st.warning("These are planning estimates from your entered reference depth and transparent scenario factors. They are not measured water use, crop-specific irrigation prescriptions, or validated yield/salinity outcomes.")
        st.plotly_chart(irrigation_chart(plans), width="stretch", theme=None, alt="Estimated weekly irrigation depth for baseline, water-saving, and EC-aware scenarios.")
        cols = st.columns(3)
        for col, plan in zip(cols, plans):
            with col:
                comparison = (f"{plan['saving_pct']:.0f}% scenario reduction" if plan["saving_pct"] >= 0 else f"{abs(plan['saving_pct']):.0f}% scenario increase")
                st.markdown(f"<div class='panel'><h3>{plan['name']}</h3><p><b>{plan['depth_mm_week']:.1f} mm/week</b> estimated</p><p><b>{plan['volume_l_week']:,.0f} L/week</b> for {profile['area_m2']:,.0f} m²</p><p>Compared with baseline: {comparison}</p><p>{plan['salinity']}</p><p class='muted'><b>Advantage:</b> {plan['advantage']}<br><b>Limitation:</b> {plan['limitation']}</p></div>", unsafe_allow_html=True)
        st.markdown("### EC readings")
        st.plotly_chart(ec_chart(profile["soil_ec"], profile["water_ec"]), width="stretch", theme=None, alt="Separate manual soil EC and irrigation-water EC measurements.")
        st.caption("Soil and water EC are separate manual measurements. Confirm the test method, units, sampling depth, and crop-specific interpretation with a qualified local agronomist.")

    else:
        st.subheader("Explainable recommendations")
        st.caption("A transparent rule-based guide. No trained AI model is used.")
        for rec in recommendations:
            with st.container(border=True):
                st.markdown(f"#### {rec['title']}")
                st.write(f"**Recommended:** {rec['action']}")
                st.write(f"**Why:** {rec['why']}")
                st.write(f"**Supporting data:** {rec['data']}")
                st.write(f"**Missing information:** {rec['missing']}")

    st.divider()
    st.caption("NASA POWER daily point data · Estimates are decision-support scenarios only · This application does not connect to physical sensors.")


if __name__ == "__main__":
    main()
