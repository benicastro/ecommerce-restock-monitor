import tempfile
import unittest
from pathlib import Path

import database
from monitor import process_product
from shopee import (
    extract_ids,
    parse_shopee_product,
    validate_target_identity,
)
from state import load_product_state


SHOP_ID = 495485096
ITEM_ID = 42583983597


def response(*, stock_display=None, stock=None, models=None, seller=None):
    item = {
        "shopid": SHOP_ID,
        "itemid": ITEM_ID,
        "name": "Example monitored item",
        "price": 149900000,
    }
    if stock_display is not None:
        item["stock_display"] = stock_display
    if stock is not None:
        item["stock"] = stock
    if models is not None:
        item["models"] = models
    data = {"item": item}
    if seller is not None:
        data["shop_detailed"] = {"name": seller}
    return {"data": data}


class ParserTests(unittest.TestCase):
    def test_seller_and_price(self):
        value = parse_shopee_product(
            response(stock_display="OUT OF STOCK", seller="TOMY PH")
        )
        self.assertEqual(value["seller"], "TOMY PH")
        self.assertEqual(value["price"], 1499.0)
        self.assertIs(value["available"], False)

    def test_model_in_stock(self):
        value = parse_shopee_product(
            response(models=[{"modelid": 7, "has_stock": True}])
        )
        self.assertIs(value["available"], True)

    def test_model_false_string_not_true(self):
        value = parse_shopee_product(
            response(models=[{"has_stock": "false"}])
        )
        self.assertIs(value["available"], False)

    def test_numeric_stock_zero(self):
        value = parse_shopee_product(response(stock=0))
        self.assertIs(value["available"], False)

    def test_missing_stock_raises(self):
        with self.assertRaisesRegex(RuntimeError, "no reliable stock"):
            parse_shopee_product(response())

    def test_unknown_model_stock_raises(self):
        with self.assertRaisesRegex(RuntimeError, "no reliable stock"):
            parse_shopee_product(response(models=[{"name": "unknown"}]))

    def test_wrong_item_rejected(self):
        value = parse_shopee_product(response(stock_display="OUT OF STOCK"))
        with self.assertRaisesRegex(RuntimeError, "wrong product"):
            validate_target_identity(
                value,
                f"https://shopee.ph/product/{SHOP_ID}/999999999",
            )

    def test_two_url_styles(self):
        url1 = f"https://shopee.ph/product/{SHOP_ID}/{ITEM_ID}?foo=bar"
        url2 = f"https://shopee.ph/my-item-i.{SHOP_ID}.{ITEM_ID}?foo=bar"
        self.assertEqual(extract_ids(url1), (SHOP_ID, ITEM_ID))
        self.assertEqual(extract_ids(url2), (SHOP_ID, ITEM_ID))


class StateTransitionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_database_file = database.DATABASE_FILE
        database.DATABASE_FILE = Path(self.temp_dir.name) / "monitor.db"
        database.initialize_database()
        self.product = parse_shopee_product(
            response(stock_display="OUT OF STOCK")
        )

    def tearDown(self):
        database.DATABASE_FILE = self.old_database_file
        self.temp_dir.cleanup()

    def test_restock_and_sold_out_events(self):
        self.assertEqual(process_product(self.product)["event"], "INITIAL")
        self.assertEqual(process_product(self.product)["event"], "NO_CHANGE")

        self.product["available"] = True
        self.assertEqual(process_product(self.product)["event"], "RESTOCK")
        self.assertEqual(process_product(self.product)["event"], "NO_CHANGE")

        self.product["available"] = False
        self.assertEqual(process_product(self.product)["event"], "SOLD_OUT")
        self.assertIs(load_product_state(self.product)["available"], False)

        self.product["available"] = True
        self.assertEqual(process_product(self.product)["event"], "RESTOCK")

    def test_bad_response_does_not_replace_database_state(self):
        process_product(self.product)
        with self.assertRaises(RuntimeError):
            parse_shopee_product(response())
        self.assertIs(load_product_state(self.product)["available"], False)


if __name__ == "__main__":
    unittest.main()
