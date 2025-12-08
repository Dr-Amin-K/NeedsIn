# main/views.py
import sqlite3
import json
import os
from django.shortcuts import render
from django.conf import settings
from .utils.locations import extract_location

# Path to DB
DB_PATH = os.path.join(settings.BASE_DIR, "scraped_posts.db")

def map_view(request):
    """Load posts from SQLite DB and prepare them for Leaflet"""
    if not os.path.exists(DB_PATH):
        print(f"DEBUG: DB not found at {DB_PATH}")
        rows = []
    else:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT author, text, date, link FROM posts")
        rows = cur.fetchall()
        conn.close()
        print(f"DEBUG: Fetched {len(rows)} rows from DB")

    posts = []

    for idx, (author, text, date, link) in enumerate(rows, start=1):
        result = extract_location(text)
        if result:
            city, (lat, lon) = result
        else:
            city = "Khartoum"
            lat, lon = 15.5007, 32.5599

        posts.append({
            "author": author,
            "text": text.replace("\n", "<br>"),
            "date": date,
            "link": link,
            "city": city,
            "lat": lat,
            "lon": lon
        })

    print(f"DEBUG: Total posts to render: {len(posts)}")
    if posts:
        print(f"DEBUG: First post: {posts[0]}")

    posts_json = json.dumps(posts, ensure_ascii=False)
    return render(request, "main/map.html", {"posts_json": posts_json})



def base(request):
    return render(request, 'main/base.html')

def home(request):
    return render(request, 'main/home.html')

def healthcare(request):
    """Load posts from SQLite DB and prepare them for Leaflet, for the healthcare page."""
    if not os.path.exists(DB_PATH):
        print(f"DEBUG: DB not found at {DB_PATH}")
        rows = []
    else:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT author, text, date, link FROM posts")
        rows = cur.fetchall()
        conn.close()
        print(f"DEBUG: Fetched {len(rows)} rows from DB")

    posts = []

    for idx, (author, text, date, link) in enumerate(rows, start=1):
        result = extract_location(text)
        if result:
            city, (lat, lon) = result
        else:
            city = "Khartoum"
            lat, lon = 15.5007, 32.5599

        posts.append({
            "author": author,
            "text": text.replace("\n", "<br>"),
            "date": date,
            "link": link,
            "city": city,
            "lat": lat,
            "lon": lon
        })

    print(f"DEBUG: Total posts to render: {len(posts)}")
    if posts:
        print(f"DEBUG: First post: {posts[0]}")

    posts_json = json.dumps(posts, ensure_ascii=False)
    return render(request, 'main/healthcare/healthcare.html', {"posts_json": posts_json})

def humanitarian(request):
    return render(request, 'main/humanitarian/humanitarian.html')

def energy(request):
    return render(request, 'main/energy/energy.html')

def about(request):
    return render(request, 'main/about/about.html')
