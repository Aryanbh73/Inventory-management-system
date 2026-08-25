import sys
import os

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

BACKEND_PATH = os.path.join(
    PROJECT_ROOT,
    "backend"
)

sys.path.insert(0, BACKEND_PATH)


import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestRegressor

from data_preparation import get_sales_history

def prepare_product_data(product_id):

    df = get_sales_history()

    if df.empty:
        return pd.DataFrame()

    df["sale_date"] = pd.to_datetime(
        df["sale_date"]
    )

    product_df = df[
        df["product_id"] == product_id
    ].copy()

    if product_df.empty:
        return pd.DataFrame()

    # Combine sales occurring on the same day
    product_df = (
        product_df
        .groupby("sale_date")["quantity"]
        .sum()
        .reset_index()
    )

    # Create continuous daily dates
    date_range = pd.date_range(
        start=product_df["sale_date"].min(),
        end=product_df["sale_date"].max(),
        freq="D"
    )

    product_df = (
        product_df
        .set_index("sale_date")
        .reindex(date_range, fill_value=0)
        .rename_axis("sale_date")
        .reset_index()
    )

    return product_df

def create_features(df):

    df = df.copy()

    df["lag_1"] = df["quantity"].shift(1)

    df["lag_7"] = df["quantity"].shift(7)

    df["rolling_7"] = (
        df["quantity"]
        .shift(1)
        .rolling(7)
        .mean()
    )

    df["day_of_week"] = (
        df["sale_date"].dt.dayofweek
    )

    df["day_of_month"] = (
        df["sale_date"].dt.day
    )

    df = df.dropna()

    return df

def train_model(product_id):

    df = prepare_product_data(product_id)

    if len(df) < 14:
        return None, df

    df = create_features(df)

    if len(df) < 7:
        return None, df

    features = [
        "lag_1",
        "lag_7",
        "rolling_7",
        "day_of_week",
        "day_of_month"
    ]

    X = df[features]

    y = df["quantity"]

    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42
    )

    model.fit(X, y)

    return model, df

def forecast_product(product_id, days=7):

    model, df = train_model(product_id)

    if model is None:

        if df.empty:
            return 0

        average_demand = (
            df["quantity"]
            .tail(7)
            .mean()
        )

        return round(
            average_demand * days
        )

    history = df.copy()

    predictions = []

    for _ in range(days):

        last_date = history["sale_date"].iloc[-1]

        next_date = (
            last_date +
            pd.Timedelta(days=1)
        )

        lag_1 = (
            history["quantity"]
            .iloc[-1]
        )

        if len(history) >= 7:

            lag_7 = (
                history["quantity"]
                .iloc[-7]
            )

        else:

            lag_7 = lag_1

        rolling_7 = (
            history["quantity"]
            .tail(7)
            .mean()
        )

        day_of_week = (
            next_date.dayofweek
        )

        day_of_month = (
            next_date.day
        )

        X_future = pd.DataFrame(
            [[
                lag_1,
                lag_7,
                rolling_7,
                day_of_week,
                day_of_month
            ]],
            columns=[
                "lag_1",
                "lag_7",
                "rolling_7",
                "day_of_week",
                "day_of_month"
            ]
        )

        prediction = model.predict(
            X_future
        )[0]

        prediction = max(
            0,
            prediction
        )

        predictions.append(
            prediction
        )

        new_row = pd.DataFrame({
            "sale_date": [next_date],
            "quantity": [prediction]
        })

        history = pd.concat(
            [history, new_row],
            ignore_index=True
        )

    return round(
        sum(predictions)
    )

if __name__ == "__main__":

    product_id = 1

    forecast_7 = forecast_product(
        product_id,
        7
    )

    forecast_30 = forecast_product(
        product_id,
        30
    )

    print(
        f"7-Day Forecast: {forecast_7} units"
    )

    print(
        f"30-Day Forecast: {forecast_30} units"
    )
