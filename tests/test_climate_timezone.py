import pandas as pd

from thermalcomfort.climate import ClimateAnalysis


def test_daytime_filter_uses_local_timezone():
    ca = ClimateAnalysis(start_year=2015, end_year=2015)

    utc_index = pd.date_range("2020-06-01 00:00", periods=24, freq="h", tz="UTC")
    df = pd.DataFrame(
        {
            "utci": [20.0] * 24,
            "utci_category": ["no thermal stress"] * 24,
            "temperature_2m": [20.0] * 24,
            "relative_humidity_2m": [50.0] * 24,
            "wind_speed_10m": [1.0] * 24,
        },
        index=utc_index,
    )

    filtered = ca._filter_daytime_hours(df, timezone="Europe/Rome")

    assert filtered.index.hour.tolist() == list(range(7, 20))
