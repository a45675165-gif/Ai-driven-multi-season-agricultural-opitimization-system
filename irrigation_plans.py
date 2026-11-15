"""Transparent scenario calculations for comparing irrigation plans."""


def compare_plans(
    area_m2: float,
    baseline_mm_week: float,
    climate_summary: dict,
    soil_ec: float | None = None,
    water_ec: float | None = None,
) -> list[dict]:
    """Return scenario estimates using 1 mm over 1 m² = 1 litre.

    Water-saving factors are illustrative user-visible assumptions, not agronomic
    prescriptions. The adaptive scenario uses temperature as a simple trigger;
    rainfall is reported to the farmer but not treated as effective crop water.
    """
    baseline = max(float(baseline_mm_week), 0.0)
    mean_temp = climate_summary.get("temperature_mean")
    is_hot = mean_temp is not None and mean_temp == mean_temp and mean_temp >= 30
    adaptive_factor = 1.10 if is_hot else 1.0
    ec_supplied = soil_ec is not None or water_ec is not None
    ec_context = (
        "Manual EC reading(s) supplied; use them for screening and local follow-up, "
        "but no universal threshold-based water adjustment is applied."
        if ec_supplied
        else "No EC reading supplied; measure soil and irrigation water using a consistent method for salinity screening."
    )
    definitions = [
        {
            "name": "Baseline irrigation",
            "factor": 1.0,
            "salinity": "Keep an eye on root-zone salinity; no leaching fraction is modeled.",
            "advantage": "Uses your entered reference irrigation depth.",
            "limitation": "Does not adjust for measured soil moisture or crop stage.",
        },
        {
            "name": "Water-saving scenario",
            "factor": 0.80,
            "salinity": "A reduced-water scenario may require close salinity and crop-stress monitoring.",
            "advantage": "Shows the volume implied by an illustrative 20% reduction.",
            "limitation": "The 20% factor is an assumption, not a validated saving or safe reduction.",
        },
        {
            "name": "EC-aware adaptive scenario",
            "factor": adaptive_factor,
            "salinity": ec_context,
            "advantage": "Presents climate context alongside the availability of manual EC readings.",
            "limitation": "EC does not change the numeric factor because test method and crop-specific thresholds are not modeled; no soil-water balance, drainage, or leaching requirement is modeled.",
        },
    ]
    plans = []
    for item in definitions:
        depth = baseline * item["factor"]
        plans.append({
            **item,
            "depth_mm_week": depth,
            "volume_l_week": depth * float(area_m2),
            "saving_pct": (1 - item["factor"]) * 100,
        })
    return plans
