"""Explainable rule-based recommendations; no trained model is involved."""


def _fmt(value, unit="", digits=1):
    if value is None:
        return "not available"
    try:
        if value != value:
            return "not available"
        return f"{value:.{digits}f}{unit}"
    except (TypeError, ValueError):
        return "not available"


def build_recommendations(profile: dict, climate: dict) -> list[dict]:
    recs = []
    temp = climate.get("temperature_mean")
    rain = climate.get("rainfall_total")
    humidity = climate.get("humidity_mean")
    if temp is not None and temp == temp and temp >= 30:
        recs.append({
            "title": "Review irrigation timing during warm conditions",
            "action": "Check field moisture and consider scheduling irrigation during cooler hours, if this fits your system and crop.",
            "why": "Warm mean air temperature can increase evaporative demand, but temperature alone cannot determine crop water need.",
            "data": f"NASA POWER period mean temperature: {_fmt(temp, ' °C')}.",
            "missing": "Crop stage, evapotranspiration, soil texture, irrigation method, and direct soil-moisture trend.",
        })
    if rain is not None and rain == rain and rain >= 10:
        recs.append({
            "title": "Inspect soil moisture after recorded rainfall",
            "action": "Check moisture in the root zone before applying the next irrigation.",
            "why": "Rain occurred during the selected period, but the amount reaching roots depends on timing, runoff, and infiltration.",
            "data": f"NASA POWER corrected precipitation total: {_fmt(rain, ' mm')}.",
            "missing": "Rain timing at the field, effective rainfall, soil infiltration, drainage, and crop stage.",
        })
    soil_ec, water_ec = profile.get("soil_ec"), profile.get("water_ec")
    if soil_ec is not None or water_ec is not None:
        values = []
        if soil_ec is not None:
            values.append(f"manual soil EC {_fmt(soil_ec, ' dS/m')}")
        if water_ec is not None:
            values.append(f"manual irrigation-water EC {_fmt(water_ec, ' dS/m')}")
        recs.append({
            "title": "Interpret EC with the measurement method and crop in mind",
            "action": "Record the sampling and test method, compare against crop-specific local guidance, and repeat measurements consistently.",
            "why": "EC is an indicator related to dissolved salts, but soil and water EC use different sampling methods and thresholds.",
            "data": "; ".join(values) + ". These values were entered manually.",
            "missing": "Soil extraction method, sampling depth, crop growth stage, lab quality, drainage, and locally validated crop thresholds.",
        })
    moisture = profile.get("soil_moisture")
    if moisture is not None:
        recs.append({
            "title": "Use the moisture reading as a trend, not a stand-alone trigger",
            "action": "Repeat the reading at consistent locations and depth, then combine it with crop stage and field observation.",
            "why": "A single manually entered moisture percentage lacks soil-specific calibration and root-zone context.",
            "data": f"User-entered soil moisture: {_fmt(moisture, '%')}.",
            "missing": "Sensor or lab method, calibration, soil texture, sampling depth, and the crop's allowable depletion.",
        })
    if humidity is not None and humidity == humidity:
        recs.append({
            "title": "Use humidity as context for field scouting",
            "action": "Pair the climate reading with local disease and crop scouting guidance.",
            "why": "Relative humidity helps describe atmospheric conditions but does not diagnose crop disease or irrigation need on its own.",
            "data": f"NASA POWER period mean RH2M: {_fmt(humidity, '%')}.",
            "missing": "Leaf wetness, canopy conditions, crop stage, local disease alerts, and field observations.",
        })
    if not recs:
        recs.append({
            "title": "Collect field observations",
            "action": "Add manual EC and moisture measurements, and review the selected-period climate data before changing irrigation.",
            "why": "The current input set does not support a specific irrigation adjustment.",
            "data": "No triggered climate or EC rule from the available inputs.",
            "missing": "Crop stage, soil texture, irrigation method, soil moisture, and measurement context.",
        })
    return recs
