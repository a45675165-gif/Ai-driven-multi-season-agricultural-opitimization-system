"""Source discovery and transparent availability checks for the planning system.

Discovery responses are metadata, not farm measurements. A source is only
reported as supplying values when its documented data endpoint returns values.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import os

import requests


def _session() -> requests.Session:
    # Avoid the disabled 127.0.0.1:9 proxy inherited in this environment.
    session = requests.Session()
    session.trust_env = False
    session.headers.update({"User-Agent": "AgriculturalOptimizationSystem/1.0"})
    return session


def _result(source, status, detail, *, records=0, coverage="Not checked", quality="Not assessed", url=""):
    return {
        "source": source,
        "status": status,
        "detail": detail,
        "records": records,
        "coverage": coverage,
        "quality": quality,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "url": url,
    }


def discover_nasa_granules(source: str, short_name: str, latitude: float, longitude: float,
                          start: date, end: date, version: str | None = None) -> dict:
    """Check NASA CMR for actual product granule metadata near a point/date."""
    url = "https://cmr.earthdata.nasa.gov/search/granules.umm_json"
    params = {"short_name": short_name, "point": f"{longitude},{latitude}",
              "temporal": f"{start.isoformat()}T00:00:00Z,{end.isoformat()}T23:59:59Z",
              "page_size": 10}
    if version:
        params["version"] = version
    try:
        response = _session().get(url, params=params, timeout=(8, 25))
        response.raise_for_status()
        payload = response.json()
        hits = int(payload.get(" hits", payload.get("hits", 0)))
        if hits:
            return _result(source, "Granules found; values require Earthdata access",
                           f"NASA CMR found {hits} matching granule(s). This is discovery metadata, not extracted farm values.",
                           records=hits, coverage="Point/date matched by CMR", quality="Granule metadata only; pixel quality not assessed", url=response.url)
        return _result(source, "No matching granules", "CMR returned no granule for this point/date. This does not imply global product coverage is absent.", coverage="No matching granule", quality="Not assessed", url=response.url)
    except (requests.RequestException, ValueError, TypeError) as exc:
        return _result(source, "Connection error", f"NASA CMR discovery failed: {exc}", url=url)


def check_sources(latitude: float, longitude: float, start: date, end: date,
                  weather_records: int = 0) -> list[dict]:
    """Probe documented discovery/data endpoints without hiding auth gaps."""
    results = []
    results.append(_result("NASA POWER", "Data retrieved" if weather_records else "No data retrieved",
                           f"NASA POWER daily values currently loaded: {weather_records} rows.", records=weather_records,
                           coverage="Global point service; requested coordinates", quality="Daily gridded/reanalysis estimates; missing days can occur",
                           url="https://power.larc.nasa.gov/api/temporal/daily/point"))
    results.append(discover_nasa_granules("NASA GPM IMERG Final Daily", "GPM_3IMERGDF", latitude, longitude, start, end, "07"))
    results.append(discover_nasa_granules("NASA SMAP L3 Radiometer", "SPL3SMP", latitude, longitude, start, end, "9"))
    earthdata_configured = bool(os.getenv("EARTHDATA_USERNAME") and os.getenv("EARTHDATA_PASSWORD"))
    for item in results:
        if item["source"].startswith(("NASA GPM", "NASA SMAP")) and item["records"]:
            item["detail"] += (" Earthdata credential variables are configured; pixel download/decoding is still not implemented." if earthdata_configured
                               else " Earthdata Login credentials are not configured; granule pixel download is unavailable.")

    # Open, documented discovery endpoints. A response is labelled metadata unless
    # the service actually returns a value observation for the requested farm.
    probes = [
        ("CoCoRaHS", "https://api2.cocorahs.org/api/SigWxObs", {"limit": 1}, "US/Canada volunteer station network; station proximity required"),
        ("USGS Water Data", "https://api.waterdata.usgs.gov/ogcapi/v1/collections/monitoring-locations/items", {"limit": 1, "f": "json"}, "United States monitoring locations"),
        ("LANDFIRE", "https://lfps.usgs.gov/arcgis/rest/services/LandfireProductService/GPServer/LandfireProductService", {"f": "json"}, "United States and listed territories"),
    ]
    for name, url, params, coverage in probes:
        try:
            response = _session().get(url, params=params, timeout=(8, 20))
            response.raise_for_status()
            results.append(_result(name, "Service reachable; farm data not verified",
                                   "Public service endpoint responded. This probe did not establish an observation for the selected farm.",
                                   coverage=coverage, quality="Endpoint reachability only", url=response.url))
        except requests.RequestException as exc:
            results.append(_result(name, "Connection error", str(exc), coverage=coverage, url=url))

    # STAC search verifies scenes for this point/time. Items expose metadata and
    # assets; extracting raster pixels is a separate authenticated workflow.
    try:
        url = "https://stac.dataspace.copernicus.eu/v1/search"
        body = {"collections": ["sentinel-2-l2a"], "intersects": {"type": "Point", "coordinates": [longitude, latitude]},
                "datetime": f"{start.isoformat()}T00:00:00Z/{end.isoformat()}T23:59:59Z", "limit": 10}
        response = _session().post(url, json=body, timeout=(8, 25))
        response.raise_for_status()
        items = response.json().get("features", [])
        results.append(_result("Copernicus Sentinel-2 STAC", "Scenes found; pixels not extracted" if items else "No matching scenes",
                               f"STAC returned {len(items)} scene item(s); metadata discovery is not a farm measurement.", records=len(items),
                               coverage="Global mission coverage; cloud, orbit and scene availability vary", quality="Scene metadata only; cloud/pixel QA not evaluated", url=response.url))
    except (requests.RequestException, ValueError, TypeError) as exc:
        results.append(_result("Copernicus Sentinel-2 STAC", "Connection error", str(exc), url="https://stac.dataspace.copernicus.eu/v1/search"))

    # GEDI CMR granules are footprint/sampling discovery; GEDI is not a wall-to-wall global raster.
    results.append(discover_nasa_granules("NASA GEDI L2A", "GEDI02_A", latitude, longitude, start, end, "002"))

    requirements = [
        ("USDA AMS Market News", "USDA_MMN_API_KEY", "Account/API key required; reports are market-level, not field measurements.", "United States market reports"),
        ("USDA NASS QuickStats", "USDA_NASS_API_KEY", "USDA NASS API key required; statistics are published geographies, not farm-point values.", "United States agricultural statistics"),
        ("OpenET", "OPENET_API_KEY", "OpenET API key required; raster service is limited to its documented US coverage.", "United States coverage; not global"),
        ("ECMWF ERA5 CDS", "CDS_API_KEY", "CDS account, accepted dataset terms, cdsapi and a local credential file are required.", "Global reanalysis grid; not a field sensor"),
    ]
    for name, variable, explanation, coverage in requirements:
        exists = bool(os.getenv(variable))
        results.append(_result(name, "Credential configured; not queried" if exists else "Credential missing",
                               explanation if not exists else "Credential variable exists; live query has not been run by this availability check.",
                               coverage=coverage, quality="Not assessed"))

    # CoCoRaHS and USGS have domestic coverage. No farm observation is inferred from a service response.
    if not (-180 <= longitude <= -50 and 10 <= latitude <= 85):
        for item in results:
            if item["source"] in {"CoCoRaHS", "USGS Water Data", "USDA AMS Market News", "USDA NASS QuickStats", "OpenET", "LANDFIRE"}:
                item["status"] = "Outside documented coverage"
                item["detail"] = "The selected coordinates are outside the source's documented US-centric coverage. No substitution was made."
    return results
