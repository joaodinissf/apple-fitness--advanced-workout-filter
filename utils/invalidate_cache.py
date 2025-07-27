#!/usr/bin/env python3
"""
Cache Invalidation Script for Apple Fitness+ Scraper

This script marks all entries in the fitness_cache.db database as needing update,
effectively invalidating the entire cache.
"""

import sqlite3
import sys
from datetime import datetime


def invalidate_all_cache(db_path="fitness_cache.db"):
    """Mark all cache entries as needing update"""

    try:
        conn = sqlite3.connect(db_path)
        print(f"🗂️  Connecting to database: {db_path}")

        # Check current state
        cursor = conn.execute("SELECT COUNT(*) FROM workout_cache")
        total_count = cursor.fetchone()[0]

        if total_count == 0:
            print("ℹ️  Database is empty - nothing to invalidate")
            return True

        cursor = conn.execute(
            "SELECT COUNT(*) FROM workout_cache WHERE needs_update = 0"
        )
        valid_count = cursor.fetchone()[0]

        cursor = conn.execute(
            "SELECT COUNT(*) FROM workout_cache WHERE needs_update = 1"
        )
        invalid_count = cursor.fetchone()[0]

        print(f"📊 Current state:")
        print(f"   Total entries: {total_count}")
        print(f"   Valid entries: {valid_count}")
        print(f"   Already invalid: {invalid_count}")

        if valid_count == 0:
            print("✅ All entries are already marked for update")
            return True

        # Confirm action
        print(f"\n⚠️  This will mark {valid_count} entries as needing update.")
        print(
            "   This means they will be re-scraped from Apple Fitness+ on next access."
        )

        # Perform invalidation
        cursor = conn.execute("UPDATE workout_cache SET needs_update = 1")
        updated_count = cursor.rowcount
        conn.commit()

        print(f"✅ Successfully invalidated {updated_count} cache entries")

        # Verify results
        cursor = conn.execute(
            "SELECT COUNT(*) FROM workout_cache WHERE needs_update = 1"
        )
        final_invalid_count = cursor.fetchone()[0]

        cursor = conn.execute(
            "SELECT COUNT(*) FROM workout_cache WHERE needs_update = 0"
        )
        final_valid_count = cursor.fetchone()[0]

        print(f"📊 Final state:")
        print(f"   Entries needing update: {final_invalid_count}")
        print(f"   Valid entries: {final_valid_count}")

        if final_valid_count == 0:
            print("🎉 All cache entries successfully invalidated!")
        else:
            print(f"⚠️  Warning: {final_valid_count} entries still marked as valid")

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
        f"🚀 Starting cache invalidation at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print("=" * 60)

    success = invalidate_all_cache(db_path)

    print("\n" + "=" * 60)
    if success:
        print("✅ Cache invalidation completed successfully")
        print(
            "💡 Tip: Use the web frontend to update entries, or run individual URLs through the scraper"
        )
    else:
        print("❌ Cache invalidation failed")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
