from dataclasses import dataclass
from itertools import combinations, product
from typing import Dict, Iterable, List

FEATURE_GROUPS: Dict[str, List[str]] = {
    "momentum": ["ret_1", "ret_3", "ret_6", "ret_12", "ret_24"],
    "candle": ["hl_range", "oc_change", "upper_wick", "lower_wick"],
    "volume": ["vol_ratio_24"],
    "volatility": ["volatility_24", "volatility_72"],
    "trend": ["dist_ma_12", "dist_ma_24", "dist_ma_72"],
    "indicators": ["rsi_14", "atr_pct_14"],
    "calendar": ["hour_of_day", "day_of_week"],
}

THRESHOLDS = [0.55, 0.58, 0.60, 0.62, 0.65]

XGB_PARAM_GRID = {
    "n_estimators": [200, 300, 500],
    "max_depth": [3, 4, 5],
    "learning_rate": [0.03, 0.05, 0.08],
    "subsample": [0.7, 0.8, 1.0],
    "colsample_bytree": [0.7, 0.8, 1.0],
    "min_child_weight": [1, 3, 5],
}


@dataclass(frozen=True)
class ExperimentConfig:
    feature_groups: tuple
    features: tuple
    xgb_params: Dict[str, float]
    threshold: float


def _flatten_feature_groups(groups: Iterable[str]) -> List[str]:
    cols: List[str] = []
    for name in groups:
        cols.extend(FEATURE_GROUPS[name])
    return cols


def generate_feature_sets(min_groups: int = 3, max_groups: int = 6) -> List[tuple]:
    group_names = sorted(FEATURE_GROUPS.keys())
    all_sets = []

    for size in range(min_groups, max_groups + 1):
        for subset in combinations(group_names, size):
            # force un signal directionnel minimal
            if "momentum" not in subset:
                continue
            all_sets.append(subset)

    return all_sets


def generate_model_params(max_combinations: int = 80) -> List[Dict[str, float]]:
    keys = list(XGB_PARAM_GRID.keys())
    values = [XGB_PARAM_GRID[k] for k in keys]

    params = []
    for combo in product(*values):
        params.append(dict(zip(keys, combo)))
        if len(params) >= max_combinations:
            break

    return params


def generate_experiments(
    min_groups: int = 3,
    max_groups: int = 6,
    max_param_combinations: int = 80,
) -> List[ExperimentConfig]:
    feature_sets = generate_feature_sets(min_groups=min_groups, max_groups=max_groups)
    param_sets = generate_model_params(max_combinations=max_param_combinations)

    experiments: List[ExperimentConfig] = []
    for group_subset in feature_sets:
        features = tuple(_flatten_feature_groups(group_subset))
        for params in param_sets:
            for threshold in THRESHOLDS:
                experiments.append(
                    ExperimentConfig(
                        feature_groups=group_subset,
                        features=features,
                        xgb_params=params,
                        threshold=threshold,
                    )
                )

    return experiments
