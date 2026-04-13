import argparse
import csv
import json
import logging
import os
import random
import re
import time
from datetime import datetime
from urllib.error import URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

load_dotenv()  # reads .env file from current directory

try:
    from camoufox.sync_api import Camoufox
except ImportError:
    Camoufox = None  # allow running in --test mode without camoufox

SCREENSHOTS_DIR = "screenshots"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# --- logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scraper.log"),
    ],
)
log = logging.getLogger(__name__)

# --- telegram config (loaded from .env) ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- price alert config ---
PRICE_CHANGE_THRESHOLD = 0.15  # 15% change (drop or raise) triggers alert

# --- config ---
URLS = [
    "https://www.amazon.com/WUNGY-Cosplay-Costume-Uniform-costume/dp/B0FCMM85GN/ref=sr_1_42?crid=193JX6Y4709MN&dib=eyJ2IjoiMSJ9.fTsQ0ZrE5hMdjieKIFfBpb2-i_z65McDGBfCz0vigpWx0_nMZLUG4uoXjzroxkRH9GDEyfWkrJu8stbDJVS7R_2EapW_LzrTe8_0ZadHzjw0vg9KbvrBURaoojT46qxzroqXMr3VoHO2FfNYij0Q-4KmocSG7p-0WZkeSFbbL9cW8Ub710fP_Yv-ArYq89mfnkG6NRyAWUReg5TFEru3TmfVxHqjqKghiwK8PFLLzavegDMrBkOoVbHeR-HihAMiI05KzQb9QRkMvDxz0-wTnrx0QNsEPP2Cb3PWSOmHXhw.6g1I3Qy2u-BVefGXKjbupji7IWfutM_uVn7Ko6wU1jI&dib_tag=se&keywords=cosplay&qid=1775725306&sprefix=cospla%2Caps%2C260&sr=8-42&th=1&psc=1",
    "https://www.amazon.com/Women-Thigh-Socks-Warmer-Stockings/dp/B074TDRF5B/ref=sr_1_14?crid=193JX6Y4709MN&dib=eyJ2IjoiMSJ9.fTsQ0ZrE5hMdjieKIFfBpb2-i_z65McDGBfCz0vigpWx0_nMZLUG4uoXjzroxkRH9GDEyfWkrJu8stbDJVS7R_2EapW_LzrTe8_0ZadHzjw0vg9KbvrBURaoojT46qxzroqXMr3VoHO2FfNYij0Q-4KmocSG7p-0WZkeSFbbL9cW8Ub710fP_Yv-ArYq89mfnkG6NRyAWUReg5TFEru3TmfVxHqjqKghiwK8PFLLzavegDMrBkOoVbHeR-HihAMiI05KzQb9QRkMvDxz0-wTnrx0QNsEPP2Cb3PWSOmHXhw.6g1I3Qy2u-BVefGXKjbupji7IWfutM_uVn7Ko6wU1jI&dib_tag=se&keywords=cosplay&qid=1775725306&sprefix=cospla%2Caps%2C260&sr=8-14&th=1&psc=1",
    "https://www.amazon.com/MEOWCOS-Bodysuit-Onesie-Pajamas-Romper/dp/B0CT2N8L5F/ref=sr_1_28?crid=193JX6Y4709MN&dib=eyJ2IjoiMSJ9.fTsQ0ZrE5hMdjieKIFfBpb2-i_z65McDGBfCz0vigpWx0_nMZLUG4uoXjzroxkRH9GDEyfWkrJu8stbDJVS7R_2EapW_LzrTe8_0ZadHzjw0vg9KbvrBURaoojT46qxzroqXMr3VoHO2FfNYij0Q-4KmocSG7p-0WZkeSFbbL9cW8Ub710fP_Yv-ArYq89mfnkG6NRyAWUReg5TFEru3TmfVxHqjqKghiwK8PFLLzavegDMrBkOoVbHeR-HihAMiI05KzQb9QRkMvDxz0-wTnrx0QNsEPP2Cb3PWSOmHXhw.6g1I3Qy2u-BVefGXKjbupji7IWfutM_uVn7Ko6wU1jI&dib_tag=se&keywords=cosplay&qid=1775725306&sprefix=cospla%2Caps%2C260&sr=8-28&th=1&psc=1",
    "https://www.amazon.com/Cosplay-fm-Cosplay-Printed-Bodysuit-Costume/dp/B07Z8ZBXPH/ref=sr_1_34?crid=193JX6Y4709MN&dib=eyJ2IjoiMSJ9.fTsQ0ZrE5hMdjieKIFfBpb2-i_z65McDGBfCz0vigpWx0_nMZLUG4uoXjzroxkRH9GDEyfWkrJu8stbDJVS7R_2EapW_LzrTe8_0ZadHzjw0vg9KbvrBURaoojT46qxzroqXMr3VoHO2FfNYij0Q-4KmocSG7p-0WZkeSFbbL9cW8Ub710fP_Yv-ArYq89mfnkG6NRyAWUReg5TFEru3TmfVxHqjqKghiwK8PFLLzavegDMrBkOoVbHeR-HihAMiI05KzQb9QRkMvDxz0-wTnrx0QNsEPP2Cb3PWSOmHXhw.6g1I3Qy2u-BVefGXKjbupji7IWfutM_uVn7Ko6wU1jI&dib_tag=se&keywords=cosplay&qid=1775725306&sprefix=cospla%2Caps%2C260&sr=8-34&th=1&psc=1",
    "https://www.amazon.com/KORURACLUB-gradient-halloween-accessories-included/dp/B0FPCNKT9X/ref=sr_1_32?crid=193JX6Y4709MN&dib=eyJ2IjoiMSJ9.fTsQ0ZrE5hMdjieKIFfBpb2-i_z65McDGBfCz0vigpWx0_nMZLUG4uoXjzroxkRH9GDEyfWkrJu8stbDJVS7R_2EapW_LzrTe8_0ZadHzjw0vg9KbvrBURaoojT46qxzroqXMr3VoHO2FfNYij0Q-4KmocSG7p-0WZkeSFbbL9cW8Ub710fP_Yv-ArYq89mfnkG6NRyAWUReg5TFEru3TmfVxHqjqKghiwK8PFLLzavegDMrBkOoVbHeR-HihAMiI05KzQb9QRkMvDxz0-wTnrx0QNsEPP2Cb3PWSOmHXhw.6g1I3Qy2u-BVefGXKjbupji7IWfutM_uVn7Ko6wU1jI&dib_tag=se&keywords=cosplay&qid=1775725306&sprefix=cospla%2Caps%2C260&sr=8-32&th=1",
    "https://www.amazon.com/Ruocealya-Virgin-Killer-Backless-Sweater-Set/dp/B0GJ5GCZMC/ref=sr_1_48?crid=193JX6Y4709MN&dib=eyJ2IjoiMSJ9.fTsQ0ZrE5hMdjieKIFfBpb2-i_z65McDGBfCz0vigpWx0_nMZLUG4uoXjzroxkRH9GDEyfWkrJu8stbDJVS7R_2EapW_LzrTe8_0ZadHzjw0vg9KbvrBURaoojT46qxzroqXMr3VoHO2FfNYij0Q-4KmocSG7p-0WZkeSFbbL9cW8Ub710fP_Yv-ArYq89mfnkG6NRyAWUReg5TFEru3TmfVxHqjqKghiwK8PFLLzavegDMrBkOoVbHeR-HihAMiI05KzQb9QRkMvDxz0-wTnrx0QNsEPP2Cb3PWSOmHXhw.6g1I3Qy2u-BVefGXKjbupji7IWfutM_uVn7Ko6wU1jI&dib_tag=se&keywords=cosplay&qid=1775725306&sprefix=cospla%2Caps%2C260&sr=8-48&th=1",
    "https://www.amazon.com/Charmnight-Fishnet-Stockings-Pantyhose-Black-g5/dp/B07NV4JGTG/ref=sr_1_8?crid=193JX6Y4709MN&dib=eyJ2IjoiMSJ9.fTsQ0ZrE5hMdjieKIFfBpb2-i_z65McDGBfCz0vigpWx0_nMZLUG4uoXjzroxkRH9GDEyfWkrJu8stbDJVS7R_2EapW_LzrTe8_0ZadHzjw0vg9KbvrBURaoojT46qxzroqXMr3VoHO2FfNYij0Q-4KmocSG7p-0WZkeSFbbL9cW8Ub710fP_Yv-ArYq89mfnkG6NRyAWUReg5TFEru3TmfVxHqjqKghiwK8PFLLzavegDMrBkOoVbHeR-HihAMiI05KzQb9QRkMvDxz0-wTnrx0QNsEPP2Cb3PWSOmHXhw.6g1I3Qy2u-BVefGXKjbupji7IWfutM_uVn7Ko6wU1jI&dib_tag=se&keywords=cosplay&qid=1775725306&sprefix=cospla%2Caps%2C260&sr=8-8&th=1&psc=1",
]

CSV_PATH = "prices.csv"
DUMMY_CSV_PATH = "dummy_prices.csv"
POLL_INTERVAL = 60 * 30  # 30 minutes between cycles
PAGE_TIMEOUT = 30_000  # ms to wait for price element
PAGE_WAIT_MIN = 2  # seconds between pages
PAGE_WAIT_MAX = 5
MAX_RETRIES = 3  # per-page retry attempts
RETRY_DELAYS = [5, 15, 30]  # seconds between retries


# =====================================================================
#  TELEGRAM NOTIFICATIONS
# =====================================================================


def send_telegram(message: str) -> bool:
    """Send a message via Telegram Bot API. Returns True on success."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning(
            "[telegram] Bot token or chat ID not configured — printing message instead:"
        )
        log.warning(f"[telegram] {message}")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps(
        {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
    ).encode("utf-8")

    req = Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )

    try:
        with urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                log.info("[telegram] Alert sent successfully")
                return True
            else:
                log.error(f"[telegram] Unexpected status: {resp.status}")
                return False
    except URLError as e:
        log.error(f"[telegram] Failed to send message: {e}")
        return False


def get_historical_prices(asin: str, csv_path: str = CSV_PATH) -> list[float]:
    """Read all past prices for an ASIN from the CSV."""
    try:
        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)
            return [
                float(row["price"])
                for row in reader
                if row["asin"] == asin and row["price"]
            ]
    except FileNotFoundError:
        return []


def check_price_alert(
    asin: str, current_price: float, url: str, csv_path: str = CSV_PATH
):
    """
    Compare current price against historical min and max from the CSV.
    If price dropped >= threshold from the max  → drop alert.
    If price raised >= threshold from the min  → raise alert.
    """
    prices = get_historical_prices(asin, csv_path)

    if not prices:
        log.info(f"[alert] {asin}: no price history yet — skipping alert check")
        return

    hist_max = max(prices)
    hist_min = min(prices)

    # --- check for drop (current vs historical max) ---
    if hist_max > 0:
        drop_pct = (hist_max - current_price) / hist_max
        if drop_pct >= PRICE_CHANGE_THRESHOLD:
            log.info(
                f"[alert] {asin}: price dropped {drop_pct:.1%} — ${hist_max:.2f} → ${current_price:.2f}"
            )
            message = (
                f"🔥 <b>Price Drop Alert!</b>\n\n"
                f"ASIN: <code>{asin}</code>\n"
                f"Previous high: <b>${hist_max:.2f}</b>\n"
                f"Now: <b>${current_price:.2f}</b>\n"
                f"Drop: <b>-{drop_pct:.1%}</b>\n\n"
                f'<a href="https://www.amazon.com/dp/{asin}">View on Amazon</a>'
            )
            send_telegram(message)
            return

    # --- check for raise (current vs historical min) ---
    if hist_min > 0:
        raise_pct = (current_price - hist_min) / hist_min
        if raise_pct >= PRICE_CHANGE_THRESHOLD:
            log.info(
                f"[alert] {asin}: price raised {raise_pct:.1%} — ${hist_min:.2f} → ${current_price:.2f}"
            )
            message = (
                f"📈 <b>Price Raise Alert!</b>\n\n"
                f"ASIN: <code>{asin}</code>\n"
                f"Previous low: <b>${hist_min:.2f}</b>\n"
                f"Now: <b>${current_price:.2f}</b>\n"
                f"Raise: <b>+{raise_pct:.1%}</b>\n\n"
                f'<a href="https://www.amazon.com/dp/{asin}">View on Amazon</a>'
            )
            send_telegram(message)
            return

    log.debug(
        f"[alert] {asin}: price within {PRICE_CHANGE_THRESHOLD:.0%} threshold, no alert"
    )


# =====================================================================
#  TEST MODE — run notification logic against dummy_prices.csv
# =====================================================================


def generate_dummy_csv(path: str = DUMMY_CSV_PATH):
    """Create a sample dummy_prices.csv for testing alerts."""
    rows = [
        # ASIN, URL, historical high price, timestamp
        {
            "asin": "B0FCMM85GN",
            "url": "https://www.amazon.com/dp/B0FCMM85GN",
            "price": "29.99",
            "timestamp": "2025-01-01T00:00:00",
        },
        {
            "asin": "B0FCMM85GN",
            "url": "https://www.amazon.com/dp/B0FCMM85GN",
            "price": "32.50",
            "timestamp": "2025-01-15T00:00:00",
        },
        {
            "asin": "B074TDRF5B",
            "url": "https://www.amazon.com/dp/B074TDRF5B",
            "price": "12.99",
            "timestamp": "2025-01-01T00:00:00",
        },
        {
            "asin": "B074TDRF5B",
            "url": "https://www.amazon.com/dp/B074TDRF5B",
            "price": "14.50",
            "timestamp": "2025-01-15T00:00:00",
        },
        {
            "asin": "B07NV4JGTG",
            "url": "https://www.amazon.com/dp/B07NV4JGTG",
            "price": "9.99",
            "timestamp": "2025-01-01T00:00:00",
        },
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["asin", "url", "price", "timestamp"])
        writer.writeheader()
        writer.writerows(rows)
    log.info(f"[test] Generated {path} with {len(rows)} rows")


def run_test_mode():
    """
    Simulate price checks against dummy_prices.csv.
    Fakes "current" prices that trigger drop / raise / no alert.
    """
    log.info("=" * 50)
    log.info("RUNNING IN TEST MODE — no browser, no scraping")
    log.info("=" * 50)

    if not os.path.exists(DUMMY_CSV_PATH):
        log.info(f"[test] {DUMMY_CSV_PATH} not found — generating sample data...")
        generate_dummy_csv()

    # simulated current prices: some trigger alerts, some don't
    fake_current_prices = [
        # 15.4% drop from max $32.50 → SHOULD trigger drop alert
        {
            "asin": "B0FCMM85GN",
            "price": 27.50,
            "url": "https://www.amazon.com/dp/B0FCMM85GN",
        },
        # 31% drop from max $14.50 → SHOULD trigger drop alert
        {
            "asin": "B074TDRF5B",
            "price": 10.00,
            "url": "https://www.amazon.com/dp/B074TDRF5B",
        },
        # 5% drop from max $9.99 → should NOT trigger (within threshold)
        {
            "asin": "B07NV4JGTG",
            "price": 9.49,
            "url": "https://www.amazon.com/dp/B07NV4JGTG",
        },
        # 20% raise from min $9.99 → SHOULD trigger raise alert
        {
            "asin": "B07NV4JGTG_RAISE",
            "price": 11.99,
            "url": "https://www.amazon.com/dp/B07NV4JGTG",
        },
    ]

    # inject an extra row into dummy CSV for the raise test case
    _ensure_raise_test_row()

    log.info(
        f"[test] Checking {len(fake_current_prices)} simulated prices against {DUMMY_CSV_PATH}..."
    )
    log.info(
        f"[test] Threshold: {PRICE_CHANGE_THRESHOLD:.0%} change from historical min/max\n"
    )

    for item in fake_current_prices:
        asin = item["asin"]
        # for the raise test, use the real ASIN in the CSV
        lookup_asin = "B07NV4JGTG" if asin == "B07NV4JGTG_RAISE" else asin
        price = item["price"]
        prices = get_historical_prices(lookup_asin, csv_path=DUMMY_CSV_PATH)
        hist_max = max(prices) if prices else 0
        hist_min = min(prices) if prices else 0

        log.info(
            f"[test] {lookup_asin}: min=${hist_min:.2f}, max=${hist_max:.2f}, now=${price:.2f}"
        )
        check_price_alert(lookup_asin, price, item["url"], csv_path=DUMMY_CSV_PATH)
        print()  # blank line for readability

    log.info("[test] Test mode complete.")


def _ensure_raise_test_row():
    """Add a low-price row for B07NV4JGTG so the raise test works."""
    try:
        with open(DUMMY_CSV_PATH, "r") as f:
            content = f.read()
        if "B07NV4JGTG" in content and content.count("B07NV4JGTG") < 2:
            with open(DUMMY_CSV_PATH, "a", newline="") as f:
                writer = csv.DictWriter(
                    f, fieldnames=["asin", "url", "price", "timestamp"]
                )
                writer.writerow(
                    {
                        "asin": "B07NV4JGTG",
                        "url": "https://www.amazon.com/dp/B07NV4JGTG",
                        "price": "9.99",
                        "timestamp": "2025-02-01T00:00:00",
                    }
                )
    except FileNotFoundError:
        pass


# =====================================================================
#  ORIGINAL HELPERS (unchanged)
# =====================================================================


def extract_asin(url: str) -> str:
    match = re.search(r"/dp/([A-Z0-9]{10})", url)
    if not match:
        raise ValueError(f"No ASIN found in URL: {url}")
    return match.group(1)


def clean_url(url: str) -> str:
    return url


def extract_slug(url: str) -> str:
    match = re.search(r"amazon\.com/([^/]+)/dp/", url)
    if match:
        return match.group(1).replace("-", " ")
    return extract_asin(url)


def navigate_via_search(page, url: str) -> bool:
    asin = extract_asin(url)
    slug = extract_slug(url)
    log.info(f"[{asin}] Navigating via search: '{slug}'")

    try:
        page.goto("https://www.amazon.com", wait_until="domcontentloaded")
        page.wait_for_timeout(random.randint(1500, 3000))
        handle_interstitial(page)

        search_box = page.query_selector("#twotabsearchtextbox")
        if not search_box:
            log.warning(
                f"[{asin}] Search box not found — falling back to direct navigation"
            )
            return False

        search_box.click()
        page.wait_for_timeout(random.randint(200, 500))
        page.keyboard.press("Control+A")

        for char in slug:
            page.keyboard.type(char)
            page.wait_for_timeout(random.randint(30, 100))

        page.wait_for_timeout(random.randint(400, 800))
        page.keyboard.press("Enter")
        page.wait_for_timeout(random.randint(2000, 3500))
        handle_interstitial(page)

        log.info(f"[{asin}] Looking for ASIN in search results...")
        found = page.evaluate(f"""
            () => {{
                const card = document.querySelector('[data-asin="{asin}"]');
                if (!card) return false;
                const link = card.querySelector('a[href*="/dp/{asin}"], h2 a, .a-link-normal');
                if (link) {{
                    link.click();
                    return true;
                }}
                return false;
            }}
        """)

        if not found:
            log.warning(
                f"[{asin}] ASIN not found in search results — falling back to direct navigation"
            )
            return False

        page.wait_for_timeout(random.randint(2000, 3500))
        handle_interstitial(page)

        if asin in page.url:
            log.info(f"[{asin}] Successfully landed on product page via search")
            return True
        else:
            log.warning(f"[{asin}] Landed on wrong page: {page.url}")
            return False

    except Exception as e:
        log.warning(f"[{asin}] Search navigation failed: {e}")
        return False


def append_to_csv(row: dict, path: str = CSV_PATH):
    try:
        with open(path, "r") as f:
            write_header = f.read(1) == ""
    except FileNotFoundError:
        write_header = True

    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["asin", "url", "price", "timestamp"])
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def is_404(page) -> bool:
    try:
        return page.evaluate("""
            () => {
                const title = document.title.toLowerCase();
                const body   = document.body?.innerText?.toLowerCase() || "";
                return (
                    title.includes("page not found") ||
                    title.includes("looking for something") ||
                    body.includes("isn't available") ||
                    body.includes("we couldn't find that page") ||
                    document.querySelector("#error-page") !== null
                );
            }
        """)
    except Exception:
        return False


def is_captcha(page) -> bool:
    try:
        return page.evaluate("""
            () => {
                const title = document.title.toLowerCase();
                const body   = document.body?.innerText?.toLowerCase() || "";
                return (
                    title.includes("robot check") ||
                    body.includes("enter the characters you see below") ||
                    body.includes("type the characters")
                );
            }
        """)
    except Exception:
        return False


def is_bot_page(page) -> bool:
    try:
        return page.evaluate("""
            () => {
                const body = document.body?.innerText?.toLowerCase() || "";
                return body.includes("secure transaction") && !body.includes("add to cart");
            }
        """)
    except Exception:
        return False


def handle_interstitial(page) -> bool:
    try:
        clicked = page.evaluate("""
            () => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const btn = buttons.find(b => b.textContent.trim() === 'Continue shopping');
                if (btn) {
                    btn.click();
                    return true;
                }
                return false;
            }
        """)

        if clicked:
            log.warning("Interstitial: clicked 'Continue shopping' via JS")
            page.wait_for_timeout(random.randint(2000, 4000))
            return True
        else:
            log.debug("Interstitial: button not present on this page")

    except Exception as e:
        log.warning(f"Interstitial handler error: {e}")

    return False


def human_behavior(page):
    page.mouse.move(random.randint(100, 800), random.randint(100, 400))
    page.wait_for_timeout(random.randint(500, 1200))
    page.mouse.wheel(0, random.randint(200, 500))
    page.wait_for_timeout(random.randint(800, 1800))
    page.mouse.move(random.randint(200, 900), random.randint(200, 600))
    page.wait_for_timeout(random.randint(400, 900))


def is_on_product_page(page, asin: str) -> bool:
    try:
        return page.evaluate(f"""
            () => {{
                return (
                    window.location.href.includes('/dp/{asin}') &&
                    document.querySelector('#dp') !== null
                );
            }}
        """)
    except Exception:
        return False


def click_asin_on_page(page, asin: str) -> bool:
    try:
        clicked = page.evaluate(f"""
            () => {{
                const links = Array.from(document.querySelectorAll('a[href*="/dp/{asin}"]'));
                if (links.length > 0) {{
                    links[0].click();
                    return true;
                }}
                const card = document.querySelector('[data-asin="{asin}"]');
                if (card) {{
                    const link = card.querySelector('a');
                    if (link) {{ link.click(); return true; }}
                }}
                return false;
            }}
        """)
        if clicked:
            log.info(f"[{asin}] Found and clicked ASIN link on redirect page")
        return bool(clicked)
    except Exception as e:
        log.warning(f"[{asin}] click_asin_on_page error: {e}")
        return False


# --- core scrape with retry (now calls check_price_alert) ---


def scrape_with_retry(page, url: str) -> dict | None:
    asin = extract_asin(url)
    curl = clean_url(url)

    for attempt in range(1, MAX_RETRIES + 1):
        log.info(f"[{asin}] Attempt {attempt}/{MAX_RETRIES} — navigating...")

        try:
            landed = navigate_via_search(page, url)
            if not landed:
                log.info(f"[{asin}] Falling back to direct URL navigation...")
                page.goto(
                    f"https://www.amazon.com/dp/{asin}/?th=1&psc=1",
                    wait_until="domcontentloaded",
                )
                page.wait_for_timeout(random.randint(2000, 4000))
                handle_interstitial(page)

            if not is_on_product_page(page, asin):
                log.warning(f"[{asin}] Not on product page — scanning for ASIN link...")
                clicked = click_asin_on_page(page, asin)
                if clicked:
                    page.wait_for_timeout(random.randint(2000, 3500))
                    handle_interstitial(page)
                    if not is_on_product_page(page, asin):
                        raise ValueError(
                            "Still not on product page after clicking ASIN link"
                        )
                    log.info(f"[{asin}] Recovered — now on product page")
                else:
                    raise ValueError("Redirected to wrong page, ASIN link not found")

            if is_404(page):
                log.error(
                    f"[{asin}] 404 — product page not found, ASIN may be delisted. Skipping permanently."
                )
                return None

            if is_captcha(page):
                log.warning(
                    f"[{asin}] Captcha detected — skipping this cycle, will retry next cycle."
                )
                return None

            if is_bot_page(page):
                log.warning(
                    f"[{asin}] Bot detection page — applying human behavior and retrying."
                )
                human_behavior(page)
                raise ValueError("Bot page detected")

            human_behavior(page)

            log.info(f"[{asin}] Waiting for price element...")
            try:
                page.wait_for_selector(f'li[data-asin="{asin}"]', timeout=PAGE_TIMEOUT)
            except Exception:
                log.warning(f"[{asin}] Price element did not appear within timeout.")
                out_of_stock = page.evaluate("""
                    () => {
                        const body = document.body?.innerText?.toLowerCase() || "";
                        return (
                            body.includes("currently unavailable") ||
                            body.includes("this item is currently unavailable") ||
                            body.includes("temporarily out of stock")
                        );
                    }
                """)
                if out_of_stock:
                    log.warning(
                        f"[{asin}] Product is out of stock / unavailable — no price to record."
                    )
                    return None
                raise TimeoutError("Price element timeout")

            price = page.evaluate(f"""
                () => {{
                    const el = document.querySelector('li[data-asin="{asin}"]');
                    if (!el) return null;
                    const match = el.textContent.match(/\\$[\\d,]+\\.?\\d*/);
                    return match ? parseFloat(match[0].replace('$', '').replace(',', '')) : null;
                }}
            """)

            if price is None:
                log.warning(f"[{asin}] Element found but no price text inside.")
                raise ValueError("Price text missing from element")

            log.info(f"[{asin}] ✓ Price: ${price}")

            # >>> CHECK FOR PRICE ALERT BEFORE saving to CSV <<<
            check_price_alert(asin, price, curl)

            return {
                "asin": asin,
                "url": curl,
                "price": price,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            log.error(f"[{asin}] Attempt {attempt} failed: {e}")
            if attempt < MAX_RETRIES:
                wait = RETRY_DELAYS[attempt - 1]
                log.info(f"[{asin}] Retrying in {wait}s...")
                time.sleep(wait)
            else:
                log.error(
                    f"[{asin}] All {MAX_RETRIES} attempts failed — giving up this cycle."
                )
                save_failure_screenshot(page, asin, str(e))

    return None


def save_failure_screenshot(page, asin: str, reason: str = ""):
    try:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        base_name = f"{ts}_{asin}"
        screenshot_path = os.path.join(SCREENSHOTS_DIR, f"{base_name}.png")
        page.screenshot(path=screenshot_path, full_page=True)
        log.info(f"[{asin}] Screenshot saved: {screenshot_path}")

        if reason:
            reason_path = os.path.join(SCREENSHOTS_DIR, f"{base_name}.txt")
            with open(reason_path, "w") as f:
                f.write(f"ASIN: {asin}\n")
                f.write(f"Timestamp: {ts}\n")
                f.write(f"URL: {page.url}\n")
                f.write(f"Reason: {reason}\n")
            log.info(f"[{asin}] Failure reason saved: {reason_path}")

    except Exception as screenshot_err:
        log.warning(f"[{asin}] Could not save screenshot: {screenshot_err}")


# --- session warmup ---

WARMUP_SEARCHES = [
    "cosplay costume",
    "anime clothing women",
    "thigh high socks",
    "halloween costume women",
    "bodysuit women",
    "lingerie set",
    "women fashion top",
]

browser_ref = [None]


def search_and_browse(page, query: str):
    log.info(f"[warmup] Searching for: '{query}'")
    tab = browser_ref[0].new_page(
        viewport={"width": 1920, "height": 1080}, locale="en-US"
    )
    try:
        tab.goto("https://www.amazon.com", wait_until="domcontentloaded")
        tab.wait_for_timeout(random.randint(1500, 3000))
        handle_interstitial(tab)

        tab.click("#twotabsearchtextbox")
        tab.wait_for_timeout(random.randint(300, 700))
        for char in query:
            tab.keyboard.type(char)
            tab.wait_for_timeout(random.randint(50, 150))

        tab.wait_for_timeout(random.randint(500, 1000))
        tab.keyboard.press("Enter")
        tab.wait_for_timeout(random.randint(2000, 4000))
        handle_interstitial(tab)

        for _ in range(random.randint(3, 6)):
            tab.mouse.wheel(0, random.randint(200, 400))
            tab.wait_for_timeout(random.randint(600, 1400))

        for _ in range(random.randint(2, 3)):
            tab.mouse.move(random.randint(200, 1400), random.randint(200, 700))
            tab.wait_for_timeout(random.randint(400, 800))

        tab.wait_for_timeout(random.randint(1500, 2500))
        log.info(f"[warmup] Done browsing search results for: '{query}'")

    except Exception as e:
        log.warning(f"[warmup] Search browse failed for '{query}': {e}")


def warmup_session(browser):
    browser_ref[0] = browser
    log.info("[warmup] Starting session warmup...")

    main_page = browser.new_page(
        viewport={"width": 1920, "height": 1080}, locale="en-US"
    )
    try:
        log.info("[warmup] Visiting Amazon homepage...")
        main_page.goto(
            "https://www.amazon.com/ref=nav_logo", wait_until="domcontentloaded"
        )
        main_page.wait_for_timeout(random.randint(2000, 4000))
        handle_interstitial(main_page)

        for _ in range(random.randint(2, 4)):
            main_page.mouse.wheel(0, random.randint(200, 500))
            main_page.wait_for_timeout(random.randint(700, 1500))

        main_page.wait_for_timeout(random.randint(1000, 2000))
        log.info("[warmup] Homepage visited")
    except Exception as e:
        log.warning(f"[warmup] Homepage visit failed: {e}")
    finally:
        main_page.close()

    queries = random.sample(WARMUP_SEARCHES, k=random.randint(2, 3))
    for query in queries:
        search_and_browse(main_page, query)
        time.sleep(random.uniform(1.5, 3.0))

    log.info("[warmup] Session warmup complete — starting product scraping")


# --- cycle runner ---


def run_scrape_cycle(browser, page, urls: list):
    shuffled = urls.copy()
    random.shuffle(shuffled)

    success = 0
    failed = 0

    log.info(f"{'='*50}")
    log.info(f"Starting scrape cycle — {len(shuffled)} URLs")
    log.info(f"{'='*50}")

    for url in shuffled:
        result = scrape_with_retry(page, url)

        if result:
            append_to_csv(result)
            success += 1
        else:
            failed += 1

        delay = random.uniform(PAGE_WAIT_MIN, PAGE_WAIT_MAX)
        log.info(f"Waiting {delay:.1f}s before next page...")
        time.sleep(delay)

    log.info(
        f"Cycle complete — {success} succeeded, {failed} failed out of {len(shuffled)}"
    )


# --- main ---


def main():
    parser = argparse.ArgumentParser(
        description="Amazon price scraper with Telegram alerts"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run notification logic against dummy_prices.csv (no browser needed)",
    )
    parser.add_argument(
        "--generate-dummy",
        action="store_true",
        help="Generate a fresh dummy_prices.csv and exit",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help=f"Override price change threshold (default: {PRICE_CHANGE_THRESHOLD:.0%}), e.g. 0.10 for 10%%",
    )
    args = parser.parse_args()

    if args.generate_dummy:
        generate_dummy_csv()
        return

    if args.test:
        run_test_mode()
        return

    # --- normal scraping mode ---
    if Camoufox is None:
        log.error(
            "camoufox is not installed — cannot run in scraping mode. Use --test for notification testing."
        )
        return

    log.info("=== Scraper started ===")
    log.info(f"Tracking {len(URLS)} URLs, polling every {POLL_INTERVAL // 60} minutes")
    log.info(
        f"Alert threshold: {PRICE_CHANGE_THRESHOLD:.0%} change from historical min/max"
    )

    with Camoufox(headless=False) as browser:
        log.info("Browser opened (headful, 1920x1080, en-US)")

        warmup_session(browser)

        page = browser.new_page(
            viewport={"width": 1920, "height": 1080}, locale="en-US"
        )

        while True:
            try:
                run_scrape_cycle(browser, page, URLS)
            except Exception as e:
                log.critical(f"Unexpected error in cycle: {e}")

            log.info(f"Sleeping {POLL_INTERVAL // 60} minutes until next cycle...")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
