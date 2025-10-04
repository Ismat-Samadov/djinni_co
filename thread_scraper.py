import requests
import json
import time
from typing import List, Dict, Any, Optional

class AbyssHubThreadScraper:
    def __init__(self, bearer_token: str):
        self.base_url = "https://api.abysshub.com/api/threads/search"
        self.headers = {
            "accept": "application/json",
            "authorization": f"Bearer {bearer_token}",
            "origin": "https://abysshub.com",
            "referer": "https://abysshub.com/",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
        }
        self.per_page = 10

    def scrape_all_threads(
        self,
        language: str = "",
        query: str = "",
        sorting: str = "top",
        tags: str = "",
        must_not: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Scrape all threads from the API using pagination.

        Args:
            language: Programming language filter (e.g., "python", "javascript")
            query: Search query string
            sorting: Sorting method (e.g., "top", "recent")
            tags: Tags to filter by
            must_not: Tags to exclude

        Returns:
            List of all threads
        """
        all_threads = []
        from_offset = 0

        while True:
            params = {
                "language": language,
                "query": query,
                "sorting": sorting,
                "tags": tags,
                "must_not": must_not,
                "from": from_offset
            }

            print(f"Fetching threads from offset {from_offset}...")

            try:
                response = requests.get(
                    self.base_url,
                    headers=self.headers,
                    params=params,
                    timeout=10
                )
                response.raise_for_status()

                data = response.json()
                threads = data.get("data", [])
                meta = data.get("meta", {})

                all_threads.extend(threads)

                print(f"Retrieved {len(threads)} threads. Total so far: {len(all_threads)}")

                # Check if we've reached the last page
                total = meta.get("total", 0)
                last_record = meta.get("last_record", 0)

                if from_offset >= last_record or len(threads) == 0:
                    print(f"Reached last page. Total threads: {len(all_threads)}")
                    break

                from_offset += self.per_page

                # Be polite to the API
                time.sleep(0.5)

            except requests.exceptions.RequestException as e:
                print(f"Error fetching data: {e}")
                break

        return all_threads

    def scrape_all_languages(
        self,
        languages: Optional[List[str]] = None,
        sorting: str = "top"
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scrape threads for multiple languages.

        Args:
            languages: List of language filters (if None, scrapes all)
            sorting: Sorting method

        Returns:
            Dictionary mapping language to list of threads
        """
        if languages is None:
            languages = ["", "python", "javascript", "java", "go", "rust", "typescript"]

        results = {}
        for language in languages:
            print(f"\n{'='*50}")
            print(f"Scraping threads for language: {language or 'all'}")
            print(f"{'='*50}\n")

            threads = self.scrape_all_threads(language=language, sorting=sorting)
            results[language or "all"] = threads

            # Be polite between language requests
            time.sleep(1)

        return results

    def save_to_file(self, threads: List[Dict[str, Any]], filename: str = "abysshub_threads.json"):
        """Save scraped threads to a JSON file."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(threads, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(threads)} threads to {filename}")

    def save_all_languages(self, results: Dict[str, List[Dict[str, Any]]], filename: str = "abysshub_threads_by_language.json"):
        """Save scraped threads by language to a JSON file."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        total = sum(len(threads) for threads in results.values())
        print(f"\nSaved {total} total threads across {len(results)} language categories to {filename}")


if __name__ == "__main__":
    # Replace with your actual bearer token
    BEARER_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiIxMzAzIiwianRpIjoiMzk4MjMzNWY1NWFhZTc0NGU0Yjc2MmMzMmYwZWNlODVkZDMxMzdhZjU5NGIxMDQ4YWNhOThjYjM5MzNiNWY1NmUwMWU5M2RiNGM0N2VhNzYiLCJpYXQiOjE3NTk2MTQ4MjEuNDQ1NDg2LCJuYmYiOjE3NTk2MTQ4MjEuNDQ1NDg4LCJleHAiOjE3NzUzMzk2MjEuNDI0NDMzLCJzdWIiOiI3NzYiLCJzY29wZXMiOltdfQ.dZOgVrYytMEzVwc6qMD6ehEqkLfRUXM44VfXb9yVnGgiA5nAmkW6AawZ89ES-mUQIfYEyyBHJTdaKL1WxBgcqhoyew2RWDj5V0692bR4pmZDBkabpxyvashiWK6RralYopEUn03ROfzHV-pAnDg0biNXg-uVc9Spr5MW8oocxqtdpsSCeEbTqygj4Sb-UQlcLAPygsjp6ya3zvM60-TXsUzejDMUAU_TkfQdymX13ZAF9RUR4aTzJblKW4PvFJIJirWvyHPC_gH6S9Gj5KbARgeXbuJlfIuorSGr2AsxloloI4WVf5coPWXGeiD-RDmLpOGciV1oyaaqOtF9bD03aaFroZlR3mdHn4TQWfvQAMCnDrYlDZEc1qRr5Ow8kf89Q301MqDCGEOPs1jvXqfrZU46XyZ6_6ux-KP2YKNVRB84YCly57wIWpAhNkHu9ewSzgMawIfWIFyw6C9mXyifdexXYNYXoovuOahhPy6fcl45gj9eE7y-Iw6n4-jdQQTvxGHZS-wWNAov933rFH4NajsTJadwt5NTrZsCyxioQ7pKlyWHA-VKwydt6nDbXmB130F6Mha-50FJ9Ubi4YgIClwBQmqrP4SLOur5yGrpL31NqARSvpGymwI4nH86J8GRDXfBPJYTYP-gYp1dQSSgsnswfiB1a6hnKeui5lWreAI"

    scraper = AbyssHubThreadScraper(BEARER_TOKEN)

    # Option 1: Scrape all threads (no language filter)
    print("Scraping all threads...")
    all_threads = scraper.scrape_all_threads()
    scraper.save_to_file(all_threads, "abysshub_threads_all.json")

    # Option 2: Scrape threads by language
    print("\n\nScraping threads by language...")
    threads_by_language = scraper.scrape_all_languages()
    scraper.save_all_languages(threads_by_language)

    # Print summary
    print(f"\n{'='*50}")
    print("Scraping complete!")
    print(f"{'='*50}")
    print(f"Total threads (all): {len(all_threads)}")
    for lang, threads in threads_by_language.items():
        print(f"Total threads ({lang}): {len(threads)}")
