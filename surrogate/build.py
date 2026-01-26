from sklearn.ensemble import (GradientBoostingRegressor,
                              HistGradientBoostingRegressor)
from sklearn.multioutput import MultiOutputRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def build_gbr_model(best_params, random_state):
    """
    best_params: dict com chaves no padrão
      model__estimator__<param>
    """
    # remove prefixo do pipeline
    gbr_params = {
        k.replace("model__estimator__", ""): v
        for k, v in best_params.items()
        if k.startswith("model__estimator__")
    }

    gbr = GradientBoostingRegressor(
        random_state=random_state,
        **gbr_params
    )

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("model", MultiOutputRegressor(gbr))
    ])

    return model


def build_hgb_model(best_params, random_state):
    """
    best_params: dict com chaves no padrão
      model__estimator__<param>
    """
    hgb_params = {
        k.replace("model__estimator__", ""): v
        for k, v in best_params.items()
        if k.startswith("model__estimator__")
    }

    hgb = HistGradientBoostingRegressor(
        random_state=random_state,
        **hgb_params
    )

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("model", MultiOutputRegressor(hgb))
    ])

    return model


def build_candidates(random_state):
    base_gbr = build_gbr_model({}, random_state=random_state)
    base_hgb = build_hgb_model({}, random_state=random_state)

    search_spaces = {
        "GBR": {
            "estimator": base_gbr,
            "param_distributions": {
                "model__estimator__n_estimators":     [200, 400, 700, 1000],
                "model__estimator__learning_rate":    [0.01, 0.03, 0.05, 0.1],
                "model__estimator__max_depth":        [2, 3, 4],
                "model__estimator__min_samples_leaf": [1, 3, 5, 10],
                "model__estimator__subsample":        [0.6, 0.7, 0.8, 1.0],
                "model__estimator__max_features":     [None, "sqrt"],
                "model__estimator__loss":             ["squared_error", "absolute_error"],
            }
        },
    }
    return search_spaces
