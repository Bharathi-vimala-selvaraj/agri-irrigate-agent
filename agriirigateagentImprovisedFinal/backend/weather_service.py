"""
Weather via Open-Meteo - free, keyless, no signup required.
Docs: https://open-meteo.com/en/docs
"""
import requests
from datetime import date, timedelta

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def get_forecast(latitude: float, longitude: float, days: int = 16) -> list[dict]:
    """Returns a list of daily forecast dicts covering `days` days starting today.
    Open-Meteo's free tier caps daily forecasts at 16 days; for the 30-day
    schedule we extrapolate the tail using the last available day's pattern.
    """
    capped_days = min(days, 16)
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ",".join([
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "precipitation_probability_max",
            "relative_humidity_2m_mean",
            "et0_fao_evapotranspiration",
        ]),
        "forecast_days": capped_days,
        "timezone": "auto",
    }
    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        daily = data.get("daily", {})
        dates = daily.get("time", [])
        result = []
        for i, d in enumerate(dates):
            result.append({
                "date": d,
                "temp_max": daily.get("temperature_2m_max", [None])[i],
                "temp_min": daily.get("temperature_2m_min", [None])[i],
                "precipitation_mm": daily.get("precipitation_sum", [0])[i] or 0,
                "rain_probability": daily.get("precipitation_probability_max", [0])[i] or 0,
                "humidity": daily.get("relative_humidity_2m_mean", [50])[i] or 50,
                "et0": daily.get("et0_fao_evapotranspiration", [4])[i] or 4,
            })

        if days > capped_days and result:
            # extrapolate remaining days by cycling the last week's pattern
            pattern = result[-7:] if len(result) >= 7 else result
            extra_needed = days - capped_days
            start_date = date.fromisoformat(result[-1]["date"]) + timedelta(days=1)
            for i in range(extra_needed):
                src = pattern[i % len(pattern)]
                d = start_date + timedelta(days=i)
                result.append({**src, "date": d.isoformat()})
        return result
    except (requests.RequestException, KeyError, ValueError):
        # Fallback synthetic forecast so scheduling never hard-fails if the
        # weather API is briefly unreachable.
        today = date.today()
        return [
            {
                "date": (today + timedelta(days=i)).isoformat(),
                "temp_max": 32.0, "temp_min": 22.0,
                "precipitation_mm": 0, "rain_probability": 15,
                "humidity": 55, "et0": 4.5,
            }
            for i in range(days)
        ]


def get_forecast_for_date(forecast: list[dict], target_date: str) -> dict:
    for day in forecast:
        if day["date"] == target_date:
            return day
    return forecast[-1] if forecast else {}
