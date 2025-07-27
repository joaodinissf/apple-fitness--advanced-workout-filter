#!/usr/bin/env python3
"""
Database Cleanup Script for Apple Fitness+ Scraper

This script removes duplicate entries, keeping the most recent/complete version
of each workout (the one with canonical_url populated).
"""

import sqlite3
import sys
from datetime import datetime


def cleanup_duplicates(db_path="fitness_cache.db"):
    """Remove duplicate entries, keeping the best version of each"""

    try:
        conn = sqlite3.connect(db_path)
        print(f"🗂️  Cleaning up duplicates in: {db_path}")

        # First, let's see what we're working with
        cursor = conn.execute("SELECT COUNT(*) FROM workout_cache")
        total_before = cursor.fetchone()[0]
        print(f"📊 Total entries before cleanup: {total_before}")

        # Find URLs that have duplicates
        cursor = conn.execute("""
            SELECT url, COUNT(*) as count
            FROM (
                SELECT COALESCE(canonical_url, original_url) as url
                FROM workout_cache
                WHERE url IS NOT NULL
            )
            GROUP BY url
            HAVING COUNT(*) > 1
        """)

        duplicates = cursor.fetchall()
        print(f"🔍 Found {len(duplicates)} URLs with duplicates")

        if not duplicates:
            print("✅ No duplicates found!")
            return True

        deleted_count = 0

        for url, count in duplicates:
            print(f"\n🔄 Processing {url} ({count} entries)...")

            # Get all entries for this URL, ordered by preference
            # Priority: 1) Has canonical_url, 2) Most recent cached_at, 3) Has category
            cursor = conn.execute(
                """
                SELECT rowid, canonical_url, original_url, needs_update, workout_category, cached_at
                FROM workout_cache 
                WHERE canonical_url = ? OR original_url = ?
                ORDER BY 
                    (canonical_url IS NOT NULL) DESC,
                    cached_at DESC,
                    (workout_category IS NOT NULL) DESC
            """,
                (url, url),
            )

            entries = cursor.fetchall()

            if len(entries) <= 1:
                continue

            # Keep the first entry (best one), delete the rest
            keep_entry = entries[0]
            delete_entries = entries[1:]

            print(
                f"   ✅ Keeping: rowid={keep_entry[0]}, canonical={keep_entry[1] is not None}, "
                f"category={keep_entry[4]}, cached_at={keep_entry[5]}"
            )

            for delete_entry in delete_entries:
                print(
                    f"   🗑️  Deleting: rowid={delete_entry[0]}, canonical={delete_entry[1] is not None}, "
                    f"category={delete_entry[4]}, cached_at={delete_entry[5]}"
                )

                cursor = conn.execute(
                    "DELETE FROM workout_cache WHERE rowid = ?", (delete_entry[0],)
                )
                deleted_count += 1

        conn.commit()

        # Final stats
        cursor = conn.execute("SELECT COUNT(*) FROM workout_cache")
        total_after = cursor.fetchone()[0]

        print(f"\n📊 Cleanup Summary:")
        print(f"   Entries before: {total_before}")
        print(f"   Entries deleted: {deleted_count}")
        print(f"   Entries after: {total_after}")
        print(f"   Space saved: {deleted_count} duplicate entries")

        # Verify no duplicates remain
        cursor = conn.execute("""
            SELECT COUNT(*) FROM (
                SELECT url, COUNT(*) as count
                FROM (
                    SELECT COALESCE(canonical_url, original_url) as url
                    FROM workout_cache
                    WHERE url IS NOT NULL
                )
                GROUP BY url
                HAVING COUNT(*) > 1
            )
        """)

        remaining_duplicates = cursor.fetchone()[0]
        if remaining_duplicates == 0:
            print("✅ All duplicates successfully removed!")
        else:
            print(f"⚠️  Warning: {remaining_duplicates} URLs still have duplicates")

        conn.close()
        return True

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def main():
    """Main function"""
    db_path = sys.argv[1] if len(sys.argv) > 1 else "fitness_cache.db"

    print(
        f"🚀 Starting duplicate cleanup at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print("=" * 60)

    success = cleanup_duplicates(db_path)

    print("\n" + "=" * 60)
    if success:
        print("✅ Duplicate cleanup completed successfully")
        print("💡 Tip: Run check_db_health.py to verify the database state")
    else:
        print("❌ Duplicate cleanup failed")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
