import pandas as pd
import numpy as np
from xgboost import XGBClassifier

DATA_PATH = "data/btcusdt_1h_features.csv"

FEATURES = [
    "ret_1", "ret_3", "ret_6", "ret_12", "ret_24",
    "hl_range", "oc_change", "upper_wick", "lower_wick",
    "vol_ratio_24", "volatility_24", "volatility_72",
    "dist_ma_12", "dist_ma_24", "dist_ma_72",
    "rsi_14", "atr_pct_14", "hour_of_day", "day_of_week"
]

THRESHOLDS = [0.55, 0.58, 0.60, 0.62, 0.65]
FEE_PER_TRADE = 0.0004  # 0.04%

def evaluate_threshold(test_df, threshold):
    out = test_df.copy()

    out["trade"] = (out["proba_up"] >= threshold).astype(int)
    out["gross_return"] = np.where(out["trade"] == 1, out["future_return_3h"], 0.0)
    out["net_return"] = np.where(out["trade"] == 1, out["future_return_3h"] - FEE_PER_TRADE, 0.0)

    trades = out[out["trade"] == 1].copy()

    nb_trades = len(trades)
    hit_rate = (trades["target"] == 1).mean() if nb_trades > 0 else 0.0
    avg_gross = trades["future_return_3h"].mean() if nb_trades > 0 else 0.0
    avg_net = trades["net_return"].mean() if nb_trades > 0 else 0.0

    strategy_factor = (1 + out["net_return"]).prod()
    market_factor = (1 + out["future_return_3h"]).prod()

    return {
        "threshold": threshold,
        "nb_trades": nb_trades,
        "hit_rate": hit_rate,
        "avg_gross_return": avg_gross,
        "avg_net_return": avg_net,
        "strategy_factor": strategy_factor,
        "market_factor": market_factor,
    }

def train_and_score(train_df, test_df):
    X_train = train_df[FEATURES]
    y_train = train_df["target"].astype(int)

    X_test = test_df[FEATURES]

    model = XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=42
    )

    model.fit(X_train, y_train, verbose=False)

    out = test_df.copy()
    out["proba_up"] = model.predict_proba(X_test)[:, 1]
    return out

def main():
    df = pd.read_csv(DATA_PATH, parse_dates=["open_time", "close_time"])
    df = df.sort_values("open_time").reset_index(drop=True)

    n = len(df)
    train_size = int(n * 0.60)
    test_size = int(n * 0.10)
    step_size = test_size

    all_results = []

    start_test = train_size
    window_num = 1

    while start_test + test_size <= n:
        train_df = df.iloc[:start_test].copy()
        test_df = df.iloc[start_test:start_test + test_size].copy()

        scored_test = train_and_score(train_df, test_df)

        for th in THRESHOLDS:
            res = evaluate_threshold(scored_test, th)
            res["window"] = window_num
            res["test_start"] = scored_test["open_time"].min()
            res["test_end"] = scored_test["open_time"].max()
            res["nb_rows_test"] = len(scored_test)
            all_results.append(res)

        start_test += step_size
        window_num += 1

    results_df = pd.DataFrame(all_results)

    print("=== Résultats détaillés par fenêtre et seuil ===")
    print(results_df[[
        "window", "threshold", "test_start", "test_end",
        "nb_trades", "hit_rate", "avg_gross_return",
        "avg_net_return", "strategy_factor", "market_factor"
    ]])

    summary_df = (
        results_df
        .groupby("threshold", as_index=False)
        .agg({
            "window": "count",
            "nb_trades": "mean",
            "hit_rate": "mean",
            "avg_gross_return": "mean",
            "avg_net_return": "mean",
            "strategy_factor": "mean",
            "market_factor": "mean"
        })
        .rename(columns={"window": "nb_windows"})
    )

    print("\n=== Résumé moyen par seuil ===")
    print(summary_df)

    summary_df.to_csv("data/walk_forward_threshold_summary.csv", index=False)
    results_df.to_csv("data/walk_forward_threshold_details.csv", index=False)

    print("\nSaved:")
    print("- data/walk_forward_threshold_summary.csv")
    print("- data/walk_forward_threshold_details.csv")

if __name__ == "__main__":
    main()