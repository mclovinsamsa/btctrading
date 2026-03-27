import pandas as pd
import numpy as np

DATA_PATH = "data/test_predictions.csv"

def run_backtest(df, threshold=0.55, fee_per_trade=0.0004):
    bt = df.copy()

    bt["trade"] = (bt["proba_up"] >= threshold).astype(int)
    bt["gross_return"] = np.where(bt["trade"] == 1, bt["future_return_3h"], 0.0)
    bt["cost"] = np.where(bt["trade"] == 1, fee_per_trade, 0.0)
    bt["net_return"] = bt["gross_return"] - bt["cost"]

    bt["cum_strategy"] = (1 + bt["net_return"]).cumprod()
    bt["cum_market"] = (1 + bt["future_return_3h"]).cumprod()

    trades = bt[bt["trade"] == 1].copy()

    nb_trades = len(trades)
    hit_rate = (trades["target"] == 1).mean() if nb_trades > 0 else 0.0
    avg_gross = trades["future_return_3h"].mean() if nb_trades > 0 else 0.0
    avg_net = trades["net_return"].mean() if nb_trades > 0 else 0.0
    final_factor = bt["cum_strategy"].iloc[-1]
    market_factor = bt["cum_market"].iloc[-1]

    return {
        "threshold": threshold,
        "nb_trades": nb_trades,
        "hit_rate": hit_rate,
        "avg_gross_return": avg_gross,
        "avg_net_return": avg_net,
        "strategy_factor": final_factor,
        "market_factor": market_factor,
    }

def main():
    df = pd.read_csv(DATA_PATH, parse_dates=["open_time"])

    print("=== Backtest avec frais ===")
    print("Hypothèse de frais par trade: 0.0004 (0.04%)\n")

    thresholds = [0.50, 0.55, 0.60, 0.65]

    for th in thresholds:
        res = run_backtest(df, threshold=th, fee_per_trade=0.0004)

        print(f"Seuil {res['threshold']}")
        print(f"  nb_trades       : {res['nb_trades']}")
        print(f"  hit_rate        : {res['hit_rate']:.4f}")
        print(f"  avg_gross_return: {res['avg_gross_return']:.5f}")
        print(f"  avg_net_return  : {res['avg_net_return']:.5f}")
        print(f"  strategy_factor : {res['strategy_factor']:.4f}")
        print(f"  market_factor   : {res['market_factor']:.4f}")
        print()

if __name__ == "__main__":
    main()