import os
import subprocess
import time
import winsound
from pathlib import Path


CHROME_PATHS = [
    Path(
        r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    ),
    Path(
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ),
    Path(
        os.path.expandvars(
            r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
        )
    ),
]


def find_chrome():
    for path in CHROME_PATHS:
        if path.exists():
            return path

    raise RuntimeError(
        "Google Chrome could not be found."
    )


def play_restock_alert():
    for _ in range(3):
        winsound.MessageBeep(
            winsound.MB_ICONEXCLAMATION
        )

        time.sleep(
            0.25
        )


def open_product_in_browser(
    product_config,
):
    product_url = product_config.get(
        "url"
    )

    if not product_url:
        raise RuntimeError(
            "Product URL is missing "
            "from products.json."
        )

    chrome_path = (
        find_chrome()
    )

    play_restock_alert()

    subprocess.Popen(
        [
            str(chrome_path),
            "--new-tab",
            product_url,
        ]
    )

    print(
        "Opened product in Chrome:",
        product_url,
    )
