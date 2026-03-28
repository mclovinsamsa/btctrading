import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

from src.research.exhaustive_btc_search import (
    DataConfig,
    SearchConfig,
    ensure_data,
    load_ohlcv,
    prepare_dataset,
    resolve_device,
)


def _parse_json_field(value):
    if isinstance(value, str):
        return json.loads(value)
    return value


def _max_drawdown(equity: pd.Series) -> float:
    if len(equity) == 0:
        return 0.0
    roll_max = equity.cummax()
    drawdown = (equity / roll_max) - 1.0
    return float(abs(drawdown.min()))


def _evaluate_slice(df: pd.DataFrame, threshold: float, total_cost: float) -> Dict[str, float]:
    out = df.copy()
    out["trade"] = (out["proba_up"] >= threshold).astype(int)
    out["net_return"] = np.where(out["trade"] == 1, out["future_return"] - total_cost, 0.0)

    trades = out[out["trade"] == 1].copy()
    total_trades = int(len(trades))

    hit_rate = float((trades["target"] == 1).mean()) if total_trades > 0 else 0.0
    avg_trade_return = float(trades["net_return"].mean()) if total_trades > 0 else 0.0
    median_trade_return = float(trades["net_return"].median()) if total_trades > 0 else 0.0

    gross_profit = float(trades.loc[trades["net_return"] > 0, "net_return"].sum())
    gross_loss = float(trades.loc[trades["net_return"] < 0, "net_return"].sum())
    profit_factor = gross_profit / abs(gross_loss) if gross_loss < 0 else float("inf")

    equity = (1.0 + out["net_return"]).cumprod()
    market = (1.0 + out["future_return"]).cumprod()

    strategy_factor = float(equity.iloc[-1]) if len(equity) > 0 else 1.0
    market_factor = float(market.iloc[-1]) if len(market) > 0 else 1.0
    max_dd = _max_drawdown(equity)

    return {
        "rows": int(len(out)),
        "total_trades": total_trades,
        "trade_ratio": float(total_trades / max(len(out), 1)),
        "hit_rate": hit_rate,
        "avg_trade_return": avg_trade_return,
        "median_trade_return": median_trade_return,
        "profit_factor": float(profit_factor),
        "strategy_factor": strategy_factor,
        "market_factor": market_factor,
        "max_drawdown": max_dd,
    }


def _regime_label(r: float) -> str:
    if pd.isna(r):
        return "unknown"
    if r > 0.10:
        return "bull"
    if r < -0.10:
        return "bear"
    return "range"


def _compute_regime_stats(df_holdout: pd.DataFrame, threshold: float, total_cost: float) -> pd.DataFrame:
    out = df_holdout.copy()
    out["ret_30d"] = out["close"].pct_change(24 * 30)
    out["regime"] = out["ret_30d"].apply(_regime_label)
    out["trade"] = (out["proba_up"] >= threshold).astype(int)
    out["net_return"] = np.where(out["trade"] == 1, out["future_return"] - total_cost, 0.0)

    rows = []
    for regime, g in out.groupby("regime"):
        trades = g[g["trade"] == 1]
        rows.append(
            {
                "regime": regime,
                "rows": int(len(g)),
                "trades": int(len(trades)),
                "hit_rate": float((trades["target"] == 1).mean()) if len(trades) > 0 else 0.0,
                "avg_trade_return": float(trades["net_return"].mean()) if len(trades) > 0 else 0.0,
                "strategy_factor": float((1.0 + g["net_return"]).prod()) if len(g) > 0 else 1.0,
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=["regime", "rows", "trades", "hit_rate", "avg_trade_return", "strategy_factor"]
        )
    return pd.DataFrame(rows).sort_values("regime")


def _walk_forward_holdout(
    df: pd.DataFrame,
    features: List[str],
    model_cfg: Dict,
    threshold: float,
    total_cost: float,
    device: str,
    random_state: int,
    train_end: int,
    wf_windows: int,
) -> pd.DataFrame:
    n = len(df)
    holdout_len = n - train_end
    chunk = max(holdout_len // max(wf_windows, 1), 1)

    rows = []
    start = train_end
    w = 1

    while start < n and w <= wf_windows:
        end = min(start + chunk, n)
        train_df = df.iloc[:start].copy()
        test_df = df.iloc[start:end].copy()

        if len(test_df) < 50 or len(train_df) < 1000:
            break

        model = XGBClassifier(
            objective="binary:logistic",
            eval_metric="logloss",
            tree_method="hist",
            device=device,
            random_state=random_state,
            **model_cfg,
        )
        model.fit(train_df[features], train_df["target"].astype(int), verbose=False)

        scored = test_df.copy()
        scored["proba_up"] = model.predict_proba(test_df[features])[:, 1]
        met = _evaluate_slice(scored, threshold=threshold, total_cost=total_cost)
        met["wf_window"] = w
        met["start_time"] = str(scored["open_time"].min())
        met["end_time"] = str(scored["open_time"].max())
        rows.append(met)

        start = end
        w += 1

    return pd.DataFrame(rows)


def _decision(metrics_holdout: Dict[str, float], wf_df: pd.DataFrame) -> Tuple[str, List[str]]:
    reasons = []

    if metrics_holdout["total_trades"] < 500:
        reasons.append("Trop peu de trades sur holdout (<500)")
    if metrics_holdout["avg_trade_return"] <= 0:
        reasons.append("Rendement moyen par trade <= 0")
    if metrics_holdout["hit_rate"] < 0.55:
        reasons.append("Hit rate holdout < 55%")
    if metrics_holdout["max_drawdown"] > 0.35:
        reasons.append("Max drawdown holdout > 35%")

    if not wf_df.empty:
        wf_neg = int((wf_df["avg_trade_return"] <= 0).sum())
        if wf_neg >= max(2, len(wf_df) // 2):
            reasons.append("Walk-forward holdout instable (trop de fenêtres négatives)")

    verdict = "GO" if not reasons else "NO_GO"
    return verdict, reasons


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Final robust validation from funnel best config")
    p.add_argument("--best-config", default="data/funnel_best_config.json")
    p.add_argument("--out-dir", default="data")
    p.add_argument("--symbol", default="BTCUSDT")
    p.add_argument("--months-back", type=int, default=120)
    p.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    p.add_argument("--holdout-ratio", type=float, default=0.20)
    p.add_argument("--fee", type=float, default=0.0004)
    p.add_argument("--slippage", type=float, default=0.0008)
    p.add_argument("--wf-windows", type=int, default=4)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(args.best_config, "r", encoding="utf-8") as f:
        best = json.load(f)

    data_cfg_dict = _parse_json_field(best["data_config"])
    model_cfg = _parse_json_field(best["model_config"])
    threshold = float(best.get("threshold", 0.5))

    data_cfg = DataConfig(
        ret_windows=tuple(data_cfg_dict["ret_windows"]),
        vol_windows=tuple(data_cfg_dict["vol_windows"]),
        ma_windows=tuple(data_cfg_dict["ma_windows"]),
        rsi_period=int(data_cfg_dict["rsi_period"]),
        atr_period=int(data_cfg_dict["atr_period"]),
        horizon_h=int(data_cfg_dict["horizon_h"]),
        target_threshold=float(data_cfg_dict["target_threshold"]),
        mtf_intervals=tuple(data_cfg_dict["mtf_intervals"]),
    )

    search_cfg = SearchConfig(
        symbol=args.symbol,
        months_back=args.months_back,
        aux_intervals=tuple(data_cfg.mtf_intervals),
        random_state=args.seed,
    )

    paths = ensure_data(search_cfg, out_dir=out_dir, force_download=False)
    base_df = load_ohlcv(paths[search_cfg.base_interval])
    aux_frames = {
        interval: load_ohlcv(path)
        for interval, path in paths.items()
        if interval != search_cfg.base_interval
    }

    dataset, features = prepare_dataset(base_df, aux_frames, data_cfg)
    if "close" not in dataset.columns:
        dataset = dataset.merge(base_df[["open_time", "close"]], on="open_time", how="left")
    dataset = dataset.sort_values("open_time").reset_index(drop=True)
    if dataset.empty:
        raise RuntimeError("Validation dataset is empty after feature engineering. Check input data alignment.")

    n = len(dataset)
    train_end = int(n * (1.0 - args.holdout_ratio))
    train_df = dataset.iloc[:train_end].copy()
    holdout_df = dataset.iloc[train_end:].copy()
    if train_df.empty or holdout_df.empty:
        raise RuntimeError("Train or holdout split is empty. Adjust holdout ratio or dataset inputs.")

    device = resolve_device(args.device)
    total_cost = float(args.fee + args.slippage)

    model = XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        tree_method="hist",
        device=device,
        random_state=args.seed,
        **model_cfg,
    )
    model.fit(train_df[features], train_df["target"].astype(int), verbose=False)

    holdout_scored = holdout_df.copy()
    holdout_scored["proba_up"] = model.predict_proba(holdout_df[features])[:, 1]

    holdout_metrics = _evaluate_slice(holdout_scored, threshold=threshold, total_cost=total_cost)
    regime_df = _compute_regime_stats(holdout_scored, threshold=threshold, total_cost=total_cost)
    wf_df = _walk_forward_holdout(
        df=dataset,
        features=features,
        model_cfg=model_cfg,
        threshold=threshold,
        total_cost=total_cost,
        device=device,
        random_state=args.seed,
        train_end=train_end,
        wf_windows=args.wf_windows,
    )

    verdict, reasons = _decision(holdout_metrics, wf_df)

    report = {
        "verdict": verdict,
        "reasons": reasons,
        "device": device,
        "threshold": threshold,
        "total_cost_per_trade": total_cost,
        "train_rows": int(len(train_df)),
        "holdout_rows": int(len(holdout_df)),
        "n_features": int(len(features)),
        "data_config": data_cfg_dict,
        "model_config": model_cfg,
        "holdout_metrics": holdout_metrics,
        "walk_forward_holdout_mean": wf_df.mean(numeric_only=True).to_dict() if not wf_df.empty else {},
    }

    report_path = out_dir / "final_validation_report.json"
    preds_path = out_dir / "final_validation_holdout_predictions.csv"
    regime_path = out_dir / "final_validation_regime_stats.csv"
    wf_path = out_dir / "final_validation_walk_forward.csv"

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    keep_cols = ["open_time", "future_return", "target", "proba_up"]
    holdout_scored[keep_cols].to_csv(preds_path, index=False)
    regime_df.to_csv(regime_path, index=False)
    wf_df.to_csv(wf_path, index=False)

    print("=== FINAL VALIDATION ===")
    print(f"Verdict: {verdict}")
    if reasons:
        for r in reasons:
            print(f"- {r}")
    print("\nHoldout metrics:")
    print(json.dumps(holdout_metrics, indent=2))
    print(f"\nSaved: {report_path}")
    print(f"Saved: {preds_path}")
    print(f"Saved: {regime_path}")
    print(f"Saved: {wf_path}")


if __name__ == "__main__":
    main()
