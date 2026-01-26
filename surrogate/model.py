import joblib
import numpy as np
from pymoo.core.problem import Problem


def load_surrogate(joblib_path: str):
    bundle = joblib.load(joblib_path)
    model = bundle["model"]          # Pipeline(scaler + MultiOutputRegressor)
    x_cols = bundle.get("x_cols")    # opcional (só metadado)
    y_cols = bundle.get("y_cols")    # opcional (só metadado)
    return model, x_cols, y_cols


class SurrogateProblem(Problem):
    def __init__(self, surrogate_model, n_var, n_obj, xl=None, xu=None):
        super().__init__(
            n_var=n_var,
            n_obj=n_obj,
            n_constr=0,
            xl=xl,
            xu=xu
        )
        self.surrogate = surrogate_model

    def _evaluate(self, X, out, *args, **kwargs):
        X = np.asarray(X, dtype=np.float32)
        F = self.surrogate.predict(X)
        F = np.asarray(F, dtype=np.float64)
        out["F"] = F


def load_problem():
    model, x_cols, y_cols = load_surrogate("models/GBR.joblib")
    n_var = len(x_cols)
    n_obj = len(y_cols)
    xl = np.zeros(n_var)          
    xu = np.ones(n_var) * 1.0
    return SurrogateProblem(model, n_var=n_var, n_obj=n_obj, xl=xl, xu=xu)


problem = load_problem()
