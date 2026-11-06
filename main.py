import time
from datetime import (
    datetime,
    time as datetime_time,
)

from database import initialize_database
from discord_notifier import (
    send_monitor_recovery,
    send_monitor_warning,
    send_restock_notification,
)
from handoff import (
    open_product_in_browser,
)
from logger import setup_logger
from monitor import process_product
from products import load_products
from shopee import (
    parse_shopee_product,
    validate_target_identity,
)
from shopee_browser import (
    ShopeeBrowser,
)
from state import (
    load_monitor_health,
    save_monitor_health,
)


NORMAL_INTERVAL = 60
BURST_INTERVAL = 5

# Example high-frequency window for an
# announced 3:40 PM product drop.
# Change these constants for your own schedule.
BURST_START = datetime_time(
    15,
    35,
)

BURST_END = datetime_time(
    15,
    45,
)

FAILURE_ALERT_THRESHOLD = 5

logger = setup_logger()


def get_check_interval():
    now = datetime.now()
    current_time = now.time()

    if BURST_START <= current_time < BURST_END:
        return BURST_INTERVAL

    if current_time < BURST_START:
        start = datetime.combine(now.date(), BURST_START)
        seconds_to_start = (start - now).total_seconds()
        # Avoid sleeping past the start of the announced burst window.
        return min(NORMAL_INTERVAL, max(0.1, seconds_to_start))

    return NORMAL_INTERVAL


def handle_product_failure(
    product_config,
    error,
):
    health = (
        load_monitor_health(
            product_config
        )
    )

    failures = (
        health[
            "consecutive_failures"
        ]
        + 1
    )

    alert_sent = (
        health[
            "alert_sent"
        ]
    )

    error_text = (
        f"{type(error).__name__}: "
        f"{error}"
    )

    logger.error(
        "Monitor failure | product=%s | "
        "failures=%s | error=%s",
        product_config.get("name"),
        failures,
        error_text,
    )

    if (
        failures
        >= FAILURE_ALERT_THRESHOLD
        and not alert_sent
    ):
        try:
            send_monitor_warning(
                product_config,
                failures,
                error_text,
            )

            alert_sent = True

            logger.warning(
                "Monitor warning sent | "
                "product=%s | failures=%s",
                product_config.get(
                    "name"
                ),
                failures,
            )

        except Exception:
            logger.exception(
                "Could not send monitor warning | "
                "product=%s",
                product_config.get(
                    "name"
                ),
            )

    save_monitor_health(
        product_config,
        failures,
        alert_sent,
        error_text,
    )


def handle_product_success(
    product_config,
):
    health = (
        load_monitor_health(
            product_config
        )
    )

    failures = health[
        "consecutive_failures"
    ]

    alert_sent = health[
        "alert_sent"
    ]

    if failures == 0:
        return

    logger.info(
        "Monitor recovered | product=%s | "
        "previous_failures=%s",
        product_config.get("name"),
        failures,
    )

    if alert_sent:
        try:
            send_monitor_recovery(
                product_config,
                failures,
            )

        except Exception:
            logger.exception(
                "Could not send recovery notification | "
                "product=%s",
                product_config.get(
                    "name"
                ),
            )

    save_monitor_health(
        product_config,
        consecutive_failures=0,
        alert_sent=False,
        last_error=None,
    )


def check_shopee_product(
    browser,
    product_config,
):
    check_started = (
        time.perf_counter()
    )

    product_url = (
        product_config["url"]
    )

    print()
    print(
        "Checking:"
    )
    print(
        product_url
    )

    response = (
        browser.fetch_product(
            product_url
        )
    )

    product = (
        parse_shopee_product(
            response
        )
    )

    validate_target_identity(
        product,
        product_url,
    )

    result = (
        process_product(
            product
        )
    )

    elapsed = (
        time.perf_counter()
        - check_started
    )

    logger.info(
        "Check completed | product=%s | "
        "duration=%.2fs",
        product["title"],
        elapsed,
    )

    logger.info(
        "Product checked | %s | "
        "seller=%s | "
        "available=%s | "
        "price=%s | "
        "event=%s",
        product["title"],
        product.get("seller"),
        product.get("available"),
        product.get("price"),
        result["event"],
    )

    print()
    print(
        "Product:"
    )
    print(
        product["title"]
    )

    print(
        "Available:",
        product["available"],
    )

    print(
        "Price:",
        product.get("price"),
    )

    print(
        "Event:",
        result["event"],
    )

    if (
        result["event"]
        == "RESTOCK"
    ):
        logger.warning(
            "RESTOCK | %s | "
            "seller=%s | "
            "price=%s",
            product["title"],
            product.get("seller"),
            product.get("price"),
        )

        try:
            send_restock_notification(
                product
            )

            logger.info(
                "Discord restock notification sent | %s",
                product["title"],
            )

        except Exception:
            logger.exception(
                "Could not send Discord restock "
                "notification | product=%s",
                product["title"],
            )

        logger.warning(
            "Opening product in normal browser | "
            "product=%s",
            product["title"],
        )

        try:
            open_product_in_browser(
                product_config
            )

            logger.warning(
                "Product opened in normal browser | "
                "product=%s",
                product["title"],
            )

        except Exception:
            logger.exception(
                "Could not open product in normal browser | "
                "product=%s",
                product["title"],
            )

    elif (
        result["event"]
        == "SOLD_OUT"
    ):
        logger.info(
            "Product sold out | %s",
            product["title"],
        )

    return product


def restart_browser(
    browser,
):
    logger.warning(
        "Restarting Shopee browser"
    )

    try:
        browser.stop()

    except Exception:
        logger.exception(
            "Error while stopping "
            "Shopee browser"
        )

    time.sleep(
        1
    )

    new_browser = (
        ShopeeBrowser()
    )

    new_browser.start()

    logger.info(
        "Shopee browser restarted successfully"
    )

    return new_browser


def check_all_products(
    browser,
    products,
):
    browser_failed = False

    for product_config in products:
        platform = (
            product_config
            .get(
                "platform",
                "",
            )
            .lower()
        )

        try:
            if platform == "shopee":
                check_shopee_product(
                    browser,
                    product_config,
                )

                handle_product_success(
                    product_config
                )

            else:
                logger.warning(
                    "Unsupported platform | "
                    "platform=%s | product=%s",
                    platform,
                    product_config.get(
                        "name"
                    ),
                )

        except Exception as error:
            logger.exception(
                "Product check failed | "
                "product=%s | url=%s",
                product_config.get(
                    "name"
                ),
                product_config.get(
                    "url"
                ),
            )

            handle_product_failure(
                product_config,
                error,
            )

            print()
            print(
                "PRODUCT CHECK FAILED:"
            )

            print(
                type(error).__name__,
                "-",
                error,
            )

            browser_failed = True

    return browser_failed


def main():
    initialize_database()

    logger.info(
        "Restock Monitor started"
    )

    products = (
        load_products()
    )

    logger.info(
        "Tracking %s product(s)",
        len(products),
    )

    browser = (
        ShopeeBrowser()
    )

    try:
        logger.info(
            "Starting persistent "
            "Shopee browser"
        )

        browser.start()

        logger.info(
            "Persistent Shopee "
            "browser started"
        )

        while True:
            cycle_started = (
                time.perf_counter()
            )

            try:
                browser_failed = (
                    check_all_products(
                        browser,
                        products,
                    )
                )

                if browser_failed:
                    try:
                        browser = (
                            restart_browser(
                                browser
                            )
                        )

                    except Exception:
                        logger.exception(
                            "Could not restart "
                            "Shopee browser"
                        )

                        time.sleep(
                            5
                        )

            except Exception:
                logger.exception(
                    "Unexpected monitoring "
                    "cycle failure"
                )

                try:
                    browser = (
                        restart_browser(
                            browser
                        )
                    )

                except Exception:
                    logger.exception(
                        "Emergency browser "
                        "restart failed"
                    )

            cycle_elapsed = (
                time.perf_counter()
                - cycle_started
            )

            check_interval = (
                get_check_interval()
            )

            if (
                check_interval
                == BURST_INTERVAL
            ):
                logger.info(
                    "BURST MODE | "
                    "cycle_duration=%.2fs | "
                    "next check in %s seconds",
                    cycle_elapsed,
                    check_interval,
                )

                print()
                print(
                    "BURST MODE:"
                    f" next check in "
                    f"{check_interval} seconds..."
                )

            else:
                logger.info(
                    "Cycle completed | "
                    "duration=%.2fs | "
                    "next check in %s seconds",
                    cycle_elapsed,
                    check_interval,
                )

                print()
                print(
                    f"Waiting "
                    f"{check_interval} seconds..."
                )

            time.sleep(
                check_interval
            )

    except KeyboardInterrupt:
        logger.info(
            "Restock Monitor "
            "stopped by user"
        )

        print()
        print(
            "Monitor stopped."
        )

    finally:
        logger.info(
            "Stopping Shopee browser"
        )

        try:
            browser.stop()

        except Exception:
            logger.exception(
                "Error while "
                "stopping browser"
            )


if __name__ == "__main__":
    main()
