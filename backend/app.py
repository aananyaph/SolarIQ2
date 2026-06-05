from datetime import datetime
import random

import numpy as np
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS
from prophet import Prophet

app = Flask(__name__)
CORS(app)

CAMPUS_NAME = "ABC&D Block"
SYSTEM_CAPACITY_KWP = 170

# User-provided ABC&D Block Solar Details (170 kWp), March 2024-February 2025.
# Generated records are kept separate and never added to this real-data list.
REAL_MONTHLY_DATA = [
    {"month": "2024-03", "eb": 58380, "solar": 14719, "source": "actual"},
    {"month": "2024-04", "eb": 61460, "solar": 14371, "source": "actual"},
    {"month": "2024-05", "eb": 63340, "solar": 12198, "source": "actual"},
    {"month": "2024-06", "eb": 54200, "solar": 12052, "source": "actual"},
    {"month": "2024-07", "eb": 56240, "solar": 9362, "source": "actual"},
    {"month": "2024-08", "eb": 60960, "solar": 10775, "source": "actual"},
    {"month": "2024-09", "eb": 60000, "solar": 11745, "source": "actual"},
    {"month": "2024-10", "eb": 65600, "solar": 10702, "source": "actual"},
    {"month": "2024-11", "eb": 60960, "solar": 10612, "source": "actual"},
    {"month": "2024-12", "eb": 57860, "solar": 10757, "source": "actual"},
    {"month": "2025-01", "eb": 56760, "solar": 13121, "source": "actual"},
    {"month": "2025-02", "eb": 63040, "solar": 14050, "source": "actual"},
]

TARIFFS = {
    "domestic": 5.8,
    "institution": 6.3,
    "industry": 7.5,
}

SOLAR_TARIFFS = {
    "domestic_no_subsidy": 4.15,
    "pm_surya_1_2kw": 2.30,
    "pm_surya_2_3kw": 2.48,
    "pm_surya_above_3kw": 2.93,
    "non_domestic": 3.08,
    "mw_ground": 3.07,
}


def monthly_df(records):
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["month"] + "-01")
    return add_energy_columns(df)


def real_monthly_df():
    return monthly_df(REAL_MONTHLY_DATA)


def add_energy_columns(df):
    df["load"] = df["eb"].astype(float)
    df["solar"] = df["solar"].astype(float)
    df["total"] = df["load"] + df["solar"]
    df["eb_percentage"] = (df["load"] / df["total"]) * 100
    df["solar_percentage"] = (df["solar"] / df["total"]) * 100
    return df


def month_start(value):
    return pd.to_datetime(value).to_period("M").to_timestamp()


def month_variation(target_month):
    """Return a stable pseudo-random variation so parallel API calls agree."""
    seed = int(target_month.strftime("%Y%m")) + (SYSTEM_CAPACITY_KWP * 10000)
    return random.Random(seed).uniform(-0.05, 0.05)


def generated_dummy_records(end=None):
    """Generate missing months after the real dataset through the requested month."""
    real_df = real_monthly_df()
    last_real_month = real_df["date"].max()
    end_dt = month_start(end if end is not None else datetime.now())
    first_dummy_month = last_real_month + pd.DateOffset(months=1)

    if end_dt < first_dummy_month:
        return []

    records_by_month = {
        row["date"].strftime("%Y-%m"): row.to_dict()
        for _, row in real_df.iterrows()
    }
    dummy_records = []

    for target_month in pd.date_range(first_dummy_month, end_dt, freq="MS"):
        base_month = target_month - pd.DateOffset(years=1)
        base = records_by_month[base_month.strftime("%Y-%m")]
        variation = month_variation(target_month)
        multiplier = 1 + variation

        # One multiplier preserves the base month's EB-to-solar ratio.
        record = {
            "month": target_month.strftime("%Y-%m"),
            "date": target_month,
            "eb": int(round(float(base["load"]) * multiplier)),
            "solar": int(round(float(base["solar"]) * multiplier)),
            "source": "dummy",
            "base_month": base_month.strftime("%Y-%m"),
            "variation_pct": round(variation * 100, 2),
        }
        records_by_month[record["month"]] = {
            **record,
            "load": float(record["eb"]),
        }
        dummy_records.append(record)

    return dummy_records


def dummy_monthly_df(end=None):
    records = generated_dummy_records(end)
    if not records:
        return real_monthly_df().iloc[0:0].copy()
    return monthly_df(records)


def campus_history_between(start=None, end=None):
    real_df = real_monthly_df()
    start_dt = month_start(start) if start else real_df["date"].min()
    end_dt = month_start(end) if end else month_start(datetime.now())

    if start_dt > end_dt:
        return real_df.iloc[0:0].copy()

    dummy_df = dummy_monthly_df(end_dt)
    combined = pd.concat([real_df, dummy_df], ignore_index=True)
    rows = combined[(combined["date"] >= start_dt) & (combined["date"] <= end_dt)].copy()

    return rows.sort_values("date").reset_index(drop=True)


def campus_records(df):
    records = []
    for _, row in df.iterrows():
        is_dummy = row.get("source") == "dummy"
        records.append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "solar": round(float(row["solar"]), 2),
            "load": round(float(row["load"]), 2),
            "total": round(float(row["total"]), 2),
            "eb_percentage": round(float(row["eb_percentage"]), 8),
            "solar_percentage": round(float(row["solar_percentage"]), 8),
            "source": row.get("source", "actual"),
            "base_month": row.get("base_month") if is_dummy else None,
            "variation_pct": float(row.get("variation_pct")) if is_dummy else None,
        })
    return records


def forecast_metric(metric, start_dt, end_dt):
    df = campus_history_between(start_dt, end_dt)
    return pd.DataFrame({
        "ds": df["date"],
        "yhat": df[metric].clip(lower=0),
    })


@app.route("/")
def home():
    return jsonify({
        "message": "SolarIQ Flask backend active",
        "version": "CAMPUS_BACKEND",
        "campus": CAMPUS_NAME,
        "capacity_kwp": SYSTEM_CAPACITY_KWP,
        "routes": ["/history", "/today_status", "/solar_status", "/predict", "/nasa_data", "/load_history"],
    })


@app.route("/nasa_data")
def nasa_data():
    """Compatibility endpoint: returns campus solar generation instead of random/NASA values."""
    start = request.args.get("start")
    end = request.args.get("end")
    if start and len(start) == 8:
        start = f"{start[:4]}-{start[4:6]}-{start[6:8]}"
    if end and len(end) == 8:
        end = f"{end[:4]}-{end[4:6]}-{end[6:8]}"

    df = campus_history_between(start, end)
    data = [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "solar_irradiance": round(float(row["solar"]), 2),
            "source": row.get("source", "actual"),
        }
        for _, row in df.iterrows()
    ]
    return jsonify({"status": "success", "campus": CAMPUS_NAME, "data": data})


@app.route("/history")
def history():
    start = request.args.get("start")
    end = request.args.get("end")
    return jsonify(campus_records(campus_history_between(start, end)))


@app.route("/load_history")
def load_history():
    start = request.args.get("start")
    end = request.args.get("end")
    if not start or not end:
        return jsonify({"status": "error", "message": "Missing start or end date"}), 400

    df = campus_history_between(start, end)
    data = [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "load": round(float(row["load"]), 2),
            "source": row.get("source", "actual"),
        }
        for _, row in df.iterrows()
    ]
    return jsonify({"status": "success", "campus": CAMPUS_NAME, "data": data})


@app.route("/today_status")
def today_status():
    df = campus_history_between(end=datetime.now())
    latest = df.iloc[-1]
    latest_year_start = latest["date"] - pd.DateOffset(months=11)
    latest_year_df = df[(df["date"] >= latest_year_start) & (df["date"] <= latest["date"])]
    totals = latest_year_df[["load", "solar", "total"]].sum()
    return jsonify({
        "status": "success",
        "campus": CAMPUS_NAME,
        "capacity_kwp": SYSTEM_CAPACITY_KWP,
        "latest_month": latest["date"].strftime("%Y-%m"),
        "latest_eb_energy": round(float(latest["load"]), 2),
        "latest_solar_energy": round(float(latest["solar"]), 2),
        "latest_total_energy": round(float(latest["total"]), 2),
        "latest_source": latest.get("source", "actual"),
        "summary_start_month": latest_year_start.strftime("%Y-%m"),
        "summary_end_month": latest["date"].strftime("%Y-%m"),
        "annual_eb_energy": round(float(totals["load"]), 2),
        "annual_solar_energy": round(float(totals["solar"]), 2),
        "annual_total_energy": round(float(totals["total"]), 2),
        "annual_eb_percentage": round(float(totals["load"] / totals["total"] * 100), 8),
        "annual_solar_percentage": round(float(totals["solar"] / totals["total"] * 100), 8),
        "dummy_months": int((latest_year_df["source"] == "dummy").sum()),
    })


@app.route("/solar_status")
def solar_status():
    category = request.args.get("category", "institution")
    avg_power = float(request.args.get("avg_power", SYSTEM_CAPACITY_KWP))
    latest = campus_history_between(end=datetime.now()).iloc[-1]

    solar_generation = float(latest["solar"])
    grid_import = float(latest["load"])
    grid_export = 0.0
    total_consumption = float(latest["total"])
    grid_tariff = TARIFFS.get(category, TARIFFS["institution"])
    solar_tariff = SOLAR_TARIFFS["non_domestic"] if category in ["institution", "industry"] else SOLAR_TARIFFS["domestic_no_subsidy"]
    normal_bill = total_consumption * grid_tariff
    solar_bill = grid_import * grid_tariff
    solar_generation_cost = solar_generation * solar_tariff
    savings = normal_bill - (solar_bill + solar_generation_cost)
    peak_voltage = 415.0
    peak_current = round((avg_power * 1000) / (np.sqrt(3) * peak_voltage), 2)

    return jsonify({
        "campus": CAMPUS_NAME,
        "category": category,
        "month": latest["date"].strftime("%Y-%m"),
        "solar_generation": round(solar_generation, 2),
        "grid_import": round(grid_import, 2),
        "grid_export": round(grid_export, 2),
        "net_grid_consumption": round(grid_import - grid_export, 2),
        "total_consumption": round(total_consumption, 2),
        "grid_tariff": grid_tariff,
        "solar_tariff": solar_tariff,
        "normal_bill": round(normal_bill, 2),
        "solar_bill": round(solar_bill, 2),
        "solar_generation_cost": round(solar_generation_cost, 2),
        "savings": round(savings, 2),
        "peak_voltage": peak_voltage,
        "peak_current": peak_current,
        "peak_power": SYSTEM_CAPACITY_KWP,
    })


@app.route("/predict", methods=["POST"])
def predict():
    try:
        req = request.get_json(force=True)
        start = req.get("start_date")
        end = req.get("end_date")

        if not start or not end:
            return jsonify({"status": "error", "message": "Missing start_date and end_date"}), 400

        start_dt = pd.to_datetime(start)
        end_dt = pd.to_datetime(end)
        solar_forecast = forecast_metric("solar", start_dt, end_dt)
        load_forecast = forecast_metric("load", start_dt, end_dt)
        merged = pd.merge(solar_forecast, load_forecast, on="ds", suffixes=("_solar", "_load"))

        predictions = []
        for _, row in merged.iterrows():
            solar = round(float(row["yhat_solar"]), 2)
            load = round(float(row["yhat_load"]), 2)
            predictions.append({
                "ds": row["ds"].strftime("%Y-%m-%d"),
                "date": row["ds"].strftime("%Y-%m-%d"),
                "yhat_solar": solar,
                "yhat_load": load,
                "yhat": solar,
                "total": round(solar + load, 2),
            })

        return jsonify({"status": "success", "campus": CAMPUS_NAME, "predictions": predictions})
    except Exception as e:
        import traceback
        print("Predict error:", traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)
