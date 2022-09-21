import numpy as np
import pandas as pd


def calc_portfolio_positions(df):
    df = df.copy()
    symbol_cols = [x for x in df.columns if x.startswith("p.")]
    for col in df.columns:
        if col.startswith("w."):
            model_id = col.replace("w.", "")

            df2 = df.index.to_frame()
            df2['model_id'] = model_id
            idx = pd.MultiIndex.from_frame(df2)

            df.loc[:, symbol_cols] += df[col].values.reshape(-1, 1) * df.loc[idx, symbol_cols].values
    return df


def calc_model_ret(df):
    model_ret = None
    for col in df.columns:
        if col.startswith("p."):
            ret_col = col.replace("p.", "ret.")
            if model_ret is None:
                model_ret = df[col] * df[ret_col]
            else:
                model_ret += df[col] * df[ret_col]
    return model_ret.unstack(level=0)


def preprocess_df(df, execution_time):
    df = df.fillna(0)
    df = df.filter(regex="^(p|w).", axis=1)
    for col in df.columns:
        if df[col].abs().sum() == 0:
            df = df.drop(col, axis=1)
    df = remove_portfolio_models(df)
    df = remove_inactive_models(df, execution_time - pd.to_timedelta(1, unit="D"))
    # TODO: consider delay
    # df = convert_to_executable_time(df, 4 * 60)
    df = asfreq_positions(
        df, "300S", execution_time
    )
    return df


def remove_portfolio_models(df):
    return df.loc[~df.index.get_level_values("model_id").str.startswith("portfolio:")]


def remove_inactive_models(df, min_timestamp):
    df_max_timestamp = df.reset_index().groupby("model_id")["timestamp"].max()
    df_max_timestamp = df_max_timestamp[min_timestamp <= df_max_timestamp]
    return df.loc[df.index.get_level_values("model_id").isin(df_max_timestamp.index)]


def convert_to_executable_time(df, execution_delay):
    df = df.reset_index()
    df["timestamp"] = np.maximum(
        df["timestamp"] + pd.to_timedelta(df["delay"] + execution_delay, unit="s"),
        df["timestamp"],
    )
    return df.set_index(["model_id", "timestamp"]).sort_index()


def asfreq_positions(df, freq, max_timestamp):
    dfs = []
    min_t = df.index.get_level_values('timestamp').min()
    for model_id, df_model in df.groupby("model_id"):
        df_model = df_model.reset_index().copy()
        df_model = df_model.drop_duplicates("timestamp", keep="last")
        df_model = df_model.set_index("timestamp").sort_index()

        t = min_t - pd.to_timedelta(freq)
        df_model.loc[t] = df_model.iloc[0]
        for col in df_model.columns:
            if col.startswith("p.") or col.startswith("w."):
                df_model.loc[t, col] = 0.0
        t = max_timestamp + pd.to_timedelta(freq)
        df_model.loc[t] = df_model.iloc[0]
        for col in df_model.columns:
            if col.startswith("p.") or col.startswith("w."):
                df_model.loc[t, col] = np.nan

        df_model = df_model.sort_index()
        df_model = df_model.asfreq(freq, method="ffill")
        df_model = df_model.loc[
            (df_model.index <= max_timestamp)
        ]

        dfs.append(df_model)

    return pd.concat(dfs).reset_index().set_index(["model_id", "timestamp"])
