"""Geospatial utility functions: distances, joins, and GeoDataFrame conversion.

geopandas and shapely are imported lazily inside each function that needs them
to avoid a PROJ library initialization hang on Windows at module load time.
"""

import numpy as np
import pandas as pd

EARTH_RADIUS_KM = 6371.0


def haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Return the great-circle distance in km between two points."""
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return EARTH_RADIUS_KM * 2 * np.arcsin(np.sqrt(a))


def add_seller_buyer_distance(
    orders_df: pd.DataFrame,
    items_df: pd.DataFrame,
    sellers_geo: pd.DataFrame,
    customers_geo: pd.DataFrame,
) -> pd.DataFrame:
    """Join orders with seller/customer coordinates and compute haversine distance.

    Returns a DataFrame with columns: order_id, seller_lat, seller_lng,
    customer_lat, customer_lng, distance_km, delivery_days.
    """
    items = items_df[["order_id", "seller_id"]].drop_duplicates("order_id")
    df = orders_df.merge(items, on="order_id", how="left")

    df = df.merge(
        sellers_geo[["geolocation_zip_code_prefix", "lat", "lng"]]
        .rename(columns={"geolocation_zip_code_prefix": "seller_zip", "lat": "seller_lat", "lng": "seller_lng"}),
        left_on="seller_zip_code_prefix",
        right_on="seller_zip",
        how="left",
    ).merge(
        customers_geo[["geolocation_zip_code_prefix", "lat", "lng"]]
        .rename(columns={"geolocation_zip_code_prefix": "customer_zip", "lat": "customer_lat", "lng": "customer_lng"}),
        left_on="customer_zip_code_prefix",
        right_on="customer_zip",
        how="left",
    )

    mask = df[["seller_lat", "seller_lng", "customer_lat", "customer_lng"]].notna().all(axis=1)
    df.loc[mask, "distance_km"] = haversine_distance(
        df.loc[mask, "seller_lat"].values,
        df.loc[mask, "seller_lng"].values,
        df.loc[mask, "customer_lat"].values,
        df.loc[mask, "customer_lng"].values,
    )

    for col in ["order_delivered_customer_date", "order_purchase_timestamp"]:
        df[col] = pd.to_datetime(df[col])
    df["delivery_days"] = (
        df["order_delivered_customer_date"] - df["order_purchase_timestamp"]
    ).dt.days

    return df


def to_geodataframe(
    df: pd.DataFrame,
    lat_col: str = "lat",
    lon_col: str = "lng",
):
    """Convert a DataFrame with lat/lon columns to a GeoDataFrame (EPSG:4326)."""
    import geopandas as gpd
    from shapely.geometry import Point
    geometry = [Point(xy) for xy in zip(df[lon_col], df[lat_col])]
    return gpd.GeoDataFrame(df.copy(), geometry=geometry, crs="EPSG:4326")
