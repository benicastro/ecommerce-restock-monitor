import json
from pathlib import Path


PRODUCTS_FILE = Path("products.json")


def load_products():
    if not PRODUCTS_FILE.exists():
        raise RuntimeError(
            "products.json was not found. "
            "Copy products.example.json to products.json "
            "and add at least one Shopee product."
        )

    with open(
        PRODUCTS_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        config = json.load(file)

    products = config.get(
        "products",
        [],
    )

    if not products:
        raise RuntimeError(
            "No products were found in products.json."
        )

    return products
