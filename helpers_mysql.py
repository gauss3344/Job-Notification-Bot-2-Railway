import hashlib
import os
import pymysql
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

# === MySQL Configuration ===
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_DB = os.getenv("MYSQL_DB")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")


# ✅ Unique Hash
def get_notice_hash(text: str, link: str) -> str:
    return hashlib.sha256((text.strip() + link.strip()).encode()).hexdigest()


# ✅ MySQL Connection (Optimized)
def get_connection():
    if not all([MYSQL_HOST, MYSQL_DB, MYSQL_USER, MYSQL_PASSWORD]):
        raise ValueError("MySQL database credentials are missing.")

    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
        read_timeout=10,
        write_timeout=10,
        autocommit=True
    )


# ✅ Retry Connection (VERY IMPORTANT 🔥)
def get_connection_retry(retries=3, delay=2):
    for i in range(retries):
        try:
            return get_connection()
        except Exception as e:
            print(f"❌ MySQL retry {i+1} failed: {e}")
            time.sleep(delay)
    raise Exception("❌ Database connection failed after retries")


# ✅ Init Table
def init_db():
    with get_connection_retry() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sent_notices (
                    site VARCHAR(255),
                    link_hash VARCHAR(64),
                    PRIMARY KEY (site, link_hash)
                )
            """)
        conn.commit()


# ✅ Load Sent Notices
def load_sent_notice_hashes(site):
    with get_connection_retry() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT link_hash FROM sent_notices WHERE site = %s",
                (site,)
            )
            return {row['link_hash'] for row in cur.fetchall()}


# ✅ Add Notice
def add_sent_notice(site, link_hash):
    with get_connection_retry() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT IGNORE INTO sent_notices (site, link_hash) VALUES (%s, %s)",
                (site, link_hash)
            )
        conn.commit()


# ✅ Clear Table
def clear_all_sent_notices():
    with get_connection_retry() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sent_notices")
        conn.commit()


# === Telegram Config ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("BOT_TOKEN or CHAT_ID environment variable not set.")

bot = Bot(token=BOT_TOKEN)


# ✅ Markdown Escape (FIXED)
def escape_markdown(text: str) -> str:
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)


# ✅ Send Telegram Message (Improved)
def send_telegram_message(message: str, markdown: bool = False):
    try:
        if markdown:
            safe_message = escape_markdown(message)
            bot.send_message(
                chat_id=CHAT_ID,
                text=safe_message,
                parse_mode="MarkdownV2",
                disable_web_page_preview=True
            )
        else:
            bot.send_message(
                chat_id=CHAT_ID,
                text=message,
                disable_web_page_preview=True
            )
    except Exception as e:
        print(f"❌ Telegram send error: {e}")


# === Selenium WebDriver ===
def get_webdriver(headless=True) -> webdriver.Chrome:
    chrome_options = Options()

    if headless:
        chrome_options.add_argument("--headless=new")

    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    return webdriver.Chrome(options=chrome_options)


def close_webdriver(driver):
    try:
        driver.quit()
    except Exception:
        pass
