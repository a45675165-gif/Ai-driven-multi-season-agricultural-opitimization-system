"""Small client for NASA POWER's daily point endpoint."""

from datetime import date

import pandas as pd
import requests


BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMETERS = ("T2M", "PRECTOTCORR", "RH2M", "WS2M")
PARAMETER_COLUMNS = {
    "T2M": "temperature_c",
    "PRECTOTCORR": "rainfall_mm",
    "RH2M": "humidity_pct",
    "WS2M": "wind_speed_ms",
}


class NASAAPIError(RuntimeError):
    """Raised when NASA POWER returns an unusable response."""


def fetch_daily_weather(latitude: float, longitude: float, start: date, end: date) -> pd.DataFrame:
    """Fetch daily meteorological observations; missing NASA sentinels become NaN."""
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise NASAAPIError("Latitude or longitude is outside its valid range.")
    if start > end:
        raise NASAAPIError("Start date must not be after end date.")
    params = {
        "parameters": ",".join(PARAMETERS),
        "community": "AG",
        "longitude": longitude,
        "latitude": latitude,
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
        "time-standard": "UTC",
    }
    try:
        # The inherited proxy environment in this runtime points to a disabled
        # local proxy (127.0.0.1:9). Bypass environment proxies for this request
        # only; do not mutate process-wide or system-wide network settings.
        with requests.Session() as session:
            session.trust_env = False
            response = session.get(BASE_URL, params=params, timeout=(8, 45))
            response.raise_for_status()
    except requests.Timeout as exc:
        raise NASAAPIError("The request timed out. Please try again.") from exc
    except requests.RequestException as exc:
        raise NASAAPIError(f"Network or HTTP error: {exc}") from exc

    try:
        payload = response.json()
        raw = payload["properties"]["parameter"]
    except (ValueError, KeyError, TypeError) as exc:
        raise NASAAPIError("NASA POWER returned an unexpected JSON response.") from exc
    if not isinstance(raw, dict):
        raise NASAAPIError("NASA POWER returned an unexpected parameter structure.")

    frames = []
    for parameter, column in PARAMETER_COLUMNS.items():
        values = raw.get(parameter, {})
        try:
            series = pd.Series(values, dtype="float64").rename(column)
        except (TypeError, ValueError) as exc:
            raise NASAAPIError(f"NASA POWER returned invalid values for {parameter}.") from exc
        # POWER uses -999 for unavailable daily values.
        series = series.mask(series <= -999)
        frames.append(series)
    if not frames or all(frame.empty for frame in frames):
        raise NASAAPIError("NASA POWER returned no daily values for this request.")
    data = pd.concat(frames, axis=1)
    data.index = pd.to_datetime(data.index, format="%Y%m%d", errors="coerce")
    data.index.name = "date"
    data = data.loc[~data.index.isna()].sort_index().reset_index()
    data = data.rename(columns={"date": "date"})
    if data.empty or data.drop(columns="date").notna().sum().sum() == 0:
        raise NASAAPIError("NASA POWER returned dates but all requested measurements are missing.")
    return data
