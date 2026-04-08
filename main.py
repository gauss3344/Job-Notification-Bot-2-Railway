from datetime import datetime
import threading
import time
import os
import json
import pytz
import logging
import requests
import random
from flask import Flask, jsonify
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from urllib3.exceptions import InsecureRequestWarning
from typing import List, Tuple, Dict, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from apscheduler.schedulers.background import BackgroundScheduler

from helpers_mysql import (
    init_db, load_sent_notice_hashes, add_sent_notice,
    send_telegram_message, get_webdriver, close_webdriver,
    clear_all_sent_notices, get_notice_hash
)

# === Flask App Setup ===
app = Flask(__name__)
last_check_time = None
bot_start_time = datetime.now(pytz.utc)

@app.route('/')
def home():
    return "✅ Job Notice Bot is Running (Railway & Human-Simulation Mode)!"

@app.route('/last-check')
def show_last_check():
    global last_check_time, bot_start_time
    dhaka_tz = pytz.timezone('Asia/Dhaka')
    start_str = bot_start_time.astimezone(dhaka_tz).strftime('%Y-%m-%d %H:%M:%S')
    
    response_html = f"🚀 <b>Bot Started At:</b> {start_str} (Asia/Dhaka)<br>"
    if last_check_time:
        local_time = last_check_time.astimezone(dhaka_tz)
        response_html += f"🕒 <b>Last Check At:</b> {local_time.strftime('%Y-%m-%d %H:%M:%S')} (Asia/Dhaka)"
    else:
        response_html += "❌ <b>Last Check:</b> No check performed yet."
    return response_html

@app.route('/clear-sent-notices')
def clear_sent_notices_api():
    clear_all_sent_notices()
    return jsonify({"status": "success", "message": "✅ All sent_notices data cleared from database."})

def run_flask():
    # Railway environment সাধারণত ১০০০০ পোর্টে রান হয়
    app.run(host='0.0.0.0', port=10000)

threading.Thread(target=run_flask, daemon=True).start()

# === Scraper Configuration ===
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
init_db()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

KEYWORDS = [
    "recruitment", "job", "নিয়োগ বিজ্ঞপ্তি", "career", "advertisement",
    "নিয়োগ", "শূন্যপদ", "শূন্য পদ", "job circular", "vacancy",
    "appointment", "opportunity"
]

# ✅ Real Browser Headers (To bypass bot detection)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,bn;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Referer': 'https://www.google.com/',
    'Upgrade-Insecure-Requests': '1'
}

def is_relevant(text: str) -> bool:
    if not text: return False
    text_lc = text.strip().lower()
    return any(keyword.lower() in text_lc for keyword in KEYWORDS)

def fetch_site_data(site: Dict[str, Any]) -> List[Tuple[str, str]]:
    notices = []
    site_name = site.get("name", "Unknown Site")
    site_url = site["url"]
    site_base_url = site.get("base_url", site_url)
    selenium_enabled = site.get("selenium_enabled", False)
    
    # ✅ config.json থেকে সেলেক্টর নেওয়া, না থাকলে ডিফল্ট "table tbody tr"
    row_selector = site.get("row_selector", "table tbody tr")
    wait_time = site.get("wait_time", 20)
    driver = None

    # মানুষের মতো আচরণ করতে র্যান্ডম ওয়েট
    time.sleep(random.uniform(2, 5))

    logging.info(f"Fetching: {site_name} | Method: {'Selenium' if selenium_enabled else 'Requests'} | Selector: {row_selector}")

    try:
        if selenium_enabled:
            driver = get_webdriver()
            driver.get(site_url)
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, row_selector))
            )
            soup = BeautifulSoup(driver.page_source, "html.parser")
        else:
            session = requests.Session()
            response = session.get(site_url, verify=False, timeout=25, headers=HEADERS)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

        # ✅ ডাইনামিক রো সেলেক্টর ব্যবহার
        rows = soup.select(row_selector)
        
        if not rows:
            logging.warning(f"No data found for {site_name} with selector: {row_selector}")
            return []

        for row in rows:
            # কলাম খোঁজা (টেবিল বা ডিভ উভয়ই সাপোর্ট করবে)
            cols = row.find_all(["td", "div", "span"], recursive=False)
            
            # টাইটেল এবং লিংক এক্সট্রাকশন লজিক
            title = ""
            if len(cols) >= 2:
                title = cols[1].get_text(strip=True)
            else:
                title = row.get_text(strip=True)

            a_tag = row.find("a", href=True)
            pdf_link = urljoin(site_base_url, a_tag["href"]) if a_tag else ""

            if title and is_relevant(title):
                notices.append((title, pdf_link))

    except Exception as e:
        logging.error(f"Error processing {site_name}: {e}")
    finally:
        if driver:
            close_webdriver(driver)

    return notices

def check_all_sites():
    global last_check_time
    last_check_time = datetime.now(pytz.utc)

    logging.info(f"🚀 Full Scan Started at {last_check_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")

    config_path = "config.json"
    if not os.path.exists(config_path):
        logging.error("config.json not found!")
        return

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        logging.error(f"Config Load Error: {e}")
        return

    for site in config:
        site_id = site.get("id")
        if not site_id: continue

        notices = fetch_site_data(site)
        if not notices: continue

        sent_hashes = load_sent_notice_hashes(site_id)
        new_notices = []

        for text, link in notices:
            notice_hash = get_notice_hash(text, link)
            if notice_hash not in sent_hashes:
                new_notices.append((text, link, notice_hash))

        if not new_notices:
            continue

        # নতুন নোটিশগুলো ক্রমানুসারে পাঠানো
        new_notices.reverse()
        for text, link, notice_hash in new_notices:
            msg = f"📢 *{site.get('name')}*\n\n📝 {text}"
            if link:
                msg += f"\n\n📥 [PDF Download]({link})"
            else:
                msg += f"\n\n❌ PDF পাওয়া যায়নি"

            send_telegram_message(msg)
            add_sent_notice(site_id, notice_hash)
            time.sleep(1) # টেলিগ্রাম স্প্যাম ফিল্টার এড়াতে ছোট গ্যাপ

# === Scheduler Setup ===
scheduler = BackgroundScheduler(timezone=pytz.timezone("Asia/Dhaka"))
# প্রতি ৬০ মিনিট পর পর চেক করবে
scheduler.add_job(check_all_sites, 'interval', minutes=60)
scheduler.start()

# স্ক্রিপ্ট রান হওয়ামাত্র প্রথমবার চেক শুরু করবে
if __name__ == "__main__":
    check_all_sites()
    while True:
        time.sleep(60)
