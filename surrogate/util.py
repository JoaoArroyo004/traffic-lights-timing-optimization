import numpy as np
import pandas as pd


def infer_xy_columns(df: pd.DataFrame):
    x_cols = sorted([c for c in df.columns if c.startswith("x") and c[1:].isdigit()],
                    key=lambda s: int(s[1:]))
    y_cols = sorted([c for c in df.columns if c.startswith("f") and c[1:].isdigit()],
                    key=lambda s: int(s[1:]))

    if len(x_cols) == 0 or len(y_cols) == 0:
        raise ValueError(
            "Não encontrei colunas no padrão x1..xN e f1..fM. "
            "Confere os nomes no df_data."
        )
    return x_cols, y_cols



def get_Xy(df: pd.DataFrame):
    x_cols, y_cols = infer_xy_columns(df)
    X = df[x_cols].to_numpy(dtype=np.float32)
    y = df[y_cols].to_numpy(dtype=np.float32)
    return X, y, x_cols, y_cols
