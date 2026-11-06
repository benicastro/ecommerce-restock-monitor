# Real-Time E-commerce Restock Monitor

A Windows-focused Python project that monitors Shopee product availability, persists state in SQLite, detects real `OUT OF STOCK -> IN STOCK` transitions, sends Discord alerts, and opens the product in the user's normal Chrome browser.

The project was designed around reliability rather than bypassing anti-bot or verification systems. It does **not** automate checkout, solve CAPTCHA, spoof browser fingerprints, or bypass platform security controls.

## Features

- Shopee product monitoring through the normal product-page response
- Persistent Playwright browser context
- Fresh temporary page for each product check
- SQLite product state and event history
- Genuine restock transition detection
- Discord restock notifications
- Windows sound alert
- Opens the exact product in normal Google Chrome
- Failure counting and Discord health warnings
- Automatic browser restart after failed checks
- Rotating log files
- Normal and burst polling modes
- PID-based minimization of the Playwright window on Windows

## Architecture

```text
products.json
     |
     v
Python monitor
     |
     v
Playwright / Shopee product page
     |
     v
/api/v4/pdp/get_pc response
     |
     v
Shopee parser
     |
     v
SQLite state
     |
     v
State-transition detector
     |
     +---- RESTOCK ----> Discord alert
     |                       |
     |                       v
     +-----------------> Sound + Chrome handoff
```

## Requirements

- Windows 10/11
- Python 3.11+ recommended
- Google Chrome
- Discord webhook
- Playwright Chromium

## Installation

Open PowerShell in the project folder.

### 1. Create a virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
playwright install chromium
```

### 3. Create `.env`

Copy:

```text
.env.example
```

to:

```text
.env
```

Then add your Discord webhook:

```text
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

Never commit `.env`.

### 4. Configure products

`products.json` is a local file and is intentionally ignored by Git.

Example:

```json
{
  "products": [
    {
      "platform": "shopee",
      "name": "Example Product",
      "url": "https://shopee.ph/product/123456789/987654321"
    }
  ]
}
```

You can also copy:

```text
products.example.json
```

to `products.json`.

If a canonical Shopee URL does not produce the product response reliably, paste the exact product URL copied from your browser instead of stripping its query parameters.

## Shopee login profile

Shopee may redirect a fresh Playwright profile to its login page before product data is requested.

If that happens, stop the monitor and run:

```powershell
python shopee_login.py
```

Log into Shopee manually in the opened Chrome-for-Testing window. The script uses the same persistent `browser_profile` as `main.py`, so the authenticated session can be reused by later monitoring runs.

The project does not store credentials in source code and does not bypass CAPTCHA or account verification.

## Running

```powershell
python main.py
```

Or:

```text
run_monitor.bat
```

Typical output:

```text
Restock Monitor started
Tracking 1 product(s)
Starting persistent Shopee browser
Playwright window minimized.

Checking:
https://shopee.ph/product/...

Shopee product data captured!

Product:
Example Product
Available: False
Price: 1099.0
Event: NO_CHANGE
```

## Restock behavior

The first successful observation is stored as `INITIAL`. Unrecognized stock data raises an error instead of being saved as `False`, and captured product IDs are checked against the requested URL.

After that:

```text
False -> False = NO_CHANGE
True  -> True  = NO_CHANGE
True  -> False = SOLD_OUT
False -> True  = RESTOCK
```

Only a real `False -> True` transition produces the restock workflow.

On `RESTOCK`:

```text
Discord notification
        |
        v
Windows sound
        |
        v
Product opens in normal Chrome
        |
        v
User completes purchase manually
```

## Polling

Current defaults in `main.py` (sleep is shortened just before a burst window so the start time is not missed):

```python
NORMAL_INTERVAL = 60
BURST_INTERVAL = 5

BURST_START = datetime_time(15, 35)
BURST_END = datetime_time(15, 45)
```

The burst configuration was originally used around an announced 3:40 PM drop.

The effective check cadence is:

```text
product-check duration + configured sleep
```

For example, a 4-second product check with a 5-second burst sleep gives roughly a 9-second effective cadence.

Avoid making the refresh behavior excessively aggressive. More requests can increase the likelihood of platform verification or failed browser sessions.

## Parser compatibility

Modern `/api/v4/pdp/get_pc` responses can expose shop information in `data.shop_detailed` rather than `data.item.shop_detailed`. The parser supports both layouts and uses the modern shop object first for seller names.

## Database

Runtime state is stored in:

```text
monitor.db
```

Tables:

- `product_state` - current state for each product
- `product_events` - initial/restock/sold-out event history
- `monitor_health` - consecutive failure state

`monitor.db` is intentionally ignored by Git.

## Health monitoring

After five consecutive failures, the monitor sends a Discord warning.

It does not repeatedly spam warnings while the same failure condition continues.

When the monitor recovers, it resets the failure count and sends a recovery message if a warning had previously been sent.

## Logs

Runtime logs are written to:

```text
logs/monitor.log
```

Logs rotate automatically at approximately 5 MB with three backups.

## Important files

```text
main.py                 Main monitoring loop
shopee_browser.py       Persistent Playwright browser + response capture
shopee.py               Shopee response parser
monitor.py              State-transition logic
state.py                SQLite state access
database.py             Database initialization
discord_notifier.py     Discord notifications
handoff.py              Sound + normal Chrome handoff
logger.py               Rotating logging
products.py             Product configuration loader
products.example.json   Safe public configuration example
.env.example            Environment-variable template
run_monitor.bat         Windows launcher
tests/test_core.py       Offline parser and state-transition tests
```

## Security and responsible use

This project intentionally stops short of defeating platform security controls.

It does not:

- bypass CAPTCHA or verification pages
- spoof browser fingerprints
- forge or replay protected security tokens
- automate credentials
- automate final order placement

If Shopee challenges the automated browser, the monitor records a failure and uses its normal recovery logic.

## Portfolio summary

**Python / Playwright / SQLite / Discord / Windows APIs**

Built a real-time e-commerce availability monitor with persistent state, genuine restock-event detection, notification integrations, fault recovery, burst polling, browser handoff, and production-style rotating logs.

## Tests

Run the offline parser and SQLite transition tests before publishing:

```powershell
python -m unittest discover -s tests -v
```

These checks use simulated Shopee responses and a temporary SQLite database. They do not confirm that Shopee will always serve a product page, that Discord is reachable, or that Chrome handoff works on every Windows installation. Real-world end-to-end verification is still required.

## Known limitations

- Shopee can redirect automated browsers to login or verification; this project does not bypass these steps.
- The normal polling and burst intervals are **sleep durations**, not guaranteed end-to-end check frequencies.
- The parser currently reports **listing-level availability**, not a specific variant's availability.
- A Discord webhook failure after a genuine restock is logged, but **that event is not automatically re-sent** in the current architecture. A durable notification outbox would be needed for delivery guarantees.
- Seller names are best-effort and may remain `None` if Shopee omits shop details.
- The project has been tested operationally on one Windows setup; broader compatibility and long-running stability are not yet established.

## GitHub publishing

Before committing, verify that the following are not tracked:

```powershell
git status
git ls-files .env
git ls-files products.json
git ls-files monitor.db
git ls-files browser_profile
git ls-files logs
```

The commands after `git status` should produce no output.

Then:

```powershell
git init
git add .
git commit -m "Initial portfolio release"
```

Create an empty GitHub repository and add it as `origin`.

Example:

```powershell
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/ecommerce-restock-monitor.git
git push -u origin main
```
