import ctypes
import time
from ctypes import wintypes
from pathlib import Path

from playwright.sync_api import (
    sync_playwright,
)


PROFILE_DIR = Path(
    "./browser_profile"
)

TH32CS_SNAPPROCESS = (
    0x00000002
)

SW_MINIMIZE = 6

CAPTURE_TIMEOUT_SECONDS = 30
CAPTURE_POLL_MS = 250


class PROCESSENTRY32W(
    ctypes.Structure
):
    _fields_ = [
        (
            "dwSize",
            wintypes.DWORD,
        ),
        (
            "cntUsage",
            wintypes.DWORD,
        ),
        (
            "th32ProcessID",
            wintypes.DWORD,
        ),
        (
            "th32DefaultHeapID",
            ctypes.c_void_p,
        ),
        (
            "th32ModuleID",
            wintypes.DWORD,
        ),
        (
            "cntThreads",
            wintypes.DWORD,
        ),
        (
            "th32ParentProcessID",
            wintypes.DWORD,
        ),
        (
            "pcPriClassBase",
            ctypes.c_long,
        ),
        (
            "dwFlags",
            wintypes.DWORD,
        ),
        (
            "szExeFile",
            wintypes.WCHAR * 260,
        ),
    ]


def get_process_ids():
    kernel32 = (
        ctypes.windll.kernel32
    )

    snapshot = (
        kernel32
        .CreateToolhelp32Snapshot(
            TH32CS_SNAPPROCESS,
            0,
        )
    )

    if snapshot == -1:
        return set()

    process_ids = set()

    entry = PROCESSENTRY32W()

    entry.dwSize = ctypes.sizeof(
        PROCESSENTRY32W
    )

    success = (
        kernel32
        .Process32FirstW(
            snapshot,
            ctypes.byref(
                entry
            ),
        )
    )

    while success:
        process_ids.add(
            entry.th32ProcessID
        )

        success = (
            kernel32
            .Process32NextW(
                snapshot,
                ctypes.byref(
                    entry
                ),
            )
        )

    kernel32.CloseHandle(
        snapshot
    )

    return process_ids


def minimize_windows_for_processes(
    process_ids,
):
    user32 = (
        ctypes.windll.user32
    )

    minimized = []

    @ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HWND,
        wintypes.LPARAM,
    )
    def enum_callback(
        hwnd,
        _,
    ):
        if not user32.IsWindowVisible(
            hwnd
        ):
            return True

        process_id = (
            wintypes.DWORD()
        )

        user32.GetWindowThreadProcessId(
            hwnd,
            ctypes.byref(
                process_id
            ),
        )

        if (
            process_id.value
            not in process_ids
        ):
            return True

        length = (
            user32
            .GetWindowTextLengthW(
                hwnd
            )
        )

        title = ""

        if length > 0:
            buffer = (
                ctypes
                .create_unicode_buffer(
                    length + 1
                )
            )

            user32.GetWindowTextW(
                hwnd,
                buffer,
                length + 1,
            )

            title = (
                buffer.value
            )

        user32.ShowWindow(
            hwnd,
            SW_MINIMIZE,
        )

        minimized.append(
            (
                hwnd,
                process_id.value,
                title,
            )
        )

        return True

    user32.EnumWindows(
        enum_callback,
        0,
    )

    return minimized


class ShopeeBrowser:
    def __init__(self):
        self.playwright = None
        self.context = None
        self.page = None

    def start(self):
        processes_before = (
            get_process_ids()
        )

        self.playwright = (
            sync_playwright()
            .start()
        )

        self.context = (
            self.playwright
            .chromium
            .launch_persistent_context(
                user_data_dir=str(
                    PROFILE_DIR
                ),
                headless=False,
                viewport={
                    "width": 1400,
                    "height": 900,
                },
            )
        )

        if self.context.pages:
            self.page = (
                self.context.pages[0]
            )
        else:
            self.page = (
                self.context
                .new_page()
            )

        time.sleep(
            2
        )

        processes_after = (
            get_process_ids()
        )

        new_processes = (
            processes_after
            - processes_before
        )

        print(
            "New Playwright process IDs:",
            sorted(
                new_processes
            ),
        )

        minimized = []

        for _ in range(5):
            minimized = (
                minimize_windows_for_processes(
                    new_processes
                )
            )

            if minimized:
                break

            time.sleep(
                0.5
            )

        if minimized:
            print(
                "Playwright window minimized."
            )

            for (
                _,
                process_id,
                title,
            ) in minimized:
                print(
                    "Minimized PID:",
                    process_id,
                    "| title:",
                    title,
                )
        else:
            print(
                "Could not find a visible "
                "Playwright window to minimize."
            )

    def stop(self):
        if self.context is not None:
            try:
                self.context.close()

            except Exception as error:
                print(
                    "Browser context was "
                    "already closed:",
                    type(error).__name__,
                )

        if self.playwright is not None:
            try:
                self.playwright.stop()

            except Exception as error:
                print(
                    "Playwright was "
                    "already stopped:",
                    type(error).__name__,
                )

        self.context = None
        self.playwright = None
        self.page = None

    def fetch_product(
        self,
        product_url,
    ):
        if self.context is None:
            raise RuntimeError(
                "Shopee browser has not "
                "been started."
            )

        captured_data = None

        page = (
            self.context
            .new_page()
        )

        capture_started = (
            time.perf_counter()
        )

        def handle_response(
            response,
        ):
            nonlocal captured_data

            if (
                "/api/v4/pdp/get_pc"
                not in response.url
            ):
                return

            elapsed = (
                time.perf_counter()
                - capture_started
            )

            print(
                "Shopee product response:",
                response.status,
                "| after",
                f"{elapsed:.2f}s",
            )

            if response.status != 200:
                return

            try:
                data = (
                    response.json()
                )

                if (
                    isinstance(
                        data,
                        dict,
                    )
                    and isinstance(
                        data.get("data"),
                        dict,
                    )
                    and isinstance(
                        data["data"].get(
                            "item"
                        ),
                        dict,
                    )
                ):
                    captured_data = (
                        data
                    )

                    print(
                        "Shopee product "
                        "data captured!"
                    )

                    print(
                        "Capture time:",
                        f"{elapsed:.2f}s",
                    )

            except Exception as error:
                print(
                    "Could not parse "
                    "Shopee response:",
                    error,
                )

        page.on(
            "response",
            handle_response,
        )

        print(
            "Opening Shopee..."
        )

        print(
            product_url
        )

        try:
            page.goto(
                product_url,
                wait_until=(
                    "domcontentloaded"
                ),
                timeout=60000,
            )

        except Exception as error:
            print(
                "Navigation warning:",
                error,
            )

        print(
            "Waiting for Shopee product data..."
        )

        max_polls = int(
            (
                CAPTURE_TIMEOUT_SECONDS
                * 1000
            )
            / CAPTURE_POLL_MS
        )

        for _ in range(
            max_polls
        ):
            if (
                captured_data
                is not None
            ):
                break

            page.wait_for_timeout(
                CAPTURE_POLL_MS
            )

        try:
            page.remove_listener(
                "response",
                handle_response,
            )

        except Exception:
            pass

        if captured_data is None:
            total_elapsed = (
                time.perf_counter()
                - capture_started
            )

            try:
                page.close()

            except Exception:
                pass

            raise RuntimeError(
                "Could not capture Shopee "
                "product data after "
                f"{total_elapsed:.2f} seconds."
            )

        try:
            page.close()

        except Exception:
            pass

        return captured_data
