import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from xgboost import XGBClassifier

DATA_PATH = "data/btcusdt_1h_features.csv"

FEATURES = [
    "ret_1", "ret_3", "ret_6", "ret_12", "ret_24",
    "hl_range", "oc_change", "upper_wick", "lower_wick",
    "vol_ratio_24", "volatility_24", "volatility_72",
    "dist_ma_12", "dist_ma_24", "dist_ma_72",
    "rsi_14", "atr_pct_14", "hour_of_day", "day_of_week"
]

def main():
    df = pd.read_csv(DATA_PATH, parse_dates=["open_time", "close_time"])
    df = df.sort_values("open_time").reset_index(drop=True)

    n = len(df)
    train_end = int(n * 0.7)
    valid_end = int(n * 0.85)

    train_df = df.iloc[:train_end].copy()
    valid_df = df.iloc[train_end:valid_end].copy()
    test_df = df.iloc[valid_end:].copy()

    X_train, y_train = train_df[FEATURES], train_df["target"].astype(int)
    X_valid, y_valid = valid_df[FEATURES], valid_df["target"].astype(int)
    X_test, y_test = test_df[FEATURES], test_df["target"].astype(int)

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

    model.fit(
        X_train, y_train,
        eval_set=[(X_valid, y_valid)],
        verbose=False
    )

    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)

    print("=== Test metrics ===")
    print("accuracy :", round(accuracy_score(y_test, pred), 4))
    print("precision:", round(precision_score(y_test, pred), 4))
    print("recall   :", round(recall_score(y_test, pred), 4))
    print("f1       :", round(f1_score(y_test, pred), 4))
    print("roc_auc  :", round(roc_auc_score(y_test, proba), 4))

    importances = pd.Series(model.feature_importances_, index=FEATURES).sort_values(ascending=False)
    print("\n=== Top feature importances ===")
    print(importances.head(10))

    test_df["proba_up"] = proba
    test_df["pred"] = pred

    out_cols = [
        "open_time", "close", "future_return_3h", "target", "proba_up", "pred"
    ]
    test_df[out_cols].to_csv("data/test_predictions.csv", index=False)

    print("\nSaved predictions to data/test_predictions.csv")

    print("\n=== Analyse par seuil de confiance ===")
    thresholds = [0.50, 0.55, 0.60, 0.65]

    for th in thresholds:
        subset = test_df[test_df["proba_up"] >= th].copy()

        if len(subset) == 0:
            print(f"threshold {th}: aucun signal")
            continue

        hit_rate = (subset["target"] == 1).mean()
        avg_ret = subset["future_return_3h"].mean()

        print(
            f"threshold {th}: "
            f"nb_signaux={len(subset)}, "
            f"hit_rate={hit_rate:.4f}, "
            f"avg_return={avg_ret:.5f}"
        )

if __name__ == "__main__":
    main()