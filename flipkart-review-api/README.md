# Flipkart Review API

A Python REST API and CLI tool that scrapes Flipkart product reviews, ratings, and metadata using Scrapy. Supports single-page, multi-page, and full review extraction. Returns structured JSON with review scores, text, reviewer info, and star distribution. Auto-bootstraps on Windows, macOS, and Linux — just run `python run.py`.

---

### Quick Start

```bash
python run.py                 # Auto-setup venv & start API server
python run.py crawl -a url="<FlipkartURL>" -o output.json  # Run scraper
python run.py test            # Run unit tests
```

**Platform launchers:**

| Platform | Command |
|---|---|
| macOS / Linux | `./run.sh` |
| Windows (CMD) | `run.bat` |
| Windows (PowerShell) | `.\run.ps1` |
| Docker | `docker compose up --build` |

---

### API Usage

```
GET /v1.0/reviews?page=1&url=<FlipkartProductURL>
GET /v1.0/reviews?page=all&url=<FlipkartProductURL>
GET /v1.0/reviews?max_pages=5&url=<FlipkartProductURL>
GET /health
```

### Example Response

```json
[
    {"product_price": "₹9999",
     "requested_url": "URL"},

    {"review_title": "Product Title",
     "avg_rating": "4.4",
     "total_ratings": "3,64,537 Ratings &",
     "total_reviews": "24,907 Reviews",
     "total_pages": "Page 1 of 2,491",
     "5": "2,50,327", "4": "67,635", "3": "22,835", "2": "7,656", "1": "16,084"},

    {"review_score": "5",
     "review_title": "Brilliant",
     "review_content": "The UI is super smooth and performs really well...",
     "reviewer_name": "Reviewer Name",
     "reviewer_location": "Reviewer Location",
     "reviewer_date": "Review Date",
     "permalink": "/reviews/permalink",
     "upvote": "6836",
     "downvote": "1292"}
]
```

### CLI Usage

```bash
python run.py crawl review -O output.json -a page=1 -a url="<FlipkartProductURL>"
```

### Requirements

- Python 3.9+ (everything else is installed automatically)
