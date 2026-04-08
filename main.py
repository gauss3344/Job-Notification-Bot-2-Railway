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

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 4000))
MYSQL_DB = os.getenv("MYSQL_DB")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")

def get_notice_hash(text: str, link: str) -> str:
    return hashlib.sha256((text.strip() + link.strip()).encode()).hexdigest()

def get_connection():
    # TiDB/MySQL SSL Fix
    ssl_config = {'ssl': True}
    if os.path.exists('/etc/ssl/certs/ca-certificates.crt'):
        ssl_config = {'ca': '/etc/ssl/certs/ca-certificates.crt'}

    return pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT,
        user=MYSQL_USER, password=MYSQL_PASSWORD,
        database=MYSQL_DB, charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=15, autocommit=True,
        ssl=ssl_config
    )

def get_connection_retry(retries=3, delay=2):
    for i in range(retries):
        try: return get_connection()
        except Exception as e:
            print(f"❌ MySQL retry {i+1}: {e}")
            time.sleep(delay)
    raise Exception("❌ Database failed")

def init_db():
    with get_connection_retry() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sent_notices (
                    site VARCHAR(255), link_hash VARCHAR(64),
                    PRIMARY KEY (site, link_hash)
                )
            """)

def load_sent_notice_hashes(site):
    with get_connection_retry() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT link_hash FROM sent_notices WHERE site = %s", (site,))
            return {row['link_hash'] for row in cur.fetchall()}

def add_sent_notice(site, link_hash):
    with get_connection_retry() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT IGNORE INTO sent_notices (site, link_hash) VALUES (%s, %s)", (site, link_hash))

def clear_all_sent_notices():
    with get_connection_retry() as conn:
        with conn.cursor() as cur: cur.execute("DELETE FROM sent_notices")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
bot = Bot(token=BOT_TOKEN)

def escape_markdown(text: str) -> str:
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

def send_telegram_message(message: str):
    try:
        bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e: print(f"❌ Telegram error: {e}")

# ✅ উন্নত Selenium WebDriver (ব্রাউজার লুকানোর জন্য)
def get_webdriver(headless=True) -> webdriver.Chrome:
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    
    # বট ডিটেকশন এড়ানোর জন্য আরগুমেন্ট
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # জাভাস্ক্রিপ্ট দিয়ে 'webdriver' প্রপার্টি মুছে ফেলা
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    
    return driver

def close_webdriver(driver):
    try: driver.quit()
    except: pass
