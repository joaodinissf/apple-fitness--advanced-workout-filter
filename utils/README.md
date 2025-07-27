# Utility Scripts

This folder contains utility scripts for database maintenance and debugging.

## Scripts

### `cleanup_duplicates.py`

Removes duplicate entries from the database, keeping the most recent/complete version of each workout.

```bash
python utils/cleanup_duplicates.py [database_path]
```

### `invalidate_cache.py`

Marks all entries in the database as needing update, effectively invalidating the entire cache.

```bash
python utils/invalidate_cache.py [database_path]
```

### `check_db_health.py`

Verifies database integrity and provides statistics about the cached data.

```bash
python utils/check_db_health.py [database_path]
```

### `fetch_html.py`

Debug tool for fetching and examining the raw HTML content from Apple Fitness+ workout pages.

```bash
python utils/fetch_html.py <workout_url>
```

## Usage Notes

- All scripts default to using `fitness_cache.db` in the project root if no database path is specified
- Make sure to stop the web server before running database maintenance scripts
- Always backup your database before running cleanup operations
