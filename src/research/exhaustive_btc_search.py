import argparse
import itertools
import json
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd
import xgboost as xgb
from xgboost import XGBClassifier

from src.download_binance import download_full_history


# Search spaces (can be overridden from CLI)
RET_WINDOW_SETS = [
    (1, 3, 6, 12, 24),
    (1, 2, 4, 8, 24),
    (1, 6, 12, 24, 48),
]

VOL_WINDOW_SETS = [
    (24, 72),
    (12, 48),
    (24, 48),
]

MA_WINDOW_SETS = [
    (12, 24, 72),
    (8, 24, 96),
    (6, 18, 72),
]

RSI_PERIODS = [7, 14, 21]
ATR_PERIODS = [7, 14, 21]

HORIZONS_H = [1, 3, 6]
TARGET_THRESHOLDS = [0.0025, 0.0040, 0.0060]
PROBA_THRESHOLDS = [0.52, 0.55, 0.58, 0.60, 0.62, 0.65]

MODEL_PARAM_GRID: Dict[str, Sequence] = {
    "n_estimators": [250, 450],
    "max_depth": [3, 5],
    "learning_rate": [0.03, 0.07],
    "subsample": [0.7, 1.0],
    "colsample_bytree": [0.7, 1.0],
    "min_child_weight": [1, 5],
    "gamma": [0.0, 0.2],
}

RESAMPLE_RULES = {
    "4h": ("4h", pd.Timedelta(hours=4)),
    "1d": ("1d", pd.Timedelta(days=1)),
}


@dataclass(frozen=True)
class DataConfig:
    ret_windows: Tuple[int, ...]
    vol_windows: Tuple[int, ...]
    ma_windows: Tuple[int, ...]
    rsi_period: int
    atr_period: int
    horizon_h: int
    target_threshold: float
    mtf_intervals: Tuple[str, ...]


@dataclass(frozen=True)
class SearchConfig:
    symbol: str = "BTCUSDT"
    months_back: int = 120
    base_interval: str = "1h"
    aux_intervals: Tuple[str, ...] = ("4h", "1d")
    fee_per_trade: float = 0.0004
    train_ratio: float = 0.60
    test_ratio: float = 0.10
    random_state: int = 42


def compute_rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_atr(df: pd.DataFrame, period: int) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - prev_close).abs()
    tr3 = (df["low"] - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return true_range.rolling(period).mean()


def powerset(items: Sequence[str]) -> List[Tuple[str, ...]]:
    out: List[Tuple[str, ...]] = []
    for k in range(len(items) + 1):
        out.extend(itertools.combinations(items, k))
    return out


def generate_data_configs(aux_intervals: Tuple[str, ...]) -> List[DataConfig]:
    interval_sets = powerset(aux_intervals)
    configs: List[DataConfig] = []

    for ret_w, vol_w, ma_w, rsi_p, atr_p, horizon, thr, mtf in itertools.product(
        RET_WINDOW_SETS,
        VOL_WINDOW_SETS,
        MA_WINDOW_SETS,
        RSI_PERIODS,
        ATR_PERIODS,
        HORIZONS_H,
        TARGET_THRESHOLDS,
        interval_sets,
    ):
        configs.append(
            DataConfig(
                ret_windows=tuple(ret_w),
                vol_windows=tuple(vol_w),
                ma_windows=tuple(ma_w),
                rsi_period=int(rsi_p),
                atr_period=int(atr_p),
                horizon_h=int(horizon),
                target_threshold=float(thr),
                mtf_intervals=tuple(mtf),
            )
        )

    return configs


def generate_model_configs(max_model_combos: int = 0) -> List[Dict[str, float]]:
    keys = list(MODEL_PARAM_GRID.keys())
    values = [MODEL_PARAM_GRID[k] for k in keys]

    rows: List[Dict[str, float]] = []
    for combo in itertools.product(*values):
        rows.append(dict(zip(keys, combo)))

    if max_model_combos and max_model_combos > 0:
        return rows[:max_model_combos]
    return rows


def resample_from_1h(df_1h: pd.DataFrame, interval: str) -> pd.DataFrame:
    if interval not in RESAMPLE_RULES:
        raise ValueError(f"Unsupported synthetic interval: {interval}")

    rule, delta = RESAMPLE_RULES[interval]
    frame = df_1h.copy().sort_values("open_time").set_index("open_time")

    agg = frame.resample(rule).agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
    )
    agg = agg.dropna().reset_index()
    agg["close_time"] = agg["open_time"] + delta - pd.to_timedelta(1, unit="ms")
    return agg[["open_time", "open", "high", "low", "close", "volume", "close_time"]]


def ensure_data(search_cfg: SearchConfig, out_dir: Path, force_download: bool = False) -> Dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)

    intervals = [search_cfg.base_interval, *search_cfg.aux_intervals]
    paths = {interval: out_dir / f"{search_cfg.symbol.lower()}_{interval}.csv" for interval in intervals}

    base_path = paths[search_cfg.base_interval]
    if force_download or not base_path.exists():
        try:
            df = download_full_history(
                symbol=search_cfg.symbol,
                interval=search_cfg.base_interval,
                months_back=search_cfg.months_back,
            )
            df.to_csv(base_path, index=False)
            print(f"Downloaded {len(df)} rows -> {base_path}")
        except Exception:
            if base_path.exists():
                print(f"Download failed, fallback to local file -> {base_path}")
            else:
                raise
    else:
        print(f"Using local file -> {base_path}")

    base_df_for_resample = load_ohlcv(base_path)

    for interval in search_cfg.aux_intervals:
        path = paths[interval]
        if not force_download and path.exists():
            print(f"Using local file -> {path}")
            continue

        try:
            df = download_full_history(
                symbol=search_cfg.symbol,
                interval=interval,
                months_back=search_cfg.months_back,
            )
            df.to_csv(path, index=False)
            print(f"Downloaded {len(df)} rows -> {path}")
        except Exception:
            synthetic = resample_from_1h(base_df_for_resample, interval=interval)
            synthetic.to_csv(path, index=False)
            print(f"Synthesized {len(synthetic)} rows from 1h -> {path}")

    return paths


def load_ohlcv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["open_time", "close_time"])
    return df.sort_values("open_time").reset_index(drop=True)


def build_base_features(df: pd.DataFrame, cfg: DataConfig) -> Tuple[pd.DataFrame, List[str]]:
    out = df.copy().sort_values("open_time").reset_index(drop=True)

    feature_cols: List[str] = []

    # Momentum
    for w in cfg.ret_windows:
        col = f"ret_{w}"
        out[col] = out["close"].pct_change(w)
        feature_cols.append(col)

    # Candle structure
    out["hl_range"] = (out["high"] - out["low"]) / out["close"]
    out["oc_change"] = (out["close"] - out["open"]) / out["open"]
    out["upper_wick"] = (out["high"] - out[["open", "close"]].max(axis=1)) / out["close"]
    out["lower_wick"] = (out[["open", "close"]].min(axis=1) - out["low"]) / out["close"]
    feature_cols.extend(["hl_range", "oc_change", "upper_wick", "lower_wick"])

    # Volume and volatility
    for w in cfg.vol_windows:
        vmean = f"vol_mean_{w}"
        vratio = f"vol_ratio_{w}"
        volat = f"volatility_{w}"

        out[vmean] = out["volume"].rolling(w).mean()
        out[vratio] = out["volume"] / out[vmean]
        out[volat] = out["ret_1"].rolling(w).std() if "ret_1" in out.columns else out["close"].pct_change().rolling(w).std()

        feature_cols.extend([vratio, volat])

    # Trend
    for w in cfg.ma_windows:
        ma = f"ma_{w}"
        dist = f"dist_ma_{w}"
        out[ma] = out["close"].rolling(w).mean()
        out[dist] = (out["close"] / out[ma]) - 1
        feature_cols.append(dist)

    # Oscillators
    rsi_col = f"rsi_{cfg.rsi_period}"
    atr_col = f"atr_{cfg.atr_period}"
    atr_pct_col = f"atr_pct_{cfg.atr_period}"

    out[rsi_col] = compute_rsi(out["close"], cfg.rsi_period)
    out[atr_col] = compute_atr(out, cfg.atr_period)
    out[atr_pct_col] = out[atr_col] / out["close"]
    feature_cols.extend([rsi_col, atr_pct_col])

    # Calendar
    out["hour_of_day"] = out["open_time"].dt.hour
    out["day_of_week"] = out["open_time"].dt.dayofweek
    out["is_weekend"] = (out["day_of_week"] >= 5).astype(int)
    feature_cols.extend(["hour_of_day", "day_of_week", "is_weekend"])

    # Label
    horizon = cfg.horizon_h
    target_name = f"future_return_{horizon}h"
    out[target_name] = (out["close"].shift(-horizon) / out["close"]) - 1

    thr = cfg.target_threshold
    # Realistic binary labeling for long-only strategy:
    # keep every timestamp to avoid look-ahead selection bias.
    out["target"] = (out[target_name] > thr).astype(int)
    out["future_return"] = out[target_name]

    out = out.replace([np.inf, -np.inf], np.nan)

    return out, feature_cols


def merge_mtf_features(
    base_df: pd.DataFrame,
    aux_frames: Dict[str, pd.DataFrame],
    cfg: DataConfig,
    feature_cols: List[str],
) -> Tuple[pd.DataFrame, List[str]]:
    out = base_df.copy()

    for interval in cfg.mtf_intervals:
        aux = aux_frames[interval].copy().sort_values("open_time").reset_index(drop=True)

        r1 = f"{interval}_ret_1"
        r3 = f"{interval}_ret_3"
        rsi = f"{interval}_rsi_{cfg.rsi_period}"

        aux[r1] = aux["close"].pct_change(1)
        aux[r3] = aux["close"].pct_change(3)
        aux[rsi] = compute_rsi(aux["close"], cfg.rsi_period)

        keep = ["open_time", r1, r3, rsi]
        out = pd.merge_asof(
            out.sort_values("open_time"),
            aux[keep].sort_values("open_time"),
            on="open_time",
            direction="backward",
        )

        feature_cols.extend([r1, r3, rsi])

    return out, feature_cols


def prepare_dataset(base_df: pd.DataFrame, aux_frames: Dict[str, pd.DataFrame], cfg: DataConfig) -> Tuple[pd.DataFrame, List[str]]:
    df, feature_cols = build_base_features(base_df, cfg)
    df, feature_cols = merge_mtf_features(df, aux_frames, cfg, feature_cols)

    needed = [*feature_cols, "future_return", "open_time"]
    df = df.dropna(subset=needed).reset_index(drop=True)

    return df, feature_cols


def max_drawdown(equity_curve: pd.Series) -> float:
    roll_max = equity_curve.cummax()
    drawdown = (equity_curve / roll_max) - 1.0
    return float(drawdown.min())


def evaluate_walk_forward(
    df: pd.DataFrame,
    features: List[str],
    model_params: Dict[str, float],
    proba_threshold: float,
    device: str,
    fee_per_trade: float,
    train_ratio: float,
    test_ratio: float,
    random_state: int,
    max_windows: int = 0,
) -> Dict[str, float]:
    data = df.sort_values("open_time").reset_index(drop=True)
    n = len(data)

    train_size = int(n * train_ratio)
    test_size = int(n * test_ratio)
    step = test_size

    if train_size <= 0 or test_size <= 0 or train_size + test_size > n:
        return {
            "nb_windows": 0,
            "total_trades": 0,
            "hit_rate": 0.0,
            "avg_trade_return": 0.0,
            "strategy_factor": 1.0,
            "market_factor": 1.0,
            "max_drawdown": 0.0,
            "objective_score": -999.0,
        }

    all_net_returns: List[float] = []
    all_market_returns: List[float] = []
    all_targets: List[int] = []
    all_trade_flags: List[int] = []

    start_test = train_size
    windows = 0

    while start_test + test_size <= n:
        train_df = data.iloc[:start_test]
        test_df = data.iloc[start_test : start_test + test_size]

        model = XGBClassifier(
            objective="binary:logistic",
            eval_metric="logloss",
            tree_method="hist",
            device=device,
            random_state=random_state,
            **model_params,
        )
        model.fit(train_df[features], train_df["target"].astype(int), verbose=False)

        proba = model.predict_proba(test_df[features])[:, 1]
        trade = (proba >= proba_threshold).astype(int)

        gross = np.where(trade == 1, test_df["future_return"].to_numpy(), 0.0)
        net = np.where(trade == 1, test_df["future_return"].to_numpy() - fee_per_trade, 0.0)

        all_net_returns.extend(net.tolist())
        all_market_returns.extend(test_df["future_return"].to_numpy().tolist())
        all_targets.extend(test_df["target"].astype(int).tolist())
        all_trade_flags.extend(trade.tolist())

        start_test += step
        windows += 1
        if max_windows and windows >= max_windows:
            break

    if windows == 0:
        return {
            "nb_windows": 0,
            "total_trades": 0,
            "hit_rate": 0.0,
            "avg_trade_return": 0.0,
            "strategy_factor": 1.0,
            "market_factor": 1.0,
            "max_drawdown": 0.0,
            "objective_score": -999.0,
        }

    net_series = pd.Series(all_net_returns)
    market_series = pd.Series(all_market_returns)
    trade_series = pd.Series(all_trade_flags)
    target_series = pd.Series(all_targets)

    strategy_equity = (1.0 + net_series).cumprod()
    market_equity = (1.0 + market_series).cumprod()

    total_trades = int(trade_series.sum())
    if total_trades > 0:
        hit_rate = float((target_series[trade_series == 1] == 1).mean())
        avg_trade_return = float(net_series[trade_series == 1].mean())
    else:
        hit_rate = 0.0
        avg_trade_return = 0.0

    strategy_factor = float(strategy_equity.iloc[-1]) if len(strategy_equity) > 0 else 1.0
    market_factor = float(market_equity.iloc[-1]) if len(market_equity) > 0 else 1.0
    mdd = abs(max_drawdown(strategy_equity)) if len(strategy_equity) > 0 else 0.0

    low_trade_penalty = -0.15 if total_trades < 50 else 0.0
    objective_score = (
        np.log(max(strategy_factor, 1e-9))
        + 0.8 * (hit_rate - 0.5)
        + 8.0 * avg_trade_return
        - 0.5 * mdd
        + low_trade_penalty
    )

    return {
        "nb_windows": windows,
        "total_trades": total_trades,
        "hit_rate": hit_rate,
        "avg_trade_return": avg_trade_return,
        "strategy_factor": strategy_factor,
        "market_factor": market_factor,
        "max_drawdown": mdd,
        "objective_score": float(objective_score),
    }


def resolve_device(requested_device: str) -> str:
    has_cuda = bool(xgb.build_info().get("USE_CUDA", False))

    if requested_device == "cpu":
        return "cpu"
    if requested_device == "cuda":
        if has_cuda:
            return "cuda"
        warnings.warn("CUDA demandé mais indisponible dans la build XGBoost: fallback vers CPU.")
        return "cpu"

    # requested_device == "auto": prefer CUDA, fallback CPU.
    if has_cuda:
        return "cuda"
    warnings.warn("CUDA indisponible: fallback vers CPU.")
    return "cpu"


def run_search(
    search_cfg: SearchConfig,
    out_dir: Path,
    force_download: bool,
    max_data_configs: int,
    max_model_combos: int,
    max_experiments: int,
    checkpoint_every: int,
    requested_device: str,
    resume_path: Path = None,
) -> pd.DataFrame:
    data_paths = ensure_data(search_cfg, out_dir=out_dir, force_download=force_download)

    base_df = load_ohlcv(data_paths[search_cfg.base_interval])
    aux_frames = {interval: load_ohlcv(path) for interval, path in data_paths.items() if interval != search_cfg.base_interval}

    data_configs = generate_data_configs(search_cfg.aux_intervals)
    model_configs = generate_model_configs(max_model_combos=max_model_combos)
    selected_device = resolve_device(requested_device)

    if max_data_configs and max_data_configs > 0:
        data_configs = data_configs[:max_data_configs]

    total_experiments = len(data_configs) * len(model_configs) * len(PROBA_THRESHOLDS)
    print(f"Data configs: {len(data_configs)}")
    print(f"Model configs: {len(model_configs)}")
    print(f"Signal thresholds: {len(PROBA_THRESHOLDS)}")
    print(f"XGBoost device: {selected_device}")
    print(f"Planned experiments: {total_experiments}")

    rows = []
    seen_keys = set()
    if resume_path is not None and resume_path.exists():
        prev = pd.read_csv(resume_path)
        rows = prev.to_dict("records")
        if "experiment_key" in prev.columns:
            seen_keys = set(prev["experiment_key"].astype(str).tolist())
        print(f"Resuming from {resume_path} with {len(rows)} existing rows")

    done = 0

    for d_idx, data_cfg in enumerate(data_configs, start=1):
        dataset, feature_cols = prepare_dataset(base_df, aux_frames, data_cfg)

        if len(dataset) < 1500:
            continue

        for model_cfg in model_configs:
            for proba_threshold in PROBA_THRESHOLDS:
                exp_key = json.dumps(
                    {
                        "data_config": asdict(data_cfg),
                        "model_config": model_cfg,
                        "proba_threshold": proba_threshold,
                    },
                    sort_keys=True,
                )
                if exp_key in seen_keys:
                    continue

                done += 1
                if max_experiments and max_experiments > 0 and done > max_experiments:
                    break

                metrics = evaluate_walk_forward(
                    df=dataset,
                    features=feature_cols,
                    model_params=model_cfg,
                    proba_threshold=proba_threshold,
                    device=selected_device,
                    fee_per_trade=search_cfg.fee_per_trade,
                    train_ratio=search_cfg.train_ratio,
                    test_ratio=search_cfg.test_ratio,
                    random_state=search_cfg.random_state,
                )

                rows.append(
                    {
                        "experiment_id": done,
                        "n_rows": len(dataset),
                        "n_features": len(feature_cols),
                        "device_used": selected_device,
                        "proba_threshold": proba_threshold,
                        "experiment_key": exp_key,
                        "data_config": json.dumps(asdict(data_cfg), sort_keys=True),
                        "model_config": json.dumps(model_cfg, sort_keys=True),
                        **metrics,
                    }
                )
                seen_keys.add(exp_key)

                if done % 50 == 0:
                    print(f"Progress: {done} experiments done (data cfg {d_idx}/{len(data_configs)})")
                if checkpoint_every > 0 and done % checkpoint_every == 0:
                    pd.DataFrame(rows).to_csv(out_dir / "exhaustive_search_checkpoint.csv", index=False)
                    print(f"Checkpoint saved at {done} experiments")

            if max_experiments and max_experiments > 0 and done > max_experiments:
                break

        if max_experiments and max_experiments > 0 and done > max_experiments:
            break

    if not rows:
        return pd.DataFrame()

    leaderboard = pd.DataFrame(rows).sort_values(
        ["objective_score", "strategy_factor", "avg_trade_return", "hit_rate"],
        ascending=False,
    )

    return leaderboard


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Exhaustive BTC XGBoost strategy search")
    parser.add_argument("--download-data", action="store_true", help="Force download fresh Binance data")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--months-back", type=int, default=120)
    parser.add_argument("--aux-intervals", default="4h,1d", help="Comma-separated, ex: 4h,1d")
    parser.add_argument("--out-dir", default="data")
    parser.add_argument("--max-data-configs", type=int, default=0, help="0 means exhaustive")
    parser.add_argument("--max-model-combos", type=int, default=0, help="0 means exhaustive")
    parser.add_argument("--max-experiments", type=int, default=0, help="0 means exhaustive")
    parser.add_argument("--fee", type=float, default=0.0004)
    parser.add_argument("--train-ratio", type=float, default=0.60)
    parser.add_argument("--test-ratio", type=float, default=0.10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--checkpoint-every", type=int, default=100)
    parser.add_argument("--resume-path", default="", help="Path to existing checkpoint/leaderboard CSV")
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

    out_dir = Path(args.out_dir)
    resume_path = Path(args.resume_path) if args.resume_path else None
    leaderboard = run_search(
        search_cfg=search_cfg,
        out_dir=out_dir,
        force_download=args.download_data,
        max_data_configs=args.max_data_configs,
        max_model_combos=args.max_model_combos,
        max_experiments=args.max_experiments,
        checkpoint_every=args.checkpoint_every,
        requested_device=args.device,
        resume_path=resume_path,
    )

    if leaderboard.empty:
        print("No results generated. Try relaxing dataset constraints.")
        return

    leaderboard_path = out_dir / "exhaustive_search_leaderboard.csv"
    top1_path = out_dir / "exhaustive_search_best_config.json"

    leaderboard.to_csv(leaderboard_path, index=False)
    best_row = leaderboard.iloc[0].to_dict()

    with open(top1_path, "w", encoding="utf-8") as f:
        json.dump(best_row, f, indent=2)

    print("\n=== TOP 20 STRATEGIES ===")
    print(
        leaderboard[
            [
                "experiment_id",
                "objective_score",
                "strategy_factor",
                "market_factor",
                "hit_rate",
                "avg_trade_return",
                "total_trades",
                "n_rows",
                "n_features",
                "proba_threshold",
            ]
        ].head(20)
    )
    print(f"\nSaved: {leaderboard_path}")
    print(f"Saved: {top1_path}")


if __name__ == "__main__":
    main()
