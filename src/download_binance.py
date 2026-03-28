import io
import os
import time
import zipfile
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

BASE_URL = "https://api.binance.com"
VISION_BASE_URL = "https://data.binance.vision"
SYMBOL = "BTCUSDT"
INTERVAL = "1h"
LIMIT = 1000

KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_asset_volume", "number_of_trades",
    "taker_buy_base_volume", "taker_buy_quote_volume", "ignore"
]


def _to_datetime(series: pd.Series) -> pd.Series:
    max_abs = series.dropna().abs().max()
    unit = "us" if pd.notna(max_abs) and max_abs > 10**14 else "ms"
    return pd.to_datetime(series, unit=unit, utc=True)


def _normalize_klines(df: pd.DataFrame) -> pd.DataFrame:
    df = df.iloc[:, :len(KLINE_COLUMNS)].copy()
    df.columns = KLINE_COLUMNS

    numeric_cols = [
        "open", "high", "low", "close", "volume",
        "quote_asset_volume", "number_of_trades",
        "taker_buy_base_volume", "taker_buy_quote_volume"
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["open_time"] = _to_datetime(pd.to_numeric(df["open_time"], errors="coerce"))
    df["close_time"] = _to_datetime(pd.to_numeric(df["close_time"], errors="coerce"))

    return df


def _month_start(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _add_month(dt: datetime) -> datetime:
    year = dt.year + (dt.month // 12)
    month = 1 if dt.month == 12 else dt.month + 1
    if dt.month != 12:
        year = dt.year
    return dt.replace(year=year, month=month, day=1)


def _iter_month_starts(start_dt: datetime, end_dt: datetime):
    current = _month_start(start_dt)
    end_month = _month_start(end_dt)
    while current <= end_month:
        yield current
        current = _add_month(current)


def _download_vision_zip_csv(url: str) -> pd.DataFrame | None:
    r = requests.get(url, timeout=60)
    if r.status_code == 404:
        return None
    r.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = [name for name in zf.namelist() if name.endswith(".csv")]
        if not names:
            raise ValueError(f"Aucun CSV trouve dans {url}")
        with zf.open(names[0]) as fh:
            return pd.read_csv(fh, header=None)


def download_from_data_vision(symbol="BTCUSDT", interval="1h", months_back=120):
    now = datetime.now(timezone.utc)
    start_dt = now - timedelta(days=months_back * 30)

    frames = []

    for month_dt in _iter_month_starts(start_dt, now):
        month_url = (
            f"{VISION_BASE_URL}/data/spot/monthly/klines/"
            f"{symbol}/{interval}/{symbol}-{interval}-{month_dt:%Y-%m}.zip"
        )
        month_df = _download_vision_zip_csv(month_url)
        if month_df is not None:
            frames.append(month_df)

    current_day = _month_start(now)
    while current_day.date() <= now.date():
        day_url = (
            f"{VISION_BASE_URL}/data/spot/daily/klines/"
            f"{symbol}/{interval}/{symbol}-{interval}-{current_day:%Y-%m-%d}.zip"
        )
        day_df = _download_vision_zip_csv(day_url)
        if day_df is not None:
            frames.append(day_df)
        current_day += timedelta(days=1)

    if not frames:
        raise RuntimeError("Aucune donnee recuperee depuis data.binance.vision")

    df = pd.concat(frames, ignore_index=True)
    df = _normalize_klines(df)
    df = df.drop_duplicates(subset=["open_time"]).sort_values("open_time").reset_index(drop=True)
    return df

def fetch_klines(symbol="BTCUSDT", interval="1h", start_time=None, end_time=None, limit=1000):
    url = f"{BASE_URL}/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }
    if start_time is not None:
        params["startTime"] = start_time
    if end_time is not None:
        params["endTime"] = end_time

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def download_full_history(symbol="BTCUSDT", interval="1h", months_back=120):
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - months_back * 30 * 24 * 60 * 60 * 1000

    all_rows = []
    current_start = start_ms

    try:
        while True:
            rows = fetch_klines(symbol=symbol, interval=interval, start_time=current_start, limit=LIMIT)
            if not rows:
                break

            all_rows.extend(rows)

            last_open_time = rows[-1][0]
            next_start = last_open_time + 1

            if next_start >= now_ms:
                break

            if len(rows) < LIMIT:
                break

            current_start = next_start
            time.sleep(0.2)

        df = pd.DataFrame(all_rows, columns=KLINE_COLUMNS)
        df = _normalize_klines(df)
        df = df.drop_duplicates(subset=["open_time"]).sort_values("open_time").reset_index(drop=True)
        return df
    except requests.exceptions.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code == 451:
            print("Binance REST API indisponible depuis ce pod (HTTP 451). Fallback vers data.binance.vision...")
            return download_from_data_vision(symbol=symbol, interval=interval, months_back=months_back)
        raise

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    df = download_full_history(symbol=SYMBOL, interval=INTERVAL, months_back=120)
    out = f"data/{SYMBOL.lower()}_{INTERVAL}.csv"
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} rows to {out}")
    print(df.head())
    print(df.tail())
