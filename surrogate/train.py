import os

import joblib
import numpy as np
import pandas as pd
from build import build_candidates, build_gbr_model
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import (KFold, RandomizedSearchCV, RepeatedKFold,
                                     train_test_split)
from util import get_Xy, infer_xy_columns


def compute_multi_metrics(y_true, y_pred):
    # y_true/y_pred: [N, T]
    T = y_true.shape[1]
    mse = np.array([mean_squared_error(y_true[:, t], y_pred[:, t]) for t in range(T)], dtype=float)
    mae = np.array([mean_absolute_error(y_true[:, t], y_pred[:, t]) for t in range(T)], dtype=float)
    r2  = np.array([r2_score(y_true[:, t], y_pred[:, t]) for t in range(T)], dtype=float)

    return {
        "MSE_per_obj": mse,
        "MAE_per_obj": mae,
        "R2_per_obj": r2,
        "MSE_mean": float(mse.mean()),
        "MAE_mean": float(mae.mean()),
        "R2_mean":  float(r2.mean()),
    }

def nested_tune_and_evaluate(
    X, y, y_cols,
    candidates,
    outer_splits=5, outer_repeats=3,
    inner_splits=4,
    n_iter=30,
    random_state=42,
    n_jobs=-1,
    verbose=1
):
    outer_cv = RepeatedKFold(
        n_splits=outer_splits,
        n_repeats=outer_repeats,
        random_state=random_state
    )
    inner_cv = KFold(n_splits=inner_splits, shuffle=True, random_state=random_state)

    all_results = {}
    best_params_summary = {}

    for name, spec in candidates.items():
        print(f"\n=== {name}: nested CV tuning + evaluation ===")

        fold_rows = []
        best_params_each_outer = []

        for fold_id, (tr_idx, te_idx) in enumerate(outer_cv.split(X), start=1):
            Xtr, Xte = X[tr_idx], X[te_idx]
            ytr, yte = y[tr_idx], y[te_idx]

            search = RandomizedSearchCV(
                estimator=spec["estimator"],
                param_distributions=spec["param_distributions"],
                n_iter=n_iter,
                scoring="r2",              
                cv=inner_cv,
                random_state=random_state,
                n_jobs=n_jobs,
                verbose=0
            )

            search.fit(Xtr, ytr)
            best_model = search.best_estimator_
            best_params_each_outer.append(search.best_params_)

            yhat = best_model.predict(Xte)
            m = compute_multi_metrics(yte, yhat)

            row = {
                "outer_fold": fold_id,
                "MSE_mean": m["MSE_mean"],
                "MAE_mean": m["MAE_mean"],
                "R2_mean":  m["R2_mean"],
            }

            for t, col in enumerate(y_cols):
                row[f"MSE_{col}"] = float(m["MSE_per_obj"][t])
                row[f"MAE_{col}"] = float(m["MAE_per_obj"][t])
                row[f"R2_{col}"]  = float(m["R2_per_obj"][t])

            fold_rows.append(row)

            if verbose:
                print(f"  fold {fold_id:02d}: R2_mean={row['R2_mean']:.4f}  MSE_mean={row['MSE_mean']:.4e}")

        df_folds = pd.DataFrame(fold_rows)

        metrics_cols = [c for c in df_folds.columns if c != "outer_fold"]
        agg = df_folds[metrics_cols].agg(["mean", "std"]).T.reset_index()
        agg.columns = ["metric", "mean", "std"]
        agg.insert(0, "model", name)

        all_results[name] = {
            "folds": df_folds,
            "summary": agg.sort_values("metric"),
            "best_params_outer": best_params_each_outer,
        }

        params_series = pd.Series([str(p) for p in best_params_each_outer])
        mode_str = params_series.mode().iloc[0]
        best_params_summary[name] = mode_str

    # junta sumários
    summary_all = pd.concat([all_results[k]["summary"] for k in all_results.keys()], ignore_index=True)

    return all_results, best_params_summary, summary_all


def train_and_save(
    df_data,
    model_builder,
    best_params,
    model_name,
    random_state,
    out_dir="models"
):
    
    os.makedirs(out_dir, exist_ok=True)

    X, y, x_cols, y_cols = get_Xy(df_data)

    model = model_builder(best_params, random_state=random_state)

    model.fit(X, y)

    # metadados
    bundle = {
        "model": model,
        "x_cols": x_cols,
        "y_cols": y_cols,
        "best_params": best_params,
        "random_state": random_state,
    }

    path = f"{out_dir}/{model_name}.joblib"
    joblib.dump(bundle, path)

    print(f"✔ Model saved in: {path}")
    return path


def tune_and_train(df_data, random_state, outer_splits=5,
        outer_repeats=3,
        inner_splits=4,
        n_iter=30):
    
    X, y, x_cols, y_cols = get_Xy(df_data)
    candidates = build_candidates(random_state=random_state)

    all_results, best_params_summary, summary_all = nested_tune_and_evaluate(
        X, y, y_cols,
        candidates=candidates,
        outer_splits=outer_splits,
        outer_repeats=outer_repeats,
        inner_splits=inner_splits,
        n_iter=n_iter,
        random_state=random_state,
        n_jobs=-1,
        verbose=1
    )

    print("\n\n===== Melhores parâmetros (representativos; modo no outer CV) =====")
    for k, v in best_params_summary.items():
        print(f"{k}: {v}")

    print("\n\n===== Comparação (média ± std) =====")
    # Mostra só as métricas médias globais primeiro
    mask_main = summary_all["metric"].isin(["MSE_mean", "MAE_mean", "R2_mean"])
    print(summary_all[mask_main].sort_values(["metric", "mean"]))
    return all_results



df_data = pd.read_csv("data.csv")
test_size = 0.3
random_state = None
all_results = tune_and_train(df_data, random_state=random_state, outer_splits=2, outer_repeats=2, inner_splits=2, n_iter=10)
X, y, x_cols, y_cols = get_Xy(df_data)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=test_size, random_state=random_state
)
for model_name, spec in all_results.items():
    train_and_save(
        df_data=df_data,
        model_builder=build_gbr_model,
        best_params=spec,
        model_name=model_name,
        random_state=random_state,
    )