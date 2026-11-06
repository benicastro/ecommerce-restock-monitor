import re


def extract_ids(product_url: str):
    """Extract a Shopee shop/item pair from either supported URL format."""
    clean_url = product_url.split("?", 1)[0]

    for pattern in (r"/product/(\d+)/(\d+)", r"-i\.(\d+)\.(\d+)"):
        match = re.search(pattern, clean_url)
        if match:
            return int(match.group(1)), int(match.group(2))

    raise ValueError("Could not find a Shopee shop ID and item ID in this URL.")


def convert_price(raw_price):
    """Convert Shopee's legacy 100,000-based PHP prices when available."""
    if raw_price is None:
        return None
    try:
        value = float(raw_price)
    except (TypeError, ValueError):
        return None
    if value < 0:
        return None
    return value / 100000


def build_image_url(image_id):
    if not image_id:
        return None
    return "https://down-ph.img.susercontent.com/file/" + str(image_id)


def _as_bool(value):
    """Return True/False only when the value is interpretable."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in ("true", "1"):
            return True
        if cleaned in ("false", "0"):
            return False
    return None


def _stock_number(value):
    if isinstance(value, bool):
        return int(value)
    try:
        # Reject values such as 1.5, malformed strings, and absent values.
        number = int(value)
        if str(value).strip() in (str(number), str(float(number))):
            return number
    except (TypeError, ValueError, OverflowError):
        pass
    return None


def _model_available(model):
    if "has_stock" in model:
        available = _as_bool(model.get("has_stock"))
        if available is not None:
            return available

    if "is_grayout" in model:
        grayout = _as_bool(model.get("is_grayout"))
        if grayout is not None:
            return not grayout

    quantity = _stock_number(model.get("stock"))
    if quantity is not None:
        return quantity > 0

    return None


def _normalize_models(models):
    normalized = []
    for model in models or []:
        if not isinstance(model, dict):
            raise RuntimeError("Shopee returned a malformed product model.")
        normalized.append({
            "model_id": model.get("modelid") or model.get("model_id"),
            "name": model.get("name") or model.get("model_name"),
            "price": convert_price(model.get("price")),
            "stock": model.get("stock"),
            "has_stock": _model_available(model),
            "is_grayout": model.get("is_grayout"),
        })
    return normalized


def _get_seller_name(data, item):
    # Shopee can put seller details outside the data.item object.
    for shop in (
        data.get("shop_detailed"),
        data.get("shop_info"),
        item.get("shop_detailed"),
    ):
        if not isinstance(shop, dict):
            continue
        seller = shop.get("name") or shop.get("shop_name")
        if seller:
            return seller
        account = shop.get("account")
        if isinstance(account, dict) and account.get("username"):
            return account["username"]

    return item.get("shop_name") or item.get("seller_name")


def _get_price(data, item):
    for raw in (item.get("price"), item.get("price_min")):
        price = convert_price(raw)
        if price is not None:
            return price

    product_price = data.get("product_price")
    if not isinstance(product_price, dict):
        return None
    info = product_price.get("price")
    if not isinstance(info, dict):
        return None
    for key in ("single_value", "range_min", "price_min"):
        price = convert_price(info.get(key))
        if price is not None:
            return price
    return None


def _get_availability(item, models):
    """Fail closed when stock is unknown rather than inventing 'sold out'."""
    statuses = [model["has_stock"] for model in models]
    if True in statuses:
        return True
    if statuses and all(status is False for status in statuses):
        return False

    display = item.get("stock_display")
    if display is not None:
        text = str(display).strip().upper()
        if text in ("OUT OF STOCK", "SOLD OUT", "NO STOCK"):
            return False
        if text in ("IN STOCK", "AVAILABLE"):
            return True

    quantity = _stock_number(item.get("stock"))
    if quantity is not None:
        return quantity > 0

    raise RuntimeError(
        "Shopee response has no reliable stock status; "
        "previous state was not changed."
    )


def parse_shopee_product(response):
    if not isinstance(response, dict):
        raise RuntimeError("Shopee response is not a JSON object.")
    data = response.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("Shopee response is missing data.")
    item = data.get("item")
    if not isinstance(item, dict):
        raise RuntimeError("Shopee response is missing item data.")

    raw_models = item.get("models")
    if raw_models is not None and not isinstance(raw_models, list):
        raise RuntimeError("Shopee returned malformed models data.")
    models = _normalize_models(raw_models or [])

    shop_id = item.get("shopid") or item.get("shop_id")
    item_id = item.get("itemid") or item.get("item_id")
    if shop_id is None or item_id is None:
        raise RuntimeError("Shopee response is missing product IDs.")
    title = item.get("name") or item.get("title")
    if not title:
        raise RuntimeError("Shopee response did not include a title.")
    available = _get_availability(item, models)
    image_id = item.get("image") or item.get("image_id")

    return {
        "platform": "shopee",
        "shop_id": shop_id,
        "item_id": item_id,
        "title": title,
        "brand": item.get("brand"),
        "seller": _get_seller_name(data, item),
        "currency": item.get("currency") or "PHP",
        "price": _get_price(data, item),
        "available": available,
        "stock_display": item.get("stock_display"),
        "image_id": image_id,
        "image_url": build_image_url(image_id),
        "models": models,
    }


def validate_target_identity(product, product_url):
    """Reject a captured response for any item other than the configured URL."""
    expected_shop, expected_item = extract_ids(product_url)
    try:
        actual_shop = int(product["shop_id"])
        actual_item = int(product["item_id"])
    except (TypeError, ValueError, KeyError) as error:
        raise RuntimeError("Shopee returned invalid product IDs.") from error
    if (actual_shop, actual_item) != (expected_shop, expected_item):
        raise RuntimeError(
            f"Shopee returned the wrong product: "
            f"expected {expected_shop}/{expected_item}, "
            f"got {actual_shop}/{actual_item}."
        )
