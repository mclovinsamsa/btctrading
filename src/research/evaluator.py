from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd
from xgboost import XGBClassifier


@dataclass
class WalkForwardSetup:
    train_ratio: float = 0.60
    test_ratio: float = 0.10
    fee_per_trade: float = 0.0004


def _evaluate_threshold(scored_test: pd.DataFrame, threshold: float, fee_per_trade: float) -> Dict[str, float]:
    out = scored_test.copy()
    out["trade"] = (out["proba_up"] >= threshold).astype(int)
    out["net_return"] = np.where(out["trade"] == 1, out["future_return_3h"] - fee_per_trade, 0.0)

    trades = out[out["trade"] == 1]
    nb_trades = len(trades)
    hit_rate = (trades["target"] == 1).mean() if nb_trades > 0 else 0.0
    avg_net_return = trades["net_return"].mean() if nb_trades > 0 else 0.0
    strategy_factor = float((1 + out["net_return"]).prod())

    return {
        "nb_trades": nb_trades,
        "hit_rate": hit_rate,
        "avg_net_return": avg_net_return,
        "strategy_factor": strategy_factor,
    }


def run_walk_forward(
    df: pd.DataFrame,
    features,
    xgb_params,
    threshold: float,
    setup: WalkForwardSetup,
    random_state: int = 42,
) -> Dict[str, float]:
    data = df.sort_values("open_time").reset_index(drop=True)
    n = len(data)

    train_size = int(n * setup.train_ratio)
    test_size = int(n * setup.test_ratio)
    step_size = test_size

    all_window_scores = []
    start_test = train_size

    while start_test + test_size <= n:
        train_df = data.iloc[:start_test]
        test_df = data.iloc[start_test : start_test + test_size]

        model = XGBClassifier(
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=random_state,
            **xgb_params,
        )

        model.fit(train_df[list(features)], train_df["target"].astype(int), verbose=False)

        scored = test_df.copy()
        scored["proba_up"] = model.predict_proba(test_df[list(features)])[:, 1]

        all_window_scores.append(_evaluate_threshold(scored, threshold, setup.fee_per_trade))

        start_test += step_size

    if not all_window_scores:
        return {
            "nb_windows": 0,
            "mean_nb_trades": 0.0,
            "mean_hit_rate": 0.0,
            "mean_avg_net_return": 0.0,
            "mean_strategy_factor": 1.0,
            "objective_score": -999.0,
        }

    res_df = pd.DataFrame(all_window_scores)

    mean_nb_trades = float(res_df["nb_trades"].mean())
    mean_hit_rate = float(res_df["hit_rate"].mean())
    mean_avg_net_return = float(res_df["avg_net_return"].mean())
    mean_strategy_factor = float(res_df["strategy_factor"].mean())

    # Score simple orienté trading: rendement net + stabilité de hit rate, pénalisé si trop peu de trades
    low_trade_penalty = 0.0 if mean_nb_trades >= 20 else -0.005
    objective_score = (mean_avg_net_return * 100.0) + (mean_hit_rate - 0.5) + low_trade_penalty

    return {
        "nb_windows": int(len(res_df)),
        "mean_nb_trades": mean_nb_trades,
        "mean_hit_rate": mean_hit_rate,
        "mean_avg_net_return": mean_avg_net_return,
        "mean_strategy_factor": mean_strategy_factor,
        "objective_score": objective_score,
    }
