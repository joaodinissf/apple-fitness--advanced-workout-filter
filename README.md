# Apple Fitness+ - Advanced Workout Filter

> **⚖️ Legal Notice**: This project is not affiliated with, endorsed by, or sponsored by Apple Inc. Apple, Apple Fitness+, Apple Music, and all related trademarks are the property of Apple Inc. This is an independent, educational project for personal use only.

A web-based tool for extracting, organizing, and filtering workout playlists from Apple Fitness+ workouts. This application allows you to build a searchable library of workouts with their complete song metadata, making it easy to find workouts based on music preferences.

## Features

- 🎵 **Workout Library**: Browse and search through your indexed Apple Fitness+ workouts
- 🔍 **Advanced Filtering**: Filter by category, trainer, genre, duration, and more
- 📊 **Smart Sorting**: Sort workouts by date, duration, or title
- 🎶 **Song Search**: Find workouts containing specific songs or artists
- ⚡ **Instant Search**: Keyboard shortcut support (Ctrl/Cmd+K) for quick access
- 🔄 **Auto-refresh**: Update workout metadata with a click
- 📱 **Responsive Design**: Works on desktop and mobile devices

## Screenshots

The application features a modern, intuitive interface with:

- Clean workout cards with metadata display
- Real-time search and filtering
- Comprehensive workout information including trainer, duration, genre, and complete playlist

## Installation

### Prerequisites

- Python 3.8 or higher
- uv (recommended) or pip for dependency management

### Setup

1. Clone the repository:

```bash
git clone https://github.com/joaodinissf/workio.git
cd workio
```

2. Create and activate a virtual environment:

```bash
# Using uv (recommended)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Or using pip
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:

```bash
# Using uv
uv pip install -r requirements.txt

# Or using pip
pip install -r requirements.txt
```

## Usage

### Web Interface

1. Start the Flask web server:

```bash
python web_frontend.py
```

2. Open your browser and navigate to `http://localhost:5000`

3. **Add Workouts**: Click "Add Workouts" and paste Apple Fitness+ workout URLs
4. **Browse Library**: Use the main page to search and filter your workout collection
5. **Search & Filter**: Use the search bar or filters to find specific workouts or songs

### Command Line

You can also use the scraper directly from the command line:

```bash
# Extract workout data
python apple_fitness_scraper.py "https://fitness.apple.com/us/workout/cycling-with-emily/1810544460"

# Output as JSON
python apple_fitness_scraper.py "https://fitness.apple.com/us/workout/cycling-with-emily/1810544460" json
```

## Supported URL Formats

The application supports various Apple Fitness+ URL formats:

- `https://fitness.apple.com/us/workout/category-with-trainer/ID`
- `https://fitness.apple.com/gb/workout/category-with-trainer/ID` (automatically normalized)
- URLs with query parameters (automatically cleaned)

## Database Management

The application includes several utility scripts for database maintenance (located in the `utils/` folder):

- `utils/cleanup_duplicates.py` - Remove duplicate entries
- `utils/invalidate_cache.py` - Mark all entries for refresh
- `utils/check_db_health.py` - Verify database integrity
- `utils/fetch_html.py` - Debug tool for fetching workout HTML

## Configuration

The application uses SQLite for data storage with automatic schema migration. The database file (`fitness_cache.db`) is created automatically and stores:

- Workout metadata (title, trainer, duration, genre, etc.)
- Complete song playlists with Apple Music links
- Caching information for performance optimization

**Custom Database Location**: If you have an existing database in a different location, you can create a symbolic link to it:

```bash
ln -s /path/to/your/custom/backup/fitness_cache.db ./fitness_cache.db
```

## Legal Notice

**This project is not affiliated with, endorsed by, or sponsored by Apple Inc.**

- Apple, Apple Fitness+, Apple Music, and all related trademarks are the property of Apple Inc.
- All other trademarks, service marks, and trade names referenced are the property of their respective owners.
- This is an independent, educational project for personal use only.

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
