import sqlite3
import json
import os
from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse
# Import your location mapping
from .utils.locations import extract_location, LOCATION_COORDS

# Path to DB
DB_PATH = os.path.join(settings.BASE_DIR, "scraped_posts.db")

def get_processed_posts():
    """Helper function to fetch and process posts from SQLite"""
    if not os.path.exists(DB_PATH):
        return []

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Fetch all necessary columns
    cur.execute("SELECT author, text, date, link, city, group_name FROM posts")
    rows = cur.fetchall()
    conn.close()

    post_list = []
    for author, text, date, link, city, group_name in rows:
        # Check if city exists in your COORDS dictionary
        if city in LOCATION_COORDS:
            lat, lon = LOCATION_COORDS[city]
            display_city = city
        else:
            # Requirements: Label as Khartoum / Unknown for default posts
            display_city = "Khartoum / Unknown Location"
            lat, lon = LOCATION_COORDS.get("Khartoum", (15.5007, 32.5599))

        post_list.append({
            "author": author,
            "text": text.replace("\n", "<br>"),
            "date": date,
            "link": link,
            "city": display_city, 
            "lat": lat,
            "lon": lon,
            "group_name": group_name if group_name else "General Source"
        })
    return post_list

# --- API View ---
def healthcare_posts_api(request):
    """The endpoint the map calls every 60 seconds"""
    return JsonResponse(get_processed_posts(), safe=False)

# --- Page Views ---
def home(request):
    return render(request, 'main/home.html')

def healthcare(request):
    """Loads the healthcare page with initial data"""
    posts = get_processed_posts()
    return render(request, 'main/healthcare/healthcare.html', {
        "posts_json": json.dumps(posts, ensure_ascii=False)
    })

def map_view(request):
    """Standalone map view if needed"""
    posts = get_processed_posts()
    return render(request, "main/map.html", {
        "posts_json": json.dumps(posts, ensure_ascii=False)
    })

def humanitarian(request):
    return render(request, 'main/humanitarian/humanitarian.html')

def energy(request):
    return render(request, 'main/energy/energy.html')

def about(request):
    return render(request, 'main/about/about.html')

def base(request):
    return render(request, 'main/base.html')