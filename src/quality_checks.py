"""Geospatial data quality checks for the Olist geolocation dataset."""

import pandas as pd

LAT_MIN, LAT_MAX = -33.8, 5.3
LON_MIN, LON_MAX = -73.9, -28.6


def null_report(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Return null counts and percentages for the given columns."""
    counts = df[cols].isnull().sum()
    pct = (counts / len(df) * 100).round(2)
    return pd.DataFrame({"null_count": counts, "null_pct": pct})


def detect_out_of_bounds(
    df: pd.DataFrame,
    lat_col: str = "geolocation_lat",
    lon_col: str = "geolocation_lng",
) -> pd.DataFrame:
    """Return rows whose coordinates fall outside Brazil's bounding box."""
    mask = (
        (df[lat_col] < LAT_MIN) | (df[lat_col] > LAT_MAX) |
        (df[lon_col] < LON_MIN) | (df[lon_col] > LON_MAX)
    )
    return df[mask].copy()


def aggregate_centroids(
    geo_df: pd.DataFrame,
    zip_col: str = "geolocation_zip_code_prefix",
    lat_col: str = "geolocation_lat",
    lon_col: str = "geolocation_lng",
) -> pd.DataFrame:
    """Compute mean lat/lng centroid per ZIP prefix after removing out-of-bounds rows."""
    oob = detect_out_of_bounds(geo_df, lat_col, lon_col)
    clean = geo_df.drop(index=oob.index)
    centroids = (
        clean.groupby(zip_col)[[lat_col, lon_col]]
        .mean()
        .reset_index()
        .rename(columns={lat_col: "lat", lon_col: "lng"})
    )
    return centroids


def geo_quality_report(geo_df: pd.DataFrame) -> pd.DataFrame:
    """Return a single-row summary DataFrame with key quality metrics."""
    total = len(geo_df)
    oob = detect_out_of_bounds(geo_df)
    duplicates = geo_df.duplicated(subset=["geolocation_zip_code_prefix"]).sum()
    nulls = geo_df[["geolocation_lat", "geolocation_lng"]].isnull().sum().sum()
    return pd.DataFrame([{
        "total_rows": total,
        "out_of_bounds": len(oob),
        "out_of_bounds_pct": round(len(oob) / total * 100, 2),
        "duplicate_zips": int(duplicates),
        "null_coords": int(nulls),
    }])
