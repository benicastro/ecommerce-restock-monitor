from state import (
    load_product_state,
    record_product_event,
    save_product_state,
)


def process_product(product):
    previous_state = (
        load_product_state(
            product
        )
    )

    current_available = (
        product["available"]
    )

    if previous_state is None:
        save_product_state(
            product
        )

        record_product_event(
            product,
            "INITIAL",
        )

        return {
            "event": "INITIAL",
            "restocked": False,
        }

    previous_available = (
        previous_state["available"]
    )

    if (
        previous_available is False
        and current_available is True
    ):
        event = "RESTOCK"

    elif (
        previous_available is True
        and current_available is False
    ):
        event = "SOLD_OUT"

    else:
        event = "NO_CHANGE"

    save_product_state(
        product
    )

    if event != "NO_CHANGE":
        record_product_event(
            product,
            event,
        )

    return {
        "event": event,
        "restocked": (
            event == "RESTOCK"
        ),
    }
