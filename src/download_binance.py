import os
import time
import requests
import pandas as pd

BASE_URL = "https://api.binance.com"
SYMBOL = "BTCUSDT"
INTERVAL = "1h"
LIMIT = 1000

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

    cols = [
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base_volume", "taker_buy_quote_volume", "ignore"
    ]

    df = pd.DataFrame(all_rows, columns=cols)
    df = df.drop_duplicates(subset=["open_time"]).sort_values("open_time")

    numeric_cols = [
        "open", "high", "low", "close", "volume",
        "quote_asset_volume", "number_of_trades",
        "taker_buy_base_volume", "taker_buy_quote_volume"
    ]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)

    return df

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    df = download_full_history(symbol=SYMBOL, interval=INTERVAL, months_back=120)
    out = f"data/{SYMBOL.lower()}_{INTERVAL}.csv"
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} rows to {out}")
    print(df.head())
    print(df.tail())