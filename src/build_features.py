import pandas as pd
import numpy as np

INPUT_PATH = "data/btcusdt_1h.csv"
OUTPUT_PATH = "data/btcusdt_1h_features.csv"

UP_THRESHOLD = 0.004
DOWN_THRESHOLD = -0.004

def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)

    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - prev_close).abs()
    tr3 = (df["low"] - prev_close).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.rolling(period).mean()
    return atr

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().sort_values("open_time")

    # Momentum
    df["ret_1"] = df["close"].pct_change(1)
    df["ret_3"] = df["close"].pct_change(3)
    df["ret_6"] = df["close"].pct_change(6)
    df["ret_12"] = df["close"].pct_change(12)
    df["ret_24"] = df["close"].pct_change(24)

    # Structure de bougie
    df["hl_range"] = (df["high"] - df["low"]) / df["close"]
    df["oc_change"] = (df["close"] - df["open"]) / df["open"]
    df["upper_wick"] = (df["high"] - df[["open", "close"]].max(axis=1)) / df["close"]
    df["lower_wick"] = (df[["open", "close"]].min(axis=1) - df["low"]) / df["close"]

    # Volume
    df["vol_mean_24"] = df["volume"].rolling(24).mean()
    df["vol_ratio_24"] = df["volume"] / df["vol_mean_24"]

    # Volatilité
    df["volatility_24"] = df["ret_1"].rolling(24).std()
    df["volatility_72"] = df["ret_1"].rolling(72).std()

    # Tendance
    df["ma_12"] = df["close"].rolling(12).mean()
    df["ma_24"] = df["close"].rolling(24).mean()
    df["ma_72"] = df["close"].rolling(72).mean()

    df["dist_ma_12"] = (df["close"] / df["ma_12"]) - 1
    df["dist_ma_24"] = (df["close"] / df["ma_24"]) - 1
    df["dist_ma_72"] = (df["close"] / df["ma_72"]) - 1

    # Features additionnelles
    df["rsi_14"] = compute_rsi(df["close"], period=14)
    df["atr_14"] = compute_atr(df, period=14)
    df["atr_pct_14"] = df["atr_14"] / df["close"]

    df["hour_of_day"] = df["open_time"].dt.hour
    df["day_of_week"] = df["open_time"].dt.dayofweek

    # Rendement futur 3h
    df["future_return_3h"] = (df["close"].shift(-3) / df["close"]) - 1

    # Nouvelle target 3h
    df["target"] = np.where(
        df["future_return_3h"] > UP_THRESHOLD,
        1,
        np.where(df["future_return_3h"] < DOWN_THRESHOLD, 0, np.nan)
    )

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna().reset_index(drop=True)

    return df

if __name__ == "__main__":
    df = pd.read_csv(INPUT_PATH, parse_dates=["open_time", "close_time"])
    feat_df = build_features(df)
    feat_df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved {len(feat_df)} rows to {OUTPUT_PATH}")
    print("\nRépartition de la target :")
    print(feat_df["target"].value_counts(normalize=True).sort_index())
    print("\nColonnes de sortie clés : future_return_3h, target")
    print("\nAperçu :")
    print(feat_df.head())