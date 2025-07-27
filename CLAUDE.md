# Apple Fitness+ Advanced Workout Filter

## Important Commands

- Start dev server: `python web_frontend.py`
- Check database schema: `sqlite3 fitness_cache.db ".schema"`
- Invalidate cache: `python utils/invalidate_cache.py`
- Check database health: `python utils/check_db_health.py`
- Cleanup duplicates: `python utils/cleanup_duplicates.py`

## Critical Architecture Notes

### Database Backup is Symbolic Link

- NEVER manually copy `personal-backup/fitness_cache.db` - it's a symbolic link
- Changes to main database automatically reflect in backup
- When committing: `git add personal-backup/fitness_cache.db` after database changes

### Schema Migration System

- Always update `_get_expected_schema()` method in `apple_fitness_scraper.py` for schema changes
- System automatically migrates by recreating table and preserving data
- Missing canonical URLs trigger `needs_update = 1` flags
- UI "needs updating" warnings often mean canonical URLs are missing

### Rate Limiting

- Built-in delays when scraping Apple servers - don't remove these
- Aggressive scraping can get IP blocked
- Background processing uses threading and queues

## Key Files

- `apple_fitness_scraper.py` - Core scraper logic, database schema, URL handling
- `web_frontend.py` - Flask app, API endpoints, data serving
- `templates/index.html` - Main UI with embedded CSS/JS
- `fitness_cache.db` - Main SQLite database
- `utils/` - Database maintenance scripts

## Code Style

- Use 4 spaces for indentation
- Follow existing patterns for error handling
- Maintain rate limiting when scraping
- Test database schema changes with existing data

## Common Gotchas

1. Don't copy database backups - they're symbolic links
2. Schema migrations mark entries for updates if canonical URLs missing
3. Rate limiting is essential - don't remove delays when scraping
4. Update `_get_expected_schema()` method for any database changes

## Legal Compliance

- Careful about Apple trademark usage
- Position as independent educational project
- Rate limiting essential to avoid being blocked
