#!/usr/bin/env python3
"""
Apple Fitness+ Workout Song Extractor

This script fetches Apple Fitness+ workout pages and extracts the playlist information,
including song titles, artists, and Apple Music links.
"""

import requests
from bs4 import BeautifulSoup
import json
import sqlite3
import sys
import re
from datetime import datetime
from urllib.parse import urlparse


class AppleFitnessScraper:
    def __init__(self, db_path="fitness_cache.db"):
        self.db_path = db_path
        self.session = requests.Session()
        # Use a realistic User-Agent to avoid being blocked
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )
        self._init_database()

    def _clean_url(self, url):
        """Remove query parameters from URL"""
        if "?" in url:
            return url.split("?")[0]
        return url

    def _normalize_url_to_us(self, url):
        """Convert international Apple Fitness URL to US format"""
        # Pattern to match international URLs
        pattern = r"https://fitness\.apple\.com/[a-z]{2}/(.+)"
        match = re.match(pattern, url)
        if match:
            return f"https://fitness.apple.com/us/{match.group(1)}"
        return url

    def _get_canonical_url(self, url):
        """Get the canonical URL by following redirects"""
        try:
            # First normalize to US format
            us_url = self._normalize_url_to_us(url)

            # Follow redirects to get canonical URL
            response = self.session.get(us_url, allow_redirects=True, timeout=10)
            if response.status_code == 200:
                return response.url
            else:
                # If US version fails, try original
                response = self.session.get(url, allow_redirects=True, timeout=10)
                if response.status_code == 200:
                    return response.url
        except Exception as e:
            print(f"Warning: Could not get canonical URL for {url}: {e}")
            # Fallback to normalized US URL
            return self._normalize_url_to_us(url)

        return url

    def _extract_workout_category(self, url):
        """Extract workout category from URL path"""
        # URL format: https://fitness.apple.com/us/workout/CATEGORY-with-trainer/ID
        # Examples:
        # - cycling-with-emily -> cycling
        # - core-with-gregg -> core
        # - strength-with-kim -> strength
        # - treadmill-with-emily -> treadmill

        try:
            # Extract the workout slug from URL
            parts = url.split("/")
            if "workout" in parts:
                workout_index = parts.index("workout")
                if workout_index + 1 < len(parts):
                    workout_slug = parts[workout_index + 1]

                    # Extract category (everything before "-with-")
                    if "-with-" in workout_slug:
                        category = workout_slug.split("-with-")[0]
                    else:
                        # Fallback: try to extract from first part of slug
                        category = workout_slug.split("-")[0]

                    # Special case: HIIT should be uppercase
                    if category.lower() == "hiit":
                        return "HIIT"

                    return category.title()  # Capitalize first letter

        except (IndexError, ValueError):
            pass

        return "Unknown"

    def _get_expected_schema(self):
        """Define the expected database schema"""
        return {
            "canonical_url": "TEXT PRIMARY KEY",
            "original_url": "TEXT",
            "title": "TEXT",
            "trainer": "TEXT",
            "duration": "TEXT",
            "genre": "TEXT",
            "episode": "TEXT",
            "workout_type": "TEXT",
            "workout_category": "TEXT",
            "date": "TEXT",
            "datetime": "TEXT",
            "songs_json": "TEXT",
            "needs_update": "BOOLEAN DEFAULT 0",
            "cached_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "is_favorite": "BOOLEAN DEFAULT 0",
        }

    def _get_current_schema(self, conn):
        """Get the current database schema"""
        cursor = conn.execute("PRAGMA table_info(workout_cache)")
        columns = {}
        for row in cursor.fetchall():
            # row format: (cid, name, type, notnull, dflt_value, pk)
            col_name = row[1]
            col_type = row[2]
            col_pk = row[5]

            if col_pk:
                col_type += " PRIMARY KEY"
            if row[4] is not None:  # default value
                col_type += f" DEFAULT {row[4]}"

            columns[col_name] = col_type
        return columns

    def _schemas_match(self, current, expected):
        """Check if current schema matches expected schema"""
        current_keys = set(current.keys())
        expected_keys = set(expected.keys())

        # Check if all expected columns exist AND if canonical_url exists as primary key
        has_all_expected = current_keys >= expected_keys
        has_canonical_pk = "canonical_url" in current and "PRIMARY KEY" in current.get(
            "canonical_url", ""
        )

        return has_all_expected and has_canonical_pk

    def _init_database(self):
        """Initialize the SQLite database for caching workout results"""
        with sqlite3.connect(self.db_path) as conn:
            current_schema = self._get_current_schema(conn)
            expected_schema = self._get_expected_schema()

            if not current_schema:
                # Create new table with full schema
                print("Creating new database...")
                columns_sql = []
                for col_name, col_type in expected_schema.items():
                    columns_sql.append(f"{col_name} {col_type}")

                conn.execute(f"""
                    CREATE TABLE workout_cache (
                        {", ".join(columns_sql)}
                    )
                """)
                conn.commit()

            elif not self._schemas_match(current_schema, expected_schema):
                # Schema migration needed
                print("Database schema migration needed - preserving existing data...")

                # Get existing data
                cursor = conn.execute("SELECT * FROM workout_cache")
                existing_data = cursor.fetchall()

                # Get column names from current schema
                cursor = conn.execute("PRAGMA table_info(workout_cache)")
                current_columns = [row[1] for row in cursor.fetchall()]

                # Drop old table and create new one
                conn.execute("DROP TABLE workout_cache")
                columns_sql = []
                for col_name, col_type in expected_schema.items():
                    columns_sql.append(f"{col_name} {col_type}")

                conn.execute(f"""
                    CREATE TABLE workout_cache (
                        {", ".join(columns_sql)}
                    )
                """)

                # Find the first column containing "url" to use for migration
                url_column = None
                for col_name in current_columns:
                    if "url" in col_name.lower():
                        url_column = col_name
                        break

                # Re-insert existing data, ALL entries need update since they don't have canonical URLs
                migrated_count = 0
                for row in existing_data:
                    # Create a dict from existing row data
                    row_data = dict(zip(current_columns, row))

                    # Find URL from the first column containing "url"
                    original_url = None
                    if url_column and row_data.get(url_column):
                        original_url = self._clean_url(row_data[url_column])

                    # ALL existing entries need update since they lack canonical URLs
                    insert_columns = ["needs_update"]
                    insert_values = [1]

                    # Add original_url if we found one
                    if original_url:
                        insert_columns.append("original_url")
                        insert_values.append(original_url)

                    # Add other columns that exist in both schemas
                    for col in expected_schema.keys():
                        if col in row_data and col not in [
                            "canonical_url",
                            "original_url",
                            "needs_update",
                        ]:
                            insert_columns.append(col)
                            insert_values.append(row_data[col])

                    placeholders = ", ".join(["?" for _ in insert_values])
                    conn.execute(
                        f"INSERT INTO workout_cache ({', '.join(insert_columns)}) VALUES ({placeholders})",
                        insert_values,
                    )
                    migrated_count += 1

                conn.commit()

                # Count entries needing update
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM workout_cache WHERE needs_update = 1"
                )
                update_count = cursor.fetchone()[0]

                print(
                    f"Migrated {migrated_count} entries. {update_count} entries marked for update due to new schema requirements."
                )
            else:
                # Even if schema matches, ensure data consistency
                # Any entry without canonical_url should be marked for update
                cursor = conn.execute("""
                    UPDATE workout_cache 
                    SET needs_update = 1 
                    WHERE canonical_url IS NULL AND needs_update = 0
                """)
                fixed_count = cursor.rowcount
                if fixed_count > 0:
                    conn.commit()
                    print(
                        f"Fixed {fixed_count} entries missing canonical URLs - marked for update."
                    )

    def _get_cached_result(self, original_url):
        """Get cached result from database if it exists and is valid"""
        # Clean the URL first
        cleaned_url = self._clean_url(original_url)

        with sqlite3.connect(self.db_path) as conn:
            # Try to find by canonical_url or original_url
            cursor = conn.execute(
                """
                SELECT title, trainer, duration, genre, episode, workout_type, workout_category, date, datetime, songs_json, needs_update, canonical_url
                FROM workout_cache WHERE canonical_url = ? OR original_url = ?
            """,
                (cleaned_url, cleaned_url),
            )
            row = cursor.fetchone()
            if row:
                # If entry needs update or has no songs data, return None to force re-fetch
                if row[10] or not row[9]:  # needs_update or no songs_json
                    return None

                return {
                    "metadata": {
                        "title": row[0],
                        "trainer": row[1],
                        "duration": row[2],
                        "genre": row[3],
                        "episode": row[4],
                        "workout_type": row[5],
                        "workout_category": row[6],
                        "date": row[7],
                        "datetime": row[8],
                    },
                    "songs": json.loads(row[9]),
                    "canonical_url": row[11],
                }
        return None

    def _get_entries_needing_update(self):
        """Get count and list of entries that need updating"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM workout_cache 
                WHERE needs_update = 1 AND (original_url IS NOT NULL OR canonical_url IS NOT NULL)
            """)
            count = cursor.fetchone()[0]

            cursor = conn.execute("""
                SELECT COALESCE(original_url, canonical_url) FROM workout_cache 
                WHERE needs_update = 1 AND (original_url IS NOT NULL OR canonical_url IS NOT NULL)
            """)
            urls = [row[0] for row in cursor.fetchall()]

            return count, urls

    def _cache_result(self, original_url, workout_data, canonical_url):
        """Cache the workout result in the database"""
        metadata = workout_data["metadata"]
        cleaned_original_url = self._clean_url(original_url)

        # Extract workout category from canonical URL
        workout_category = self._extract_workout_category(canonical_url)

        with sqlite3.connect(self.db_path) as conn:
            # First, delete any existing entries for this URL (handles both canonical_url and original_url matches)
            # This is necessary because the primary key is canonical_url, but old entries may have canonical_url=NULL
            conn.execute(
                """
                DELETE FROM workout_cache 
                WHERE canonical_url = ? OR original_url = ?
            """,
                (canonical_url, cleaned_original_url),
            )

            # Then insert the new complete entry
            conn.execute(
                """
                INSERT INTO workout_cache 
                (canonical_url, original_url, title, trainer, duration, genre, episode, workout_type, workout_category, date, datetime, songs_json, needs_update) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
                (
                    canonical_url,
                    cleaned_original_url,
                    metadata.get("title"),
                    metadata.get("trainer"),
                    metadata.get("duration"),
                    metadata.get("genre"),
                    metadata.get("episode"),
                    metadata.get("workout_type"),
                    workout_category,
                    metadata.get("date"),
                    metadata.get("datetime"),
                    json.dumps(workout_data["songs"]),
                ),
            )
            conn.commit()

    def fetch_workout_page(self, url):
        """Fetch the Apple Fitness+ workout page"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching page: {e}")
            return None

    def extract_workout_data(self, html_content):
        """Extract workout metadata and songs from the HTML"""
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract workout metadata
        metadata = self._extract_metadata(soup)

        # Extract songs
        songs = []

        # Look for script tags containing JSON data
        script_tags = soup.find_all("script", type="application/ld+json")

        for script in script_tags:
            try:
                data = json.loads(script.string)
                # Look for workout data that might contain playlist info
                if isinstance(data, dict) and "workoutData" in str(data):
                    songs.extend(self._extract_from_json(data))
            except (json.JSONDecodeError, TypeError):
                continue

        # Fallback: look for song information in HTML structure
        if not songs:
            songs = self._extract_from_html(soup)

        return {"metadata": metadata, "songs": songs}

    def _extract_metadata(self, soup):
        """Extract workout metadata from HTML"""
        metadata = {}

        # Extract workout title
        title_element = soup.find("h1", class_="t-intro-elevated")
        if title_element:
            metadata["title"] = title_element.get_text(strip=True)

        # Extract metadata attributes (duration, genre, episode, date, type)
        metadata_list = soup.find("div", class_="workout-subcaption")
        if metadata_list:
            attributes = metadata_list.find_all("li", class_="metadata__attribute")

            for attr in attributes:
                text = attr.get_text(strip=True)

                # Parse different types of metadata
                if text.endswith("min"):
                    metadata["duration"] = text
                elif text.startswith("Ep"):
                    metadata["episode"] = text
                elif (
                    "Cycle" in text
                    or "Strength" in text
                    or "Yoga" in text
                    or "HIIT" in text
                ):
                    metadata["workout_type"] = text
                else:
                    # Check if it's a date
                    time_element = attr.find("time")
                    if time_element:
                        metadata["date"] = time_element.get_text(strip=True)
                        metadata["datetime"] = time_element.get("datetime")
                    else:
                        # Assume it's a genre if not caught by other conditions
                        if "genre" not in metadata:
                            metadata["genre"] = text

        # Extract trainer name
        trainer_link = soup.find("a", href=lambda x: x and "/trainer/" in x)
        if trainer_link:
            metadata["trainer"] = trainer_link.get_text(strip=True)

        return metadata

    def _extract_from_json(self, data):
        """Extract songs from JSON data structure"""
        songs = []

        def recursive_search(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key.lower() in ["tracks", "songs", "playlist", "music"]:
                        if isinstance(value, list):
                            for item in value:
                                if isinstance(item, dict):
                                    song_info = self._parse_song_dict(item)
                                    if song_info:
                                        songs.append(song_info)
                    recursive_search(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    recursive_search(item, f"{path}[{i}]")

        recursive_search(data)
        return songs

    def _parse_song_dict(self, song_dict):
        """Parse individual song dictionary"""
        title = (
            song_dict.get("name")
            or song_dict.get("title")
            or song_dict.get("trackName")
        )
        artist = None

        # Look for artist in various formats
        if "artist" in song_dict:
            artist_data = song_dict["artist"]
            if isinstance(artist_data, dict):
                artist = artist_data.get("name")
            elif isinstance(artist_data, str):
                artist = artist_data
        elif "by" in song_dict:
            artist = song_dict["by"]
        elif "performer" in song_dict:
            performer = song_dict["performer"]
            if isinstance(performer, dict):
                artist = performer.get("name")
            elif isinstance(performer, str):
                artist = performer

        apple_music_url = song_dict.get("url") or song_dict.get("link")

        if title:
            return {
                "title": title,
                "artist": artist or "Unknown Artist",
                "apple_music_url": apple_music_url,
            }
        return None

    def _extract_from_html(self, soup):
        """Extract songs from HTML structure using song-lockup class"""
        songs = []

        # Look for song-lockup figures which contain the song information
        song_figures = soup.find_all("figure", class_="song-lockup")

        for figure in song_figures:
            # Extract song title from the link
            title_link = figure.find("a", class_="song-lockup__song-name")
            if not title_link:
                continue

            title = title_link.get_text(strip=True)
            apple_music_url = title_link.get("href")

            # Extract artist name
            artist_div = figure.find("div", class_="song-lockup__artist-name")
            artist = artist_div.get_text(strip=True) if artist_div else "Unknown Artist"

            if title:
                songs.append(
                    {
                        "title": title,
                        "artist": artist,
                        "apple_music_url": apple_music_url,
                    }
                )

        return songs

    def get_workout_songs(self, original_url):
        """Main method to get workout data from a URL"""
        # Clean the URL first (remove query parameters)
        cleaned_url = self._clean_url(original_url)

        # Check cache first
        cached_data = self._get_cached_result(cleaned_url)
        if cached_data:
            print("Using cached result")
            return cached_data

        print("Fetching from server...")

        # Get the canonical URL for consistent metadata retrieval
        canonical_url = self._get_canonical_url(cleaned_url)
        print(f"Canonical URL: {canonical_url}")

        # Always fetch using the canonical URL for consistent metadata
        html_content = self.fetch_workout_page(canonical_url)
        if not html_content:
            return None

        workout_data = self.extract_workout_data(html_content)

        # Cache the result if data was found
        if workout_data and workout_data["songs"]:
            self._cache_result(original_url, workout_data, canonical_url)

        return workout_data

    def format_output(self, workout_data, format_type="list"):
        """Format the output in the requested format"""
        if not workout_data:
            return "No workout data found."

        if format_type.lower() == "json":
            return json.dumps(workout_data, indent=2, ensure_ascii=False)
        else:
            output = []
            metadata = workout_data.get("metadata", {})
            songs = workout_data.get("songs", [])

            # Add workout metadata
            if metadata.get("title"):
                output.append(f"🏋️ Workout: {metadata['title']}")
            if metadata.get("trainer"):
                output.append(f"👤 Trainer: {metadata['trainer']}")
            if metadata.get("duration"):
                output.append(f"⏱️ Duration: {metadata['duration']}")
            if metadata.get("workout_type"):
                output.append(f"🎯 Type: {metadata['workout_type']}")
            if metadata.get("genre"):
                output.append(f"🎵 Genre: {metadata['genre']}")
            if metadata.get("episode"):
                output.append(f"📺 Episode: {metadata['episode']}")
            if metadata.get("date"):
                output.append(f"📅 Date: {metadata['date']}")

            if songs:
                output.append(f"\n🎶 Playlist ({len(songs)} songs):")
                for i, song in enumerate(songs, 1):
                    line = f'{i}. "{song["title"]}" by {song["artist"]}'
                    if song.get("apple_music_url"):
                        line += f" - {song['apple_music_url']}"
                    output.append(line)

            return "\n".join(output)


def main():
    if len(sys.argv) < 2:
        print("Usage: python apple_fitness_scraper.py <workout_url> [format]")
        print("Format options: list (default), json")
        sys.exit(1)

    url = sys.argv[1]
    format_type = sys.argv[2] if len(sys.argv) > 2 else "list"

    scraper = AppleFitnessScraper()

    # Check for entries needing update
    count, urls = scraper._get_entries_needing_update()
    if count > 0:
        print(
            f"📝 Note: {count} cached entries need updating (use web frontend to update them)"
        )
        print()

    workout_data = scraper.get_workout_songs(url)

    if not workout_data or not workout_data.get("songs"):
        print("No workout data found or unable to fetch the workout page.")
        sys.exit(1)

    print(scraper.format_output(workout_data, format_type))


if __name__ == "__main__":
    main()
