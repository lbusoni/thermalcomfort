import cdsapi

dataset = "derived-utci-historical-timeseries"

request = {
    "variable": [
        "mean_radiant_temperature",
        "universal_thermal_climate_index",
    ],
    "location": {
        "longitude": 11.25,
        "latitude": 43.75,
    },
    "date": [
        "2026-06-10/2026-06-10"
    ],
    "data_format": "netcdf",
}

client = cdsapi.Client()

client.retrieve(
    dataset,
    request,
    "era5_extract/utci_firenze_20260610.nc"
)

print()
print("Download completato:")
print("  era5_extract/utci_firenze_20260610.nc")

