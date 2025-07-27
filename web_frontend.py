#!/usr/bin/env python3
"""
Web frontend for Apple Fitness+ workout playlist scraper
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
import time
import threading
from queue import Queue
from apple_fitness_scraper import AppleFitnessScraper
import os

app = Flask(__name__)

# Global variables for processing state
processing_queue = Queue()
processing_status = {
    "is_processing": False,
    "current_url": "",
    "completed": 0,
    "total": 0,
    "results": [],
    "errors": [],
}


def process_urls_worker():
    """Background worker to process URLs with rate limiting"""
    global processing_status

    scraper = AppleFitnessScraper()

    while True:
        if not processing_queue.empty():
            queue_item = processing_queue.get()

            # Handle both old format (just URLs) and new format (URLs, force_refresh)
            if isinstance(queue_item, tuple):
                urls, force_refresh = queue_item
            else:
                urls = queue_item
                force_refresh = False

            processing_status["is_processing"] = True
            processing_status["completed"] = 0
            processing_status["total"] = len(urls)
            processing_status["results"] = []
            processing_status["errors"] = []

            for i, url in enumerate(urls):
                if url is None:
                    continue
                url = url.strip()
                if not url:
                    continue

                processing_status["current_url"] = url

                try:
                    # Check if already cached (unless force refresh is enabled)
                    cached_songs = (
                        None if force_refresh else scraper._get_cached_result(url)
                    )
                    made_server_request = False

                    if cached_songs:
                        processing_status["results"].append(
                            {
                                "url": url,
                                "status": "cached",
                                "songs": len(cached_songs.get("songs", [])),
                                "message": "Found in cache",
                            }
                        )
                    else:
                        # Fetch from server
                        made_server_request = True
                        songs = scraper.get_workout_songs(url)
                        if songs:
                            status_msg = "Refreshed" if force_refresh else "Scraped"
                            processing_status["results"].append(
                                {
                                    "url": url,
                                    "status": "success",
                                    "songs": len(songs.get("songs", [])),
                                    "message": f"{status_msg} {len(songs.get('songs', []))} songs",
                                }
                            )
                        else:
                            processing_status["errors"].append(
                                {
                                    "url": url,
                                    "error": "No songs found or page unavailable",
                                }
                            )

                except Exception as e:
                    processing_status["errors"].append({"url": url, "error": str(e)})

                processing_status["completed"] = i + 1

                # Rate limiting: only wait after server requests (not cache hits)
                if made_server_request and i < len(urls) - 1:
                    time.sleep(2)

            processing_status["is_processing"] = False
            processing_status["current_url"] = ""
            processing_queue.task_done()
        else:
            time.sleep(1)


# Start background worker
worker_thread = threading.Thread(target=process_urls_worker, daemon=True)
worker_thread.start()


@app.route("/")
def index():
    """Main page - Workout Library"""
    scraper = AppleFitnessScraper()

    import sqlite3

    with sqlite3.connect(scraper.db_path) as conn:
        cursor = conn.execute("""
            SELECT COALESCE(canonical_url, original_url) as display_url, 
                   original_url,
                   canonical_url, title, trainer, duration, genre, episode, workout_type, workout_category, date, datetime, 
                   cached_at, songs_json, needs_update 
            FROM workout_cache 
            ORDER BY cached_at DESC
        """)
        rows = cursor.fetchall()

    cache_data = []
    for row in rows:
        (
            display_url,
            original_url,
            canonical_url,
            title,
            trainer,
            duration,
            genre,
            episode,
            workout_type,
            workout_category,
            date,
            datetime_val,
            cached_at,
            songs_json,
            needs_update,
        ) = row

        songs = []
        if songs_json:
            import json

            songs = json.loads(songs_json)

        duration_bucket = normalize_duration(duration)

        cache_data.append(
            {
                "url": display_url,  # Show canonical URL primarily
                "original_url": original_url,  # Keep original for reference
                "canonical_url": canonical_url,
                "title": title or "Unknown Workout",
                "trainer": trainer,
                "duration": duration,
                "duration_bucket": duration_bucket,
                "genre": genre,
                "episode": episode,
                "workout_type": workout_type,
                "workout_category": workout_category,
                "date": date,
                "datetime": datetime_val,
                "cached_at": cached_at,
                "song_count": len(songs),
                "songs": songs,
                "needs_update": bool(needs_update),
            }
        )

    return render_template("index.html", cache_data=cache_data)


@app.route("/process", methods=["POST"])
def process_urls():
    """Handle URL processing request"""
    data = request.json
    urls = [url.strip() for url in data.get("urls", "").split("\n") if url.strip()]
    force_refresh = data.get("force_refresh", False)

    if not urls:
        return jsonify({"error": "No valid URLs provided"}), 400

    if processing_status["is_processing"]:
        return jsonify({"error": "Already processing URLs. Please wait."}), 400

    # Add URLs to processing queue with force_refresh flag
    processing_queue.put((urls, force_refresh))

    return jsonify({"message": f"Started processing {len(urls)} URLs"})


@app.route("/status")
def get_status():
    """Get current processing status"""
    return jsonify(processing_status)


@app.route("/pending-updates")
def get_pending_updates():
    """Get list of entries that need updating"""
    scraper = AppleFitnessScraper()
    count, urls = scraper._get_entries_needing_update()
    return jsonify({"count": count, "urls": urls})


@app.route("/update-pending", methods=["POST"])
def update_pending():
    """Update all pending entries"""
    scraper = AppleFitnessScraper()
    count, urls = scraper._get_entries_needing_update()

    if not urls:
        return jsonify({"message": "No entries need updating"}), 400

    if processing_status["is_processing"]:
        return jsonify({"error": "Already processing URLs. Please wait."}), 400

    # Add URLs to processing queue (always force refresh for pending updates)
    processing_queue.put((urls, True))

    return jsonify({"message": f"Started updating {len(urls)} pending entries"})


@app.route("/update-single", methods=["POST"])
def update_single():
    """Update a single cache entry"""
    data = request.json
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    if processing_status["is_processing"]:
        return jsonify({"error": "Already processing URLs. Please wait."}), 400

    # Add single URL to processing queue (always force refresh for individual updates)
    processing_queue.put(([url], True))

    return jsonify({"message": f"Started updating: {url}"})


def normalize_duration(duration_str):
    """Normalize duration to standard buckets: 5, 10, 20, 30, 45 minutes"""
    if not duration_str:
        return None

    # Extract number from duration string (e.g., "45min" -> 45)
    import re

    match = re.search(r"(\d+)", duration_str)
    if not match:
        return None

    minutes = int(match.group(1))

    # Map to buckets
    if minutes <= 7:
        return 5
    elif minutes <= 15:
        return 10
    elif minutes <= 25:
        return 20
    elif minutes <= 37:
        return 30
    else:
        return 45


@app.route("/add")
def add_workouts():
    """Add new workouts page"""
    return render_template("add.html")


@app.route("/filter-options")
def get_filter_options():
    """Get unique filter options for trainers, genres, and durations"""
    scraper = AppleFitnessScraper()

    import sqlite3

    with sqlite3.connect(scraper.db_path) as conn:
        # Get unique trainers
        cursor = conn.execute(
            "SELECT DISTINCT trainer FROM workout_cache WHERE trainer IS NOT NULL ORDER BY trainer"
        )
        trainers = [row[0] for row in cursor.fetchall()]

        # Get unique genres
        cursor = conn.execute(
            "SELECT DISTINCT genre FROM workout_cache WHERE genre IS NOT NULL ORDER BY genre"
        )
        genres = [row[0] for row in cursor.fetchall()]

        # Get unique workout categories
        cursor = conn.execute(
            "SELECT DISTINCT workout_category FROM workout_cache WHERE workout_category IS NOT NULL ORDER BY workout_category"
        )
        workout_categories = [row[0] for row in cursor.fetchall()]

        # Get all durations and normalize them
        cursor = conn.execute(
            "SELECT DISTINCT duration FROM workout_cache WHERE duration IS NOT NULL"
        )
        duration_buckets = set()
        for row in cursor.fetchall():
            bucket = normalize_duration(row[0])
            if bucket:
                duration_buckets.add(bucket)

        durations = sorted(list(duration_buckets))

    return jsonify(
        {
            "trainers": trainers,
            "genres": genres,
            "workout_categories": workout_categories,
            "durations": durations,
        }
    )


if __name__ == "__main__":
    # Create templates directory if it doesn't exist
    os.makedirs("templates", exist_ok=True)
    app.run(debug=True, host="0.0.0.0", port=5001)
