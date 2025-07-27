# Architecture & Development Notes

*Critical knowledge for working on this project*

## ⚠️ Critical Things to Know First

### Database Backup is a Symbolic Link

- **NEVER manually copy** `personal-backup/fitness_cache.db` - it's a symbolic link to the main database
- Changes to main database automatically reflect in backup
- When committing, just `git add personal-backup/fitness_cache.db` after database changes

### Schema Migration System

- **Schema definition**: Expected database schema defined in `_get_expected_schema()` method in `apple_fitness_scraper.py`
- **Migration trigger**: System detects schema mismatches using `_schemas_match()` method
- **Migration process**:
  1. Fetches all existing data with `SELECT * FROM workout_cache`
  2. Gets current column names with `PRAGMA table_info(workout_cache)`
  3. Drops old table with `DROP TABLE workout_cache`
  4. Creates new table with updated schema
  5. Migrates data, excluding `canonical_url`, `original_url`, and `needs_update` columns
  6. Auto-sets new columns to their default values
- **Data preservation**: All existing data is preserved, but excluded columns get default values
- **Auto-invalidation**: Missing canonical URLs trigger `needs_update = 1` flags via consistency checks
- **UI warnings**: "needs updating" messages often mean canonical URLs are missing

### Rate Limiting is Critical

- Built-in delays when scraping Apple's servers - **don't remove these**
- Background processing uses threading and queues for non-blocking operations
- Aggressive scraping can get IP blocked

## Key Files & What They Do

- `apple_fitness_scraper.py` - **Core scraper logic, database schema, URL handling**
- `web_frontend.py` - **Flask app, API endpoints, data serving**
- `templates/index.html` - **Main UI with embedded CSS/JS**
- `fitness_cache.db` - **Main SQLite database**
- `utils/` - Database maintenance scripts
- `personal-backup/` - Backup directory with symbolic link

## Database & Schema Management

- **Schema definition**: Expected database schema defined in `_get_expected_schema()` method
- **Migration strategy**: Recreates table and preserves data when schema changes
- **Consistency checks**: Entries without canonical URLs are automatically flagged for updates
- **JSON storage**: Complete playlists stored as JSON in `songs_json` column

## Architecture Overview

- **Flask web frontend**: `web_frontend.py` serves UI and API endpoints
- **Scraper core**: `apple_fitness_scraper.py` handles data extraction and database operations  
- **Template-based UI**: Uses Jinja2 templates with embedded JavaScript for interactivity
- **Background processing**: Threading and queues for non-blocking URL processing
- **Caching strategy**: SQLite database caches workout data to minimize repeated requests

## Data Flow Patterns

- **URL normalization**: Converts international Apple Fitness URLs to US format for consistency
- **Canonical vs original URLs**: Tracks both user input and canonical Apple URLs
- **Metadata extraction**: Pulls trainer, duration, genre, category, and song information
- **Real-time updates**: UI can trigger individual workout refreshes via API
- **Filtering system**: Client-side JavaScript filtering with server-side filter options endpoint

## Development Setup

- **Debug mode**: Currently runs in debug mode with `host="0.0.0.0"` for development
- **Database utilities**: Scripts in `utils/` for cache invalidation, duplicate cleanup, health checks
- **Error handling**: Comprehensive error handling for network requests and database operations
- **Thread safety**: Background processing uses proper threading patterns

## Legal & Compliance

- **Apple trademarks**: Careful about usage and positioning as independent educational project
- **Rate limiting**: Essential when scraping Apple's servers to avoid being blocked

## Common Gotchas & Mistakes

1. **Don't copy database backups** - they're symbolic links
2. **Schema migrations mark entries for updates** if canonical URLs are missing
3. **UI "needs updating" warnings** often due to missing canonical URLs  
4. **Rate limiting is essential** - don't remove delays when scraping
5. **Always test database schema changes** with existing data
6. **Update `_get_expected_schema()`** method for any database changes

## Claude Code Documentation

Based on Anthropic's best practices, this project should have:

### CLAUDE.md File

- **Project context**: Store team-shared instructions in `./CLAUDE.md`
- **Key commands**: Include `python web_frontend.py`, testing commands, lint commands
- **Code style**: Specify formatting preferences (spaces vs tabs, line length, etc.)
- **Architecture patterns**: Reference this file for schema migration patterns

### Recommended CLAUDE.md Structure

```markdown
# Apple Fitness+ Advanced Workout Filter

## Important Commands
- Start dev server: `python web_frontend.py`
- Check database: `sqlite3 fitness_cache.db ".schema"`
- Invalidate cache: `python utils/invalidate_cache.py`

## Schema Changes
- Always update `_get_expected_schema()` method
- System handles migration automatically
- Never manually alter database schema

## Critical Notes
- Database backup is symbolic link - don't copy manually
- Rate limiting essential when scraping Apple servers
```

This architecture demonstrates a well-designed approach to web scraping with proper caching, user experience, and maintainability.
