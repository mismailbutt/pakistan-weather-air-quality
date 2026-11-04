import sqlite3
import time
import requests
import pandas as pd
from pydantic import BaseModel, field_validator, ValidationError
from typing import Optional

CITIES = {
    "Lahore": (31.55, 74.34),
    "Karachi": (24.86, 67.01),
    "Islamabad": (33.68, 73.05),
    "Peshawar": (34.01, 71.52),
    "Quetta": (30.18, 66.99),
}

WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


# ---------- Pydantic: checks one row ----------
class Reading(BaseModel):
    city: str
    time: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    rain: Optional[float] = None
    wind: Optional[float] = None
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    aqi: Optional[float] = None

    @field_validator("temperature")
    def check_temp(cls, v):
        if v is not None and not (-50 <= v <= 60):
            raise ValueError("temperature not realistic")
        return v

    @field_validator("humidity")
    def check_humidity(cls, v):
        if v is not None and not (0 <= v <= 100):
            raise ValueError("humidity must be 0-100")
        return v

    @field_validator("rain", "wind", "pm25", "pm10", "aqi")
    def check_not_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("value cannot be negative")
        return v


# ---------- EXTRACT ----------
def extract(city, lat, lon):
    base = {"latitude": lat, "longitude": lon,
            "start_date": "2024-01-01", "end_date": "2025-12-31",
            "timezone": "Asia/Karachi"}

    w = requests.get(WEATHER_URL, params={
        **base,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
    }).json()["hourly"]

    a = requests.get(AIR_URL, params={
        **base,
        "hourly": "pm2_5,pm10,us_aqi"
    }).json()["hourly"]

    df = pd.DataFrame(w).merge(pd.DataFrame(a), on="time")
    df = df.rename(columns={
        "temperature_2m": "temperature",
        "relative_humidity_2m": "humidity",
        "precipitation": "rain",
        "wind_speed_10m": "wind",
        "pm2_5": "pm25",
        "us_aqi": "aqi",
    })
    df["city"] = city
    return df


# ---------- TRANSFORM ----------
def transform(df):
    good, bad = [], 0
    for row in df.to_dict("records"):
        row = {k: (None if pd.isna(v) else v) for k, v in row.items()}
        try:
            good.append(Reading.model_validate(row).model_dump())   # Pydantic check  # Pydantic check
        except ValidationError:
            bad += 1
    print(f"  valid rows: {len(good)}, rejected rows: {bad}")

    df = pd.DataFrame(good)                              # pandas cleaning
    df["time"] = pd.to_datetime(df["time"])
    df = df.drop_duplicates(subset=["city", "time"])
    df = df.sort_values(["city", "time"])
    cols = ["temperature", "humidity", "rain", "wind", "pm25", "pm10", "aqi"]
    df[cols] = df.groupby("city")[cols].transform(lambda s: s.interpolate(limit=6))
    df["date"] = df["time"].dt.strftime("%Y-%m-%d")
    df["time"] = df["time"].dt.strftime("%Y-%m-%d %H:%M")
    return df


# ---------- LOAD ----------
def load(df):
    conn = sqlite3.connect("weather.db")
    df.to_sql("readings", conn, if_exists="replace", index=False)
    conn.close()


if __name__ == "__main__":
    all_data = []
    for city, (lat, lon) in CITIES.items():
        print("Working on", city)
        all_data.append(transform(extract(city, lat, lon)))
        time.sleep(1)
    final = pd.concat(all_data)
    load(final)
    print("Done! Rows saved:", len(final))