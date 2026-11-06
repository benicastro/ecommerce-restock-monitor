import os
from datetime import datetime

import requests
from dotenv import load_dotenv


load_dotenv()


def _get_webhook_url():
    webhook_url = os.getenv(
        "DISCORD_WEBHOOK_URL"
    )

    if not webhook_url:
        raise RuntimeError(
            "DISCORD_WEBHOOK_URL is missing. "
            "Create a .env file from .env.example."
        )

    return webhook_url


def _post_payload(
    payload,
):
    response = requests.post(
        _get_webhook_url(),
        json=payload,
        timeout=15,
    )

    response.raise_for_status()


def _product_url(
    product,
):
    return (
        "https://shopee.ph/product/"
        f'{product["shop_id"]}/'
        f'{product["item_id"]}'
    )


def send_restock_notification(
    product,
):
    price = product.get(
        "price"
    )

    if price is None:
        price_text = "Unknown"

    else:
        price_text = (
            f"PHP {price:,.2f}"
        )

    fields = [
        {
            "name": "Store",
            "value": (
                product.get("seller")
                or "Unknown"
            ),
            "inline": True,
        },
        {
            "name": "Price",
            "value": price_text,
            "inline": True,
        },
        {
            "name": "Status",
            "value": "IN STOCK",
            "inline": True,
        },
    ]

    brand = product.get(
        "brand"
    )

    if brand:
        fields.append(
            {
                "name": "Brand",
                "value": str(brand),
                "inline": True,
            }
        )

    embed = {
        "title": (
            "RESTOCK: "
            + product["title"]
        ),
        "url": _product_url(
            product
        ),
        "description": (
            "A monitored Shopee product "
            "changed from out of stock "
            "to available."
        ),
        "fields": fields,
        "timestamp": (
            datetime.now()
            .astimezone()
            .isoformat()
        ),
    }

    image_url = product.get(
        "image_url"
    )

    if image_url:
        embed["thumbnail"] = {
            "url": image_url
        }

    _post_payload(
        {
            "content": (
                "🚨 Shopee restock detected"
            ),
            "embeds": [
                embed
            ],
        }
    )


def send_monitor_warning(
    product_config,
    failures,
    error_text,
):
    name = product_config.get(
        "name",
        "Unknown product",
    )

    _post_payload(
        {
            "content": (
                "⚠️ Restock monitor warning"
            ),
            "embeds": [
                {
                    "title": (
                        "Product monitor is failing"
                    ),
                    "description": (
                        f"**{name}** has failed "
                        f"{failures} consecutive checks."
                    ),
                    "fields": [
                        {
                            "name": "Last error",
                            "value": (
                                str(error_text)[:1000]
                            ),
                            "inline": False,
                        }
                    ],
                    "timestamp": (
                        datetime.now()
                        .astimezone()
                        .isoformat()
                    ),
                }
            ],
        }
    )


def send_monitor_recovery(
    product_config,
    previous_failures,
):
    name = product_config.get(
        "name",
        "Unknown product",
    )

    _post_payload(
        {
            "content": (
                "✅ Restock monitor recovered"
            ),
            "embeds": [
                {
                    "title": (
                        "Product monitor recovered"
                    ),
                    "description": (
                        f"**{name}** is working again "
                        f"after {previous_failures} "
                        "consecutive failures."
                    ),
                    "timestamp": (
                        datetime.now()
                        .astimezone()
                        .isoformat()
                    ),
                }
            ],
        }
    )
