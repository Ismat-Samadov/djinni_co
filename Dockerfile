FROM python:3.11-slim

WORKDIR /app

COPY widget_scraper.py thread_scraper.py scrape_all.py ./

RUN pip install --no-cache-dir requests

CMD ["python", "scrape_all.py"]
