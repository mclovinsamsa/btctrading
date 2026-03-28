import argparse
import json
import random
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from src.research.exhaustive_btc_search import (
    PROBA_THRESHOLDS,
    SearchConfig,
    ensure_data,
    evaluate_walk_forward,
    generate_data_configs,
    generate_model_configs,
    load_ohlcv,
    prepare_dataset,
    resolve_device,
)


def _pick_indices(total: int, target: int, seed: int) -> List[int]:
    if total <= target:
        return list(range(total))
    rng = random.Random(seed)
    return sorted(rng.sample(range(total), target))


def _to_json(x) -> str:
    return json.dumps(x, sort_keys=True)


def _compute_robust_score(df: pd.DataFrame) -> pd.Series:
    outperf = np.log(np.clip(df["strategy_factor"].astype(float), 1e-12, None)) - np.log(
        np.clip(df["market_factor"].astype(float), 1e-12, None)
    )
    trade_bonus = np.clip(df["total_trades"].astype(float) / 2000.0, 0.0, 1.0) * 0.20
    neg_return_penalty = np.where(df["avg_trade_return"] <= 0.0, -1.0, 0.0)
    high_dd_penalty = np.where(df["max_drawdown"] > 0.35, -0.75, 0.0)

    return (
        outperf
        + (30.0 * df["avg_trade_return"].astype(float))
        + (0.8 * (df["hit_rate"].astype(float) - 0.5))
        - (1.5 * df["max_drawdown"].astype(float))
        + trade_bonus
        + neg_return_penalty
        + high_dd_penalty
    )


def _rank_frame(
    df: pd.DataFrame,
    min_threshold: float,
    min_trades: int,
    max_drawdown_cap: float,
) -> pd.DataFrame:
    out = df.copy()
    out["robust_score"] = _compute_robust_score(out)
    out["is_viable"] = (
        (out["threshold"] >= min_threshold)
        & (out["total_trades"] >= min_trades)
        & (out["max_drawdown"] <= max_drawdown_cap)
        & (out["avg_trade_return"] > 0.0)
    )
    return out.sort_values(
        ["is_viable", "robust_score", "objective_score", "avg_trade_return"],
        ascending=[False, False, False, False],
    )


def _evaluate_experiment(
    dataset: pd.DataFrame,
    features: List[str],
    model_cfg: Dict,
    proba_threshold: float,
    search_cfg: SearchConfig,
    device: str,
    max_windows: int,
) -> Dict:
    return evaluate_walk_forward(
        df=dataset,
        features=features,
        model_params=model_cfg,
        proba_threshold=proba_threshold,
        device=device,
        fee_per_trade=search_cfg.fee_per_trade,
        train_ratio=search_cfg.train_ratio,
        test_ratio=search_cfg.test_ratio,
        random_state=search_cfg.random_state,
        max_windows=max_windows,
    )


def run_funnel(
    search_cfg: SearchConfig,
    out_dir: Path,
    requested_device: str,
    force_download: bool,
    max_model_combos: int,
    stage1_data: int,
    stage1_models: int,
    stage1_windows: int,
    stage2_top_data: int,
    stage2_top_models: int,
    stage2_windows: int,
    stage3_top_pairs: int,
    min_threshold: float,
    min_trades: int,
    max_drawdown_cap: float,
    shortlist_top_k: int,
) -> pd.DataFrame:
    out_dir.mkdir(parents=True, exist_ok=True)

    data_paths = ensure_data(search_cfg, out_dir=out_dir, force_download=force_download)
    base_df = load_ohlcv(data_paths[search_cfg.base_interval])
    aux_frames = {
        interval: load_ohlcv(path)
        for interval, path in data_paths.items()
        if interval != search_cfg.base_interval
    }

    all_data_cfgs = generate_data_configs(search_cfg.aux_intervals)
    all_model_cfgs = generate_model_configs(max_model_combos=max_model_combos)
    device = resolve_device(requested_device)

    print(f"Device selected: {device}")
    print(f"All data configs: {len(all_data_cfgs)}")
    print(f"All model configs: {len(all_model_cfgs)}")

    data_idx_s1 = _pick_indices(len(all_data_cfgs), stage1_data, search_cfg.random_state)
    model_idx_s1 = _pick_indices(len(all_model_cfgs), stage1_models, search_cfg.random_state + 1)
    thresholds_s1 = [x for x in [0.55, 0.60, 0.65] if x >= min_threshold]
    if not thresholds_s1:
        thresholds_s1 = [min_threshold]

    print(f"Stage1 => data:{len(data_idx_s1)} x model:{len(model_idx_s1)} x th:{len(thresholds_s1)}")

    rows_s1: List[Dict] = []
    dataset_cache: Dict[int, Tuple[pd.DataFrame, List[str]]] = {}
    done = 0

    for di in data_idx_s1:
        dcfg = all_data_cfgs[di]
        ds, feats = prepare_dataset(base_df, aux_frames, dcfg)
        if len(ds) < 1500:
            continue
        dataset_cache[di] = (ds, feats)

        for mi in model_idx_s1:
            mcfg = all_model_cfgs[mi]
            for th in thresholds_s1:
                done += 1
                m = _evaluate_experiment(ds, feats, mcfg, th, search_cfg, device, stage1_windows)
                rows_s1.append(
                    {
                        "stage": "stage1",
                        "data_idx": di,
                        "model_idx": mi,
                        "threshold": th,
                        "n_rows": len(ds),
                        "n_features": len(feats),
                        "data_config": _to_json(asdict(dcfg)),
                        "model_config": _to_json(mcfg),
                        **m,
                    }
                )
                if done % 100 == 0:
                    print(f"Stage1 progress: {done}")

    s1 = pd.DataFrame(rows_s1)
    if s1.empty:
        raise RuntimeError("Stage1 produced no results")
    s1 = _rank_frame(s1, min_threshold=min_threshold, min_trades=min_trades, max_drawdown_cap=max_drawdown_cap)
    s1.to_csv(out_dir / "funnel_stage1.csv", index=False)

    s1_for_select = s1[s1["is_viable"]].copy()
    if s1_for_select.empty:
        s1_for_select = s1.copy()

    top_data = (
        s1_for_select.groupby("data_idx", as_index=False)["robust_score"].max()
        .sort_values("robust_score", ascending=False)
        .head(stage2_top_data)["data_idx"]
        .tolist()
    )
    top_models = (
        s1_for_select.groupby("model_idx", as_index=False)["robust_score"].max()
        .sort_values("robust_score", ascending=False)
        .head(stage2_top_models)["model_idx"]
        .tolist()
    )

    stage2_thresholds = [x for x in PROBA_THRESHOLDS if x >= min_threshold]
    if not stage2_thresholds:
        stage2_thresholds = [min_threshold]
    print(f"Stage2 => data:{len(top_data)} x model:{len(top_models)} x th:{len(stage2_thresholds)}")

    rows_s2: List[Dict] = []
    done = 0

    for di in top_data:
        dcfg = all_data_cfgs[di]
        if di not in dataset_cache:
            ds, feats = prepare_dataset(base_df, aux_frames, dcfg)
            if len(ds) < 1500:
                continue
            dataset_cache[di] = (ds, feats)
        ds, feats = dataset_cache[di]

        for mi in top_models:
            mcfg = all_model_cfgs[mi]
            for th in stage2_thresholds:
                done += 1
                m = _evaluate_experiment(ds, feats, mcfg, th, search_cfg, device, stage2_windows)
                rows_s2.append(
                    {
                        "stage": "stage2",
                        "data_idx": di,
                        "model_idx": mi,
                        "threshold": th,
                        "n_rows": len(ds),
                        "n_features": len(feats),
                        "data_config": _to_json(asdict(dcfg)),
                        "model_config": _to_json(mcfg),
                        **m,
                    }
                )
                if done % 100 == 0:
                    print(f"Stage2 progress: {done}")

    s2 = pd.DataFrame(rows_s2)
    if s2.empty:
        raise RuntimeError("Stage2 produced no results")
    s2 = _rank_frame(s2, min_threshold=min_threshold, min_trades=min_trades, max_drawdown_cap=max_drawdown_cap)
    s2.to_csv(out_dir / "funnel_stage2.csv", index=False)

    s2_for_select = s2[s2["is_viable"]].copy()
    if s2_for_select.empty:
        s2_for_select = s2.copy()

    finalists = (
        s2_for_select.sort_values("robust_score", ascending=False)
        .head(stage3_top_pairs)[["data_idx", "model_idx"]]
        .drop_duplicates()
        .to_dict("records")
    )
    fine_start = max(0.50, min_threshold)
    fine_thresholds = [round(x, 2) for x in np.arange(fine_start, 0.701, 0.01)]

    print(f"Stage3 => pairs:{len(finalists)} x fine_thresholds:{len(fine_thresholds)}")
    rows_s3: List[Dict] = []
    done = 0

    for pair in finalists:
        di = int(pair["data_idx"])
        mi = int(pair["model_idx"])
        dcfg = all_data_cfgs[di]
        mcfg = all_model_cfgs[mi]

        if di not in dataset_cache:
            ds, feats = prepare_dataset(base_df, aux_frames, dcfg)
            if len(ds) < 1500:
                continue
            dataset_cache[di] = (ds, feats)
        ds, feats = dataset_cache[di]

        for th in fine_thresholds:
            done += 1
            m = _evaluate_experiment(ds, feats, mcfg, th, search_cfg, device, 0)
            rows_s3.append(
                {
                    "stage": "stage3",
                    "data_idx": di,
                    "model_idx": mi,
                    "threshold": th,
                    "n_rows": len(ds),
                    "n_features": len(feats),
                    "data_config": _to_json(asdict(dcfg)),
                    "model_config": _to_json(mcfg),
                    **m,
                }
            )
            if done % 50 == 0:
                print(f"Stage3 progress: {done}")

    s3 = pd.DataFrame(rows_s3)
    if s3.empty:
        raise RuntimeError("Stage3 produced no results")
    s3 = _rank_frame(s3, min_threshold=min_threshold, min_trades=min_trades, max_drawdown_cap=max_drawdown_cap)

    s3.to_csv(out_dir / "funnel_leaderboard.csv", index=False)
    top_pool = s3[s3["is_viable"]].copy()
    if top_pool.empty:
        top_pool = s3.copy()
    best = top_pool.iloc[0].to_dict()
    with open(out_dir / "funnel_best_config.json", "w", encoding="utf-8") as f:
        json.dump(best, f, indent=2)
    top_pool.head(shortlist_top_k).to_csv(out_dir / "funnel_shortlist_topk.csv", index=False)

    print("\n=== Funnel Top 20 ===")
    print(
        s3[
            [
                "objective_score",
                "robust_score",
                "is_viable",
                "strategy_factor",
                "market_factor",
                "hit_rate",
                "avg_trade_return",
                "max_drawdown",
                "total_trades",
                "threshold",
                "n_features",
            ]
        ].head(20)
    )

    return s3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Funnel BTC XGBoost strategy search")
    parser.add_argument("--download-data", action="store_true")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--months-back", type=int, default=120)
    parser.add_argument("--aux-intervals", default="4h,1d")
    parser.add_argument("--out-dir", default="data")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")

    parser.add_argument("--max-model-combos", type=int, default=128)

    parser.add_argument("--stage1-data", type=int, default=300)
    parser.add_argument("--stage1-models", type=int, default=24)
    parser.add_argument("--stage1-windows", type=int, default=2)

    parser.add_argument("--stage2-top-data", type=int, default=60)
    parser.add_argument("--stage2-top-models", type=int, default=16)
    parser.add_argument("--stage2-windows", type=int, default=4)

    parser.add_argument("--stage3-top-pairs", type=int, default=30)
    parser.add_argument("--min-threshold", type=float, default=0.55)
    parser.add_argument("--min-trades", type=int, default=800)
    parser.add_argument("--max-drawdown-cap", type=float, default=0.35)
    parser.add_argument("--shortlist-top-k", type=int, default=10)

    parser.add_argument("--fee", type=float, default=0.0004)
    parser.add_argument("--train-ratio", type=float, default=0.60)
    parser.add_argument("--test-ratio", type=float, default=0.10)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    aux_intervals = tuple(x.strip() for x in args.aux_intervals.split(",") if x.strip())

    search_cfg = SearchConfig(
        symbol=args.symbol,
        months_back=args.months_back,
        aux_intervals=aux_intervals,
        fee_per_trade=args.fee,
        train_ratio=args.train_ratio,
        test_ratio=args.test_ratio,
        random_state=args.seed,
    )

    run_funnel(
        search_cfg=search_cfg,
        out_dir=Path(args.out_dir),
        requested_device=args.device,
        force_download=args.download_data,
        max_model_combos=args.max_model_combos,
        stage1_data=args.stage1_data,
        stage1_models=args.stage1_models,
        stage1_windows=args.stage1_windows,
        stage2_top_data=args.stage2_top_data,
        stage2_top_models=args.stage2_top_models,
        stage2_windows=args.stage2_windows,
        stage3_top_pairs=args.stage3_top_pairs,
        min_threshold=args.min_threshold,
        min_trades=args.min_trades,
        max_drawdown_cap=args.max_drawdown_cap,
        shortlist_top_k=args.shortlist_top_k,
    )


if __name__ == "__main__":
    main()
