import requests
import json
import time
from typing import List, Dict, Any

class AbyssHubScraper:
    def __init__(self, bearer_token: str):
        self.base_url = "https://api.abysshub.com/api/products/search"
        self.headers = {
            "accept": "application/json",
            "authorization": f"Bearer {bearer_token}",
            "origin": "https://abysshub.com",
            "referer": "https://abysshub.com/",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
        }
        self.per_page = 10

    def scrape_all_products(self, query: str = "", tags: str = "", must_not: str = "") -> List[Dict[str, Any]]:
        """
        Scrape all products from the API using pagination.

        Args:
            query: Search query string
            tags: Tags to filter by
            must_not: Tags to exclude

        Returns:
            List of all products
        """
        all_products = []
        from_offset = 0

        while True:
            params = {
                "query": query,
                "tags": tags,
                "must_not": must_not,
                "from": from_offset
            }

            print(f"Fetching products from offset {from_offset}...")

            try:
                response = requests.get(
                    self.base_url,
                    headers=self.headers,
                    params=params,
                    timeout=10
                )
                response.raise_for_status()

                data = response.json()
                products = data.get("data", [])
                meta = data.get("meta", {})

                all_products.extend(products)

                print(f"Retrieved {len(products)} products. Total so far: {len(all_products)}")

                # Check if we've reached the last page
                total = meta.get("total", 0)
                last_record = meta.get("last_record", 0)

                if from_offset >= last_record or len(products) == 0:
                    print(f"Reached last page. Total products: {len(all_products)}")
                    break

                from_offset += self.per_page

                # Be polite to the API
                time.sleep(0.5)

            except requests.exceptions.RequestException as e:
                print(f"Error fetching data: {e}")
                break

        return all_products

    def save_to_file(self, products: List[Dict[str, Any]], filename: str = "abysshub_products.json"):
        """Save scraped products to a JSON file."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(products, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(products)} products to {filename}")


if __name__ == "__main__":
    # Replace with your actual bearer token
    BEARER_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiIxMzAzIiwianRpIjoiMzk4MjMzNWY1NWFhZTc0NGU0Yjc2MmMzMmYwZWNlODVkZDMxMzdhZjU5NGIxMDQ4YWNhOThjYjM5MzNiNWY1NmUwMWU5M2RiNGM0N2VhNzYiLCJpYXQiOjE3NTk2MTQ4MjEuNDQ1NDg2LCJuYmYiOjE3NTk2MTQ4MjEuNDQ1NDg4LCJleHAiOjE3NzUzMzk2MjEuNDI0NDMzLCJzdWIiOiI3NzYiLCJzY29wZXMiOltdfQ.dZOgVrYytMEzVwc6qMD6ehEqkLfRUXM44VfXb9yVnGgiA5nAmkW6AawZ89ES-mUQIfYEyyBHJTdaKL1WxBgcqhoyew2RWDj5V0692bR4pmZDBkabpxyvashiWK6RralYopEUn03ROfzHV-pAnDg0biNXg-uVc9Spr5MW8oocxqtdpsSCeEbTqygj4Sb-UQlcLAPygsjp6ya3zvM60-TXsUzejDMUAU_TkfQdymX13ZAF9RUR4aTzJblKW4PvFJIJirWvyHPC_gH6S9Gj5KbARgeXbuJlfIuorSGr2AsxloloI4WVf5coPWXGeiD-RDmLpOGciV1oyaaqOtF9bD03aaFroZlR3mdHn4TQWfvQAMCnDrYlDZEc1qRr5Ow8kf89Q301MqDCGEOPs1jvXqfrZU46XyZ6_6ux-KP2YKNVRB84YCly57wIWpAhNkHu9ewSzgMawIfWIFyw6C9mXyifdexXYNYXoovuOahhPy6fcl45gj9eE7y-Iw6n4-jdQQTvxGHZS-wWNAov933rFH4NajsTJadwt5NTrZsCyxioQ7pKlyWHA-VKwydt6nDbXmB130F6Mha-50FJ9Ubi4YgIClwBQmqrP4SLOur5yGrpL31NqARSvpGymwI4nH86J8GRDXfBPJYTYP-gYp1dQSSgsnswfiB1a6hnKeui5lWreAI"

    scraper = AbyssHubScraper(BEARER_TOKEN)

    # Scrape all products
    products = scraper.scrape_all_products()

    # Save to file
    scraper.save_to_file(products)

    # Print summary
    print(f"\nScraping complete!")
    print(f"Total products scraped: {len(products)}")
