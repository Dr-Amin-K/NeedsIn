import json
import re
import time
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from django.core.management.base import BaseCommand
from playwright.sync_api import sync_playwright
from main.utils.locations import extract_location


GROUP_URL = "https://www.facebook.com/groups/wafradawa"
OUTPUT_FILE = Path("fb_public_scrape.json")
MAX_SCROLLS = 40

# Normalize raw strings
def norm(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r'[\u00A0\u202F\u2007\u2009\u200E\u200F\u202A-\u202E]+', ' ', s)
    return s.strip()

# Parse Facebook post date
MONTH_NAME_RE = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)'
FULL_DATE_RE = re.compile(
    rf'({MONTH_NAME_RE})\s+(\d{{1,2}})\s*(?:at\s*(\d{{1,2}}:\d{{2}}\s*(?:AM|PM)))?', 
    re.IGNORECASE
)

def parse_fb_date(raw: str, now=None):
    if not raw:
        return None
    if now is None:
        now = datetime.now()
    s = norm(raw).replace(',', '')
    m = FULL_DATE_RE.search(s)
    if m:
        month_name = m.group(1)
        day = m.group(2)
        date_str = f"{month_name} {day} {now.year}"
        try:
            candidate = datetime.strptime(date_str, "%B %d %Y")
            if candidate.date() > now.date() and (candidate - now).days > 7:
                candidate = candidate.replace(year=now.year - 1)
            return candidate.date().isoformat()
        except ValueError:
            pass
    s_lower = s.lower()
    for regex, delta in [(r'(\d+)\s*(?:d|day|days)\b', 'days'),
                         (r'(\d+)\s*(?:h|hr|hour|hours)\b', 'hours'),
                         (r'(\d+)\s*(?:m|min|minute|minutes)\b', 'minutes')]:
        m = re.search(regex, s_lower)
        if m:
            kwargs = {delta: int(m.group(1))}
            return (now - timedelta(**kwargs)).date().isoformat()
    return None

# Close login popups
def close_login_popup(page):
    selectors = [
        'div[aria-label="Close"]',
        'button[aria-label="Close"]',
        'div[role="dialog"] [aria-label="Close"]',
        'svg[aria-label="Close"]',
        'div[role="dialog"] button',
    ]
    for _ in range(6):
        for s in selectors:
            try:
                el = page.locator(s)
                if el.count() > 0:
                    el.first.click(force=True)
                    time.sleep(0.5)
                    return True
            except:
                pass
        page.mouse.click(10, 10)
        time.sleep(0.2)
    return False

# Scroll helper
def scroll(page):
    page.mouse.wheel(0, random.randint(900, 1400))
    time.sleep(random.uniform(1.0, 1.8))

# Extract posts (no screenshots)
def extract_posts(page):
    posts = []
    articles = page.locator('div[role="article"]')
    total = articles.count()
    now = datetime.now()
    for i in range(total):
        art = articles.nth(i)
        try:
            art.scroll_into_view_if_needed()
            time.sleep(0.3)
        except:
            pass
        try:
            raw_text = norm(art.inner_text())
        except:
            raw_text = ""
        # Extract link
        link = None
        try:
            l = art.locator('a[href*="/posts/"], a[href*="/permalink/"]')
            if l.count() > 0:
                href = l.first.get_attribute("href")
                if href:
                    if href.startswith("/"):
                        href = "https://www.facebook.com" + href
                    link = href.split("?")[0]
        except:
            pass
        # Extract date
        date_val = parse_fb_date(raw_text, now=now)
        posts.append({
            "text": raw_text,
            "date": date_val,
            "link": link,
        })
    return posts

# Parse author and body
def extract_author_text(full_text: str):
    lines = full_text.split("\n")
    author = lines[0].strip() if lines else ""
    body_start = None
    for i, line in enumerate(lines):
        if "·" in line:
            body_start = i + 1
            break
    if body_start is None:
        return author, ""
    stop_words = ["Like", "All reactions", "Comment", "Share"]
    body_lines = []
    for line in lines[body_start:]:
        if any(sw in line for sw in stop_words):
            break
        body_lines.append(line)
    return author, "\n".join(body_lines).strip()

# Django management command
class Command(BaseCommand):
    help = "Facebook group scraper. Extracts text + date + link + city + group."

    def handle(self, *args, **kwargs):
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,  # MUST be True on a server
                executable_path="/usr/bin/chromium",
                args=["--no-sandbox", "--disable-gpu"]
            )
            context = browser.new_context(
                viewport={"width": 1400, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122 Safari/537.36"
            )
            page = context.new_page()
            page.goto(GROUP_URL, timeout=60000)
            time.sleep(5)

            popup_count = 0
            if close_login_popup(page):
                popup_count += 1

            last_count = 0
            all_posts = []

            for _ in range(MAX_SCROLLS):
                if close_login_popup(page):
                    popup_count += 1
                    if popup_count >= 2:
                        print("Second popup → stopping.")
                        browser.close()
                        return

                new_posts = extract_posts(page)
                all_posts.extend(new_posts)

                scroll(page)

                count = page.locator('div[role="article"]').count()
                if count == last_count:
                    break
                last_count = count

            # Dedupe + remove empties
            cleaned = []
            seen_links = set()
            for p in all_posts:
                if not p["text"].strip() and not p["link"]:
                    continue
                if p["link"] and p["link"] in seen_links:
                    continue
                if p["link"]:
                    seen_links.add(p["link"])
                cleaned.append(p)

            OUTPUT_FILE.write_text(
                json.dumps(cleaned, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            # DATABASE SAVE
            conn = sqlite3.connect("scraped_posts.db")
            cur = conn.cursor()

            # Add new columns: group_name, city
            cur.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    author TEXT,
                    text TEXT,
                    date TEXT,
                    link TEXT UNIQUE,
                    group_name TEXT,
                    city TEXT
                )
            """)

            for post in cleaned:
                author, textbody = extract_author_text(post["text"])
                group_name = GROUP_URL.rstrip("/").split("/")[-1]  # e.g., 'wafradawa'

                # Extract city
                result = extract_location(post["text"])
                if result:
                    city_name, _ = result
                else:
                    city_name = "Khartoum"

                cur.execute("""
                    INSERT INTO posts (author, text, date, link, group_name, city)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(link) DO UPDATE SET
                        author=excluded.author,
                        text=excluded.text,
                        date=excluded.date,
                        group_name=excluded.group_name,
                        city=excluded.city
                """, (author, textbody, post["date"], post["link"], group_name, city_name))

            conn.commit()
            conn.close()

            browser.close()
            print(f"Saved → {OUTPUT_FILE}")
            print(f"Total posts: {len(cleaned)}")
