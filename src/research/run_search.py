import json
from pathlib import Path

import pandas as pd

from src.research.evaluator import WalkForwardSetup, run_walk_forward
from src.research.search_space import generate_experiments

DATA_PATH = Path("data/btcusdt_1h_features.csv")
OUTPUT_LEADERBOARD = Path("data/research_leaderboard.csv")
TOP_K = 20


def main():
    df = pd.read_csv(DATA_PATH, parse_dates=["open_time", "close_time"])

    experiments = generate_experiments(
        min_groups=3,
        max_groups=6,
        max_param_combinations=40,
    )

    setup = WalkForwardSetup(
        train_ratio=0.60,
        test_ratio=0.10,
        fee_per_trade=0.0004,
    )

    rows = []
    total = len(experiments)

    for idx, exp in enumerate(experiments, start=1):
        score = run_walk_forward(
            df=df,
            features=exp.features,
            xgb_params=exp.xgb_params,
            threshold=exp.threshold,
            setup=setup,
        )

        rows.append(
            {
                "rank_hint": idx,
                "feature_groups": "|".join(exp.feature_groups),
                "features": "|".join(exp.features),
                "threshold": exp.threshold,
                "xgb_params": json.dumps(exp.xgb_params, sort_keys=True),
                **score,
            }
        )

        if idx % 25 == 0:
            print(f"Progress: {idx}/{total} experiments")

    leaderboard = pd.DataFrame(rows).sort_values(
        ["objective_score", "mean_strategy_factor", "mean_avg_net_return"],
        ascending=False,
    )

    leaderboard.to_csv(OUTPUT_LEADERBOARD, index=False)

    print("\n=== Top configurations ===")
    print(
        leaderboard[
            [
                "feature_groups",
                "threshold",
                "objective_score",
                "mean_hit_rate",
                "mean_avg_net_return",
                "mean_nb_trades",
                "mean_strategy_factor",
            ]
        ].head(TOP_K)
    )
    print(f"\nSaved leaderboard -> {OUTPUT_LEADERBOARD}")


if __name__ == "__main__":
    main()
