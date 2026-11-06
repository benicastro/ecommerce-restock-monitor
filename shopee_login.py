from pathlib import Path

from playwright.sync_api import sync_playwright

from products import load_products


PROFILE_DIR = Path("./browser_profile")
PAGE_LOAD_TIMEOUT_MS = 60000


def find_shopee_product():
    products = load_products()

    for product in products:
        if (
            product
            .get("platform", "")
            .lower()
            == "shopee"
        ):
            return product

    raise RuntimeError(
        "No Shopee product was found in products.json."
    )


def looks_like_login(url):
    url = url.lower()

    return (
        "/login" in url
        or "/buyer/login" in url
    )


def looks_like_verification(url):
    url = url.lower()

    return (
        "/verify/" in url
        or "/captcha" in url
    )


def main():
    product = find_shopee_product()
    product_url = product["url"]

    PROFILE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=====================================")
    print(" SHOPEE MONITOR LOGIN SETUP")
    print("=====================================")
    print()
    print(
        "This opens the same browser profile used by main.py."
    )
    print(
        "Log into Shopee manually. Credentials are not stored in this script."
    )
    print()

    with sync_playwright() as playwright:
        context = (
            playwright.chromium
            .launch_persistent_context(
                user_data_dir=str(PROFILE_DIR),
                headless=False,
                viewport={
                    "width": 1400,
                    "height": 900,
                },
            )
        )

        if context.pages:
            page = context.pages[0]
        else:
            page = context.new_page()

        try:
            try:
                page.goto(
                    product_url,
                    wait_until="domcontentloaded",
                    timeout=PAGE_LOAD_TIMEOUT_MS,
                )
            except Exception as error:
                print(
                    "Navigation warning:",
                    error,
                )

            print()
            print(
                "Log in manually, complete any normal Shopee verification, "
                "and navigate back to the target product."
            )
            print()

            input(
                "When the product page is visible, press ENTER here..."
            )

            final_url = page.url

            if looks_like_verification(final_url):
                print()
                print(
                    "Shopee is still showing a verification page."
                )
            elif looks_like_login(final_url):
                print()
                print(
                    "Shopee is still showing the login page."
                )
            else:
                print()
                print(
                    "Login session appears to be saved successfully."
                )
                print()
                print("You can now run:")
                print()
                print("python main.py")

            print()
            input(
                "Press ENTER to save the profile and close..."
            )

        finally:
            context.close()


if __name__ == "__main__":
    main()
