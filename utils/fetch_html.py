#!/usr/bin/env python3
"""Fetch Apple Fitness+ page HTML for local development"""

import requests
import sys


def fetch_page(url, output_file):
    """Fetch the HTML page and save it locally"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        print(f"Fetching {url}...")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(response.text)

        print(f"HTML saved to {output_file}")
        print(f"File size: {len(response.text)} characters")

    except requests.RequestException as e:
        print(f"Error fetching page: {e}")


if __name__ == "__main__":
    url = "https://fitness.apple.com/us/workout/cycling-with-emily/1810544460"
    output_file = "workout_page.html"

    if len(sys.argv) > 1:
        url = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    fetch_page(url, output_file)
