from datetime import datetime

from database import get_connection


def get_product_key(product):
    return (
        f'{product["platform"]}:'
        f'{product["shop_id"]}:'
        f'{product["item_id"]}'
    )


def load_product_state(product):
    product_key = get_product_key(
        product
    )

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                available,
                price,
                updated_at
            FROM product_state
            WHERE product_key = ?
            """,
            (product_key,),
        ).fetchone()

    if row is None:
        return None

    return {
        "available": bool(row[0]),
        "price": row[1],
        "updated_at": row[2],
    }


def save_product_state(product):
    product_key = get_product_key(
        product
    )

    timestamp = datetime.now().isoformat(
        timespec="seconds"
    )

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO product_state (
                product_key,
                platform,
                shop_id,
                item_id,
                title,
                available,
                price,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(product_key)
            DO UPDATE SET
                title = excluded.title,
                available = excluded.available,
                price = excluded.price,
                updated_at = excluded.updated_at
            """,
            (
                product_key,
                product.get("platform"),
                str(
                    product.get("shop_id")
                ),
                str(
                    product.get("item_id")
                ),
                product.get("title"),
                int(
                    product.get(
                        "available",
                        False,
                    )
                ),
                product.get("price"),
                timestamp,
            ),
        )

        connection.commit()


def record_product_event(
    product,
    event_type,
):
    product_key = get_product_key(
        product
    )

    timestamp = datetime.now().isoformat(
        timespec="seconds"
    )

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO product_events (
                product_key,
                event_type,
                title,
                price,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                product_key,
                event_type,
                product.get("title"),
                product.get("price"),
                timestamp,
            ),
        )

        connection.commit()


def get_health_key(
    product_config,
):
    platform = product_config.get(
        "platform",
        "unknown",
    )

    url = product_config.get(
        "url",
        "unknown",
    )

    return f"{platform}:{url}"


def load_monitor_health(
    product_config,
):
    health_key = get_health_key(
        product_config
    )

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                consecutive_failures,
                alert_sent,
                last_error
            FROM monitor_health
            WHERE product_key = ?
            """,
            (health_key,),
        ).fetchone()

    if row is None:
        return {
            "consecutive_failures": 0,
            "alert_sent": False,
            "last_error": None,
        }

    return {
        "consecutive_failures": row[0],
        "alert_sent": bool(row[1]),
        "last_error": row[2],
    }


def save_monitor_health(
    product_config,
    consecutive_failures,
    alert_sent,
    last_error=None,
):
    health_key = get_health_key(
        product_config
    )

    timestamp = datetime.now().isoformat(
        timespec="seconds"
    )

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO monitor_health (
                product_key,
                consecutive_failures,
                alert_sent,
                last_error,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(product_key)
            DO UPDATE SET
                consecutive_failures = excluded.consecutive_failures,
                alert_sent = excluded.alert_sent,
                last_error = excluded.last_error,
                updated_at = excluded.updated_at
            """,
            (
                health_key,
                consecutive_failures,
                int(alert_sent),
                last_error,
                timestamp,
            ),
        )

        connection.commit()
