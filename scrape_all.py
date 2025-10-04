import subprocess
import sys

def main():
    print("=" * 60)
    print("Starting AbyssHub Scraping - All Scrapers")
    print("=" * 60)

    # Run widget scraper
    print("\n[1/2] Running Widget Scraper...")
    print("-" * 60)
    widget_result = subprocess.run([sys.executable, "widget_scraper.py"])

    # Run thread scraper
    print("\n[2/2] Running Thread Scraper...")
    print("-" * 60)
    thread_result = subprocess.run([sys.executable, "thread_scraper.py"])

    # Summary
    print("\n" + "=" * 60)
    print("Scraping Complete - Summary")
    print("=" * 60)
    print(f"Widget Scraper: {'✓ Success' if widget_result.returncode == 0 else '✗ Failed'}")
    print(f"Thread Scraper: {'✓ Success' if thread_result.returncode == 0 else '✗ Failed'}")
    print("=" * 60)

if __name__ == "__main__":
    main()
