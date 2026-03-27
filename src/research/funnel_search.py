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


def _evaluate_experiment(
    dataset: pd.DataFrame,
    features: List[str],
    model_cfg: Dict,
    proba_threshold: float,
    search_cfg: SearchConfig,
    device: str,
    max_windows: int,
) -> Dict:
    metrics = evaluate_walk_forward(
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
    return metrics


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

    # Stage 1: coarse sampling + few windows
    data_idx_s1 = _pick_indices(len(all_data_cfgs), stage1_data, search_cfg.random_state)
    model_idx_s1 = _pick_indices(len(all_model_cfgs), stage1_models, search_cfg.random_state + 1)
    thresholds_s1 = sorted(set([0.52, 0.58, 0.64]).intersection(set(PROBA_THRESHOLDS)))
    if not thresholds_s1:
        thresholds_s1 = [PROBA_THRESHOLDS[0]]

    print(
        f"Stage1 => data:{len(data_idx_s1)} x model:{len(model_idx_s1)} x th:{len(thresholds_s1)}"
    )

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
                m = _evaluate_experiment(
                    dataset=ds,
                    features=feats,
                    model_cfg=mcfg,
                    proba_threshold=th,
                    search_cfg=search_cfg,
                    device=device,
                    max_windows=stage1_windows,
                )
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

    s1.to_csv(out_dir / "funnel_stage1.csv", index=False)

    top_data = (
        s1.groupby("data_idx", as_index=False)["objective_score"].max()
        .sort_values("objective_score", ascending=False)
        .head(stage2_top_data)["data_idx"]
        .tolist()
    )
    top_models = (
        s1.groupby("model_idx", as_index=False)["objective_score"].max()
        .sort_values("objective_score", ascending=False)
        .head(stage2_top_models)["model_idx"]
        .tolist()
    )

    # Stage 2: focus on promising regions, medium windows
    print(f"Stage2 => data:{len(top_data)} x model:{len(top_models)} x th:{len(PROBA_THRESHOLDS)}")
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
            for th in PROBA_THRESHOLDS:
                done += 1
                m = _evaluate_experiment(
                    dataset=ds,
                    features=feats,
                    model_cfg=mcfg,
                    proba_threshold=th,
                    search_cfg=search_cfg,
                    device=device,
                    max_windows=stage2_windows,
                )
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
    s2.to_csv(out_dir / "funnel_stage2.csv", index=False)

    # Stage 3: full validation on finalists + finer threshold search
    finalists = (
        s2.sort_values("objective_score", ascending=False)
        .head(stage3_top_pairs)[["data_idx", "model_idx"]]
        .drop_duplicates()
        .to_dict("records")
    )
    fine_thresholds = [round(x, 2) for x in np.arange(0.50, 0.701, 0.01)]

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
            m = _evaluate_experiment(
                dataset=ds,
                features=feats,
                model_cfg=mcfg,
                proba_threshold=th,
                search_cfg=search_cfg,
                device=device,
                max_windows=0,
            )
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

    s3 = s3.sort_values(
        ["objective_score", "strategy_factor", "avg_trade_return", "hit_rate"],
        ascending=False,
    )

    s3.to_csv(out_dir / "funnel_leaderboard.csv", index=False)
    best = s3.iloc[0].to_dict()
    with open(out_dir / "funnel_best_config.json", "w", encoding="utf-8") as f:
        json.dump(best, f, indent=2)

    print("\n=== Funnel Top 20 ===")
    print(
        s3[
            [
                "objective_score",
                "strategy_factor",
                "market_factor",
                "hit_rate",
                "avg_trade_return",
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
    )


if __name__ == "__main__":
    main()
