"""Data loading and caching utilities for the Olist dataset."""

import pathlib
import pandas as pd

TABLES = [
    "olist_orders_dataset",
    "olist_order_items_dataset",
    "olist_order_payments_dataset",
    "olist_order_reviews_dataset",
    "olist_customers_dataset",
    "olist_sellers_dataset",
    "olist_products_dataset",
    "olist_geolocation_dataset",
]

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_OUTPUTS_DIR = _ROOT / "outputs" / "processed_data"


def download_dataset() -> str:
    """Download the Olist dataset via kagglehub and return the local path."""
    import kagglehub
    path = kagglehub.dataset_download("olistbr/brazilian-ecommerce")
    print(f"Dataset path: {path}")
    return path


def load_tables(path: str | None = None) -> dict[str, pd.DataFrame]:
    """Load all 8 Olist CSV tables.

    Uses cached CSVs in outputs/processed_data/ when available.
    Downloads via kagglehub if path is None and no cache exists.
    """
    tables: dict[str, pd.DataFrame] = {}
    missing = []

    for name in TABLES:
        cached = _OUTPUTS_DIR / f"{name}.csv"
        if cached.exists():
            tables[name] = pd.read_csv(cached)
        else:
            missing.append(name)

    if missing:
        if path is None:
            path = download_dataset()
        data_dir = pathlib.Path(path)
        for name in missing:
            csv_path = data_dir / f"{name}.csv"
            if csv_path.exists():
                tables[name] = pd.read_csv(csv_path)
            else:
                print(f"Warning: {csv_path} not found — skipping.")

    print(f"Loaded {len(tables)} tables.")
    return tables


def cache_tables(tables: dict[str, pd.DataFrame]) -> None:
    """Save each DataFrame as a CSV in outputs/processed_data/."""
    _OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(_OUTPUTS_DIR / f"{name}.csv", index=False)
    print(f"Cached {len(tables)} tables to {_OUTPUTS_DIR}")
