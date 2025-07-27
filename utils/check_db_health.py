#!/usr/bin/env python3
"""
Database Health Check Script for Apple Fitness+ Scraper

This script analyzes the fitness_cache.db database and reports on its health,
structure, and data integrity.
"""

import sqlite3
import json
import sys
from datetime import datetime


def check_db_health(db_path="fitness_cache.db"):
    """Comprehensive database health check"""

    try:
        conn = sqlite3.connect(db_path)
        print(f"🔍 Checking database: {db_path}")
        print("=" * 60)

        # Check table structure
        print("\n=== DATABASE SCHEMA ===")
        cursor = conn.execute("PRAGMA table_info(workout_cache)")
        schema_info = cursor.fetchall()

        if not schema_info:
            print("❌ No workout_cache table found!")
            return False

        for row in schema_info:
            pk_indicator = " (PRIMARY KEY)" if row[5] else ""
            default_val = f" DEFAULT {row[4]}" if row[4] is not None else ""
            not_null = " NOT NULL" if row[3] else ""
            print(f"  {row[1]}: {row[2]}{default_val}{not_null}{pk_indicator}")

        # Basic stats
        print("\n=== DATABASE STATS ===")
        cursor = conn.execute("SELECT COUNT(*) FROM workout_cache")
        total_count = cursor.fetchone()[0]
        print(f"📊 Total entries: {total_count}")

        if total_count == 0:
            print("ℹ️  Database is empty")
            return True

        cursor = conn.execute(
            "SELECT COUNT(*) FROM workout_cache WHERE needs_update = 1"
        )
        needs_update_count = cursor.fetchone()[0]
        print(f"🔄 Entries needing update: {needs_update_count}")

        cursor = conn.execute(
            "SELECT COUNT(*) FROM workout_cache WHERE canonical_url IS NOT NULL"
        )
        canonical_count = cursor.fetchone()[0]
        print(f"🔗 Entries with canonical URL: {canonical_count}")

        cursor = conn.execute(
            "SELECT COUNT(*) FROM workout_cache WHERE original_url IS NOT NULL"
        )
        original_count = cursor.fetchone()[0]
        print(f"📝 Entries with original URL: {original_count}")

        # Sample data
        print("\n=== SAMPLE DATA ===")
        cursor = conn.execute("""
            SELECT canonical_url, original_url, title, needs_update, trainer, workout_type, workout_category, songs_json 
            FROM workout_cache 
            ORDER BY cached_at DESC 
            LIMIT 5
        """)

        for i, row in enumerate(cursor.fetchall(), 1):
            (
                canonical,
                original,
                title,
                needs_update,
                trainer,
                workout_type,
                workout_category,
                songs_json,
            ) = row
            songs_count = 0
            if songs_json:
                try:
                    songs = json.loads(songs_json)
                    songs_count = len(songs) if isinstance(songs, list) else 0
                except:
                    songs_count = "ERROR"

            print(f"{i}. {title or 'Untitled'}")
            print(f"   👤 Trainer: {trainer or 'Unknown'}")
            print(f"   🏃 Category: {workout_category or 'Unknown'}")
            print(f"   🎯 Type: {workout_type or 'Unknown'}")
            print(f"   🎵 Songs: {songs_count}")
            print(f"   🔗 Canonical: {canonical or 'None'}")
            print(f"   📝 Original: {original or 'None'}")
            print(f"   🔄 Needs update: {bool(needs_update)}")
            print()

        # Data integrity checks
        print("=== DATA INTEGRITY CHECKS ===")

        # Check for orphaned entries
        cursor = conn.execute("""
            SELECT COUNT(*) FROM workout_cache 
            WHERE canonical_url IS NULL AND original_url IS NULL
        """)
        orphaned_count = cursor.fetchone()[0]
        if orphaned_count > 0:
            print(f"⚠️  Orphaned entries (no URLs): {orphaned_count}")
        else:
            print("✅ No orphaned entries found")

        # Check for entries with songs
        cursor = conn.execute("""
            SELECT COUNT(*) FROM workout_cache 
            WHERE songs_json IS NOT NULL AND songs_json != '[]' AND songs_json != 'null'
        """)
        with_songs_count = cursor.fetchone()[0]
        print(f"🎵 Entries with songs: {with_songs_count}")

        # Check for empty songs
        cursor = conn.execute("""
            SELECT COUNT(*) FROM workout_cache 
            WHERE songs_json IS NULL OR songs_json = '[]' OR songs_json = 'null'
        """)
        empty_songs_count = cursor.fetchone()[0]
        print(f"🔇 Entries with no songs: {empty_songs_count}")

        # URL normalization check
        print("\n=== URL NORMALIZATION CHECK ===")
        cursor = conn.execute("""
            SELECT original_url, canonical_url 
            FROM workout_cache 
            WHERE original_url IS NOT NULL AND canonical_url IS NOT NULL 
            AND original_url != canonical_url
        """)
        normalized_entries = cursor.fetchall()
        print(f"🌐 URLs that were normalized: {len(normalized_entries)}")

        if normalized_entries:
            print("Examples:")
            for orig, canon in normalized_entries[:3]:
                print(f"  📥 {orig}")
                print(f"  📤 {canon}")
                print()

        # Content analysis
        print("=== CONTENT ANALYSIS ===")

        # Trainers
        cursor = conn.execute("""
            SELECT DISTINCT trainer 
            FROM workout_cache 
            WHERE trainer IS NOT NULL 
            ORDER BY trainer
        """)
        trainers = [row[0] for row in cursor.fetchall()]
        print(
            f"👥 Trainers ({len(trainers)}): {', '.join(trainers) if trainers else 'None'}"
        )

        # Workout categories
        cursor = conn.execute("""
            SELECT DISTINCT workout_category 
            FROM workout_cache 
            WHERE workout_category IS NOT NULL 
            ORDER BY workout_category
        """)
        workout_categories = [row[0] for row in cursor.fetchall()]
        print(
            f"🏃 Workout categories ({len(workout_categories)}): {', '.join(workout_categories) if workout_categories else 'None'}"
        )

        # Workout types
        cursor = conn.execute("""
            SELECT DISTINCT workout_type 
            FROM workout_cache 
            WHERE workout_type IS NOT NULL 
            ORDER BY workout_type
        """)
        workout_types = [row[0] for row in cursor.fetchall()]
        print(
            f"🎯 Workout types ({len(workout_types)}): {', '.join(workout_types) if workout_types else 'None'}"
        )

        # Genres
        cursor = conn.execute("""
            SELECT DISTINCT genre 
            FROM workout_cache 
            WHERE genre IS NOT NULL 
            ORDER BY genre
        """)
        genres = [row[0] for row in cursor.fetchall()]
        print(
            f"🎵 Music genres ({len(genres)}): {', '.join(genres) if genres else 'None'}"
        )

        # Durations
        cursor = conn.execute("""
            SELECT DISTINCT duration 
            FROM workout_cache 
            WHERE duration IS NOT NULL 
            ORDER BY duration
        """)
        durations = [row[0] for row in cursor.fetchall()]
        print(
            f"⏱️  Durations ({len(durations)}): {', '.join(durations) if durations else 'None'}"
        )

        # Recent activity
        print("\n=== RECENT ACTIVITY ===")
        cursor = conn.execute("""
            SELECT COUNT(*), DATE(cached_at) as date
            FROM workout_cache 
            WHERE cached_at IS NOT NULL 
            GROUP BY DATE(cached_at) 
            ORDER BY date DESC 
            LIMIT 7
        """)
        recent_activity = cursor.fetchall()

        if recent_activity:
            print("📅 Entries added by date:")
            for count, date in recent_activity:
                print(f"  {date}: {count} entries")
        else:
            print("📅 No recent activity found")

        # Health summary
        print("\n=== HEALTH SUMMARY ===")
        health_score = 0
        max_score = 5

        if total_count > 0:
            health_score += 1
            print("✅ Database has data")
        else:
            print("⚠️  Database is empty")

        if orphaned_count == 0:
            health_score += 1
            print("✅ No orphaned entries")
        else:
            print(f"❌ {orphaned_count} orphaned entries found")

        if canonical_count > 0:
            health_score += 1
            print("✅ Canonical URLs present")
        else:
            print("⚠️  No canonical URLs found")

        if with_songs_count > 0:
            health_score += 1
            print("✅ Song data present")
        else:
            print("⚠️  No song data found")

        if normalized_entries:
            health_score += 1
            print("✅ URL normalization working")
        else:
            print("ℹ️  No URL normalization examples (may be normal)")
            health_score += 1  # Not necessarily bad

        print(
            f"\n🏥 Overall health: {health_score}/{max_score} ({'Good' if health_score >= 4 else 'Needs attention'})"
        )

        conn.close()
        return True

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "fitness_cache.db"
    print(
        f"🚀 Starting database health check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    success = check_db_health(db_path)
    sys.exit(0 if success else 1)
