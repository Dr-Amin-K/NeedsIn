import json
import re
import time
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from django.core.management.base import BaseCommand
from playwright.sync_api import sync_playwright
from main.locations import extract_location


GROUP_URL = "https://www.facebook.com/groups/wafradawa"
OUTPUT_FILE = Path("fb_public_scrape.json")
MAX_SCROLLS = 40

# Normalize raw strings
def norm(s: str) -> str:
    if not s:
        return ""
    # Remove various FB hidden formatting chars
    s = re.sub(r'[\u00A0\u202F\u2007\u2009\u200E\u200F\u202A-\u202E]+', ' ', s)
    return s.strip()


# Parse date (YYYY-MM-DD)

MONTH_NAME_RE = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)'

# Ensure this variable is defined globally, before parse_fb_date
FULL_DATE_RE = re.compile(
    rf'({MONTH_NAME_RE})\s+(\d{{1,2}})\s*(?:at\s*(\d{{1,2}}:\d{{2}}\s*(?:AM|PM)))?', 
    re.IGNORECASE
)

def parse_fb_date(raw: str, now=None):
    if not raw:
        return None
    if now is None:
        now = datetime.now()

    s = norm(raw).replace(',', '') # Clean up commas

    # Explicit Date: "e.g. November 7 at 6:24 PM" or "November 7"
    m = FULL_DATE_RE.search(s)
    if m:
        month_name = m.group(1)
        day = m.group(2)
        
        # Build the full date string for parsing
        date_str = f"{month_name} {day}"
        date_format = "%B %d"
        
        # Add the year component if available
        date_str += f" {now.year}"
        date_format += " %Y"

        try:
            candidate = datetime.strptime(date_str, date_format)

            # Year rollover fix: If the parsed date is far in the future, assume last year
            if candidate.date() > now.date() and (candidate - now).days > 7:
                candidate = candidate.replace(year=now.year - 1)

            return candidate.date().isoformat()
        except ValueError:
            # Failed to parse the constructed string
            pass

    s_lower = s.lower()

    # days ago
    m = re.search(r'(\d+)\s*(?:d|day|days)\b', s_lower)
    if m:
        return (now - timedelta(days=int(m.group(1)))).date().isoformat()

    # hours
    m = re.search(r'(\d+)\s*(?:h|hr|hour|hours)\b', s_lower)
    if m:
        return (now - timedelta(hours=int(m.group(1)))).date().isoformat()

    # minutes
    m = re.search(r'(\d+)\s*(?:m|min|minute|minutes)\b', s_lower)
    if m:
        return (now - timedelta(minutes=int(m.group(1)))).date().isoformat()

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


# Extract posts (NO screenshots)

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

        # Get text
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




#  DATABASE PARSER

def extract_author_text(full_text: str):
    lines = full_text.split("\n")
    author = lines[0].strip() if lines else ""

    # Locate the "·" separator
    body_start = None
    for i, line in enumerate(lines):
        if "·" in line:
            body_start = i + 1
            break

    if body_start is None:
        return author, ""

    # collect body until Like / All reactions / Comment / Share
    stop_words = ["Like", "All reactions", "Comment", "Share"]
    body_lines = []
    for line in lines[body_start:]:
        if any(sw in line for sw in stop_words):
            break
        body_lines.append(line)

    return author, "\n".join(body_lines).strip()




# Django command

class Command(BaseCommand):
    help = "Facebook group scraper. Extracts text + date + link."

    def handle(self, *args, **kwargs):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
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

            cur.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    author TEXT,
                    text TEXT,
                    date TEXT,
                    link TEXT UNIQUE
                )
            """)

            for post in cleaned:
                author, textbody = extract_author_text(post["text"])

                cur.execute("""
                    INSERT INTO posts (author, text, date, link)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(link) DO UPDATE SET
                        author=excluded.author,
                        text=excluded.text,
                        date=excluded.date
                """, (author, textbody, post["date"], post["link"]))

            conn.commit()
            conn.close()
            

            browser.close()
            print(f"Saved → {OUTPUT_FILE}")
            print(f"Total posts: {len(cleaned)}")
