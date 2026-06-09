"""Spatial models: DBSCAN clustering, GWR, and Moran's I / LISA.

geopandas is imported lazily inside build_lisa_map to avoid a PROJ library
initialization hang on Windows at module load time.
"""

import pathlib
import numpy as np
import pandas as pd
import folium

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_MAPS_DIR = _ROOT / "outputs" / "maps"

CLUSTER_COLORS = [
    "#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00",
    "#a65628", "#f781bf", "#999999", "#66c2a5", "#fc8d62",
]
NOISE_COLOR = "#cccccc"


def run_dbscan(
    coords_array: np.ndarray,
    eps_km: float = 50.0,
    min_samples: int = 5,
) -> np.ndarray:
    """Run DBSCAN with haversine metric on lat/lng coordinates.

    coords_array: shape (n, 2) with columns [lat, lng] in degrees.
    Returns cluster labels (-1 = noise).
    """
    from sklearn.cluster import DBSCAN
    coords_rad = np.radians(coords_array)
    eps_rad = eps_km / 6371.0
    db = DBSCAN(eps=eps_rad, min_samples=min_samples, algorithm="ball_tree", metric="haversine")
    return db.fit_predict(coords_rad)


def build_folium_cluster_map(
    sellers_geo_df: pd.DataFrame,
    cluster_labels: np.ndarray,
    lat_col: str = "lat",
    lon_col: str = "lng",
    output_path: str | pathlib.Path | None = None,
) -> folium.Map:
    """Build an interactive Folium map colored by DBSCAN cluster.

    Saves to outputs/maps/seller_clusters.html by default.
    """
    if output_path is None:
        _MAPS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = _MAPS_DIR / "seller_clusters.html"

    df = sellers_geo_df.copy()
    df["cluster"] = cluster_labels
    center = [df[lat_col].mean(), df[lon_col].mean()]
    m = folium.Map(location=center, zoom_start=4, tiles="CartoDB positron")

    for _, row in df.iterrows():
        c = int(row["cluster"])
        color = NOISE_COLOR if c == -1 else CLUSTER_COLORS[c % len(CLUSTER_COLORS)]
        folium.CircleMarker(
            location=[row[lat_col], row[lon_col]],
            radius=4,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            tooltip=f"Cluster {c}",
        ).add_to(m)

    m.save(str(output_path))
    print(f"Cluster map saved → {output_path}")
    return m


def run_gwr(
    y: np.ndarray,
    X: np.ndarray,
    coords: np.ndarray,
    bw: float | None = None,
):
    """Fit a GWR model using mgwr.

    y: (n,) response array.
    X: (n, k) predictor matrix (should NOT include a constant column).
    coords: (n, 2) array of [lng, lat] in degrees.
    Returns mgwr GWRResults object.
    """
    from mgwr.gwr import GWR
    from mgwr.sel_bw import Sel_BW

    if bw is None:
        selector = Sel_BW(coords, y.reshape(-1, 1), X)
        bw = selector.search(criterion="AICc")
        print(f"Optimal bandwidth: {bw}")

    model = GWR(coords, y.reshape(-1, 1), X, bw=bw)
    results = model.fit()
    return results


def build_gwr_coefficient_map(
    geo_df: pd.DataFrame,
    gwr_results,
    predictor_idx: int = 1,
    lat_col: str = "seller_lat",
    lon_col: str = "seller_lng",
    output_path: str | pathlib.Path | None = None,
) -> folium.Map:
    """Build a choropleth map of local GWR coefficients."""
    import branca.colormap as cm

    if output_path is None:
        _MAPS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = _MAPS_DIR / "gwr_coefficients.html"

    df = geo_df.copy()
    df["gwr_coef"] = gwr_results.params[:, predictor_idx]
    center = [df[lat_col].mean(), df[lon_col].mean()]
    m = folium.Map(location=center, zoom_start=4, tiles="CartoDB positron")

    vmin, vmax = df["gwr_coef"].quantile(0.05), df["gwr_coef"].quantile(0.95)
    colormap = cm.linear.RdYlBu_11.scale(vmin, vmax)
    colormap.add_to(m)

    for _, row in df.iterrows():
        color = colormap(row["gwr_coef"])
        folium.CircleMarker(
            location=[row[lat_col], row[lon_col]],
            radius=5,
            color="#333",
            weight=0.5,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            tooltip=f"GWR coef: {row['gwr_coef']:.3f}",
        ).add_to(m)

    m.save(str(output_path))
    print(f"GWR coefficient map saved → {output_path}")
    return m


def compute_morans_i(values: np.ndarray, weights):
    """Compute global Moran's I and local LISA statistics.

    values: 1-D array aligned with the spatial weights object.
    weights: libpysal weights object (e.g. Queen).
    Returns (esda.Moran, esda.Moran_Local).
    """
    from esda.moran import Moran, Moran_Local
    moran_global = Moran(values, weights)
    moran_local = Moran_Local(values, weights)
    print(f"Moran's I = {moran_global.I:.4f}  p-value = {moran_global.p_sim:.4f}")
    return moran_global, moran_local


LISA_COLORS = {
    "HH": "#d7191c",
    "LH": "#abd9e9",
    "LL": "#2c7bb6",
    "HL": "#fdae61",
    "NS": "#eeeeee",
}

LISA_LABELS = {1: "HH", 2: "LH", 3: "LL", 4: "HL"}


def build_lisa_map(
    geo_gdf,
    lisa,
    value_col: str,
    output_path: str | pathlib.Path | None = None,
) -> folium.Map:
    """Build a LISA quadrant map (HH/LH/LL/HL/NS).

    geo_gdf: GeoDataFrame with geometry (Point or Polygon) aligned with lisa results.
    lisa: esda.Moran_Local result.
    value_col: column name used in tooltip.
    """
    import geopandas as gpd  # noqa: F401
    if output_path is None:
        _MAPS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = _MAPS_DIR / "lisa_satisfaction.html"

    gdf = geo_gdf.copy()
    sig = lisa.p_sim < 0.05
    gdf["quad_label"] = "NS"
    for code, label in LISA_LABELS.items():
        gdf.loc[(lisa.q == code) & sig, "quad_label"] = label
    gdf["color"] = gdf["quad_label"].map(LISA_COLORS)

    bounds = gdf.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2
    m = folium.Map(location=[center_lat, center_lon], zoom_start=4, tiles="CartoDB positron")

    legend_html = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
                background:white;padding:10px;border:1px solid grey;font-size:13px;">
      <b>LISA Quadrants</b><br>
      <span style="color:#d7191c">&#9632;</span> HH (High-High)<br>
      <span style="color:#fdae61">&#9632;</span> HL (High-Low)<br>
      <span style="color:#abd9e9">&#9632;</span> LH (Low-High)<br>
      <span style="color:#2c7bb6">&#9632;</span> LL (Low-Low)<br>
      <span style="color:#eeeeee">&#9632;</span> NS (Not Significant)
    </div>"""
    m.get_root().html.add_child(folium.Element(legend_html))

    tooltip_fields = ["name", value_col, "quad_label"] if "name" in gdf.columns else [value_col, "quad_label"]

    for _, row in gdf.iterrows():
        geom = row["geometry"]
        color = row["color"]
        tip_parts = [f"{f}: {row[f]}" for f in tooltip_fields if f in row.index]
        tip_text = " | ".join(str(p) for p in tip_parts)

        if geom.geom_type == "Point":
            folium.CircleMarker(
                location=[geom.y, geom.x],
                radius=10,
                color="#333",
                weight=1,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                tooltip=tip_text,
            ).add_to(m)
        else:
            feature = {
                "type": "Feature",
                "geometry": geom.__geo_interface__,
                "properties": {f: str(row[f]) for f in tooltip_fields if f in row.index},
            }
            folium.GeoJson(
                feature,
                style_function=lambda _, c=color: {
                    "fillColor": c,
                    "color": "#333",
                    "weight": 1,
                    "fillOpacity": 0.7,
                },
                tooltip=folium.GeoJsonTooltip(fields=tooltip_fields),
            ).add_to(m)

    m.save(str(output_path))
    print(f"LISA map saved → {output_path}")
    return m
