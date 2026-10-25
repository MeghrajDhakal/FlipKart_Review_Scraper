import json
import logging
import os
import subprocess
import sys
import tempfile

from flask import Flask, jsonify, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "name": "Flipkart Review API",
        "version": "1.0",
        "description": "API to scrape Flipkart product reviews, ratings, and price metadata",
        "endpoints": {
            "/v1.0/reviews": "GET reviews for a given Flipkart product URL, page, or page range",
            "/health": "GET service health status",
        },
        "usage": {
            "single_page": "/v1.0/reviews?page=1&url=<FlipkartProductOrReviewURL>",
            "multiple_pages": "/v1.0/reviews?max_pages=3&url=<FlipkartProductOrReviewURL>",
            "all_pages": "/v1.0/reviews?page=all&url=<FlipkartProductOrReviewURL>",
        },
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


@app.route("/v1.0/reviews", methods=["GET"])
def get_reviews():
    url = request.args.get("url", "").strip()
    if not url:
        return jsonify({
            "error": "Bad Request",
            "message": "Missing required 'url' parameter",
        }), 400

    page_param = request.args.get("page", "").strip()
    max_pages_param = request.args.get("max_pages", "").strip()

    spider_name = "review"

    # Use an isolated temporary file to prevent race conditions during concurrent requests
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_output_path = tmp.name

    try:
        cmd = [
            sys.executable,
            "-m",
            "scrapy",
            "crawl",
            spider_name,
            "-O",
            tmp_output_path,
            "-a",
            f"url={url}",
        ]
        if page_param:
            cmd.extend(["-a", f"page={page_param}"])
        else:
            cmd.extend(["-a", "page=1"])

        if max_pages_param:
            cmd.extend(["-a", f"max_pages={max_pages_param}"])

        # Determine reasonable timeout based on whether multiple pages are scraped
        timeout = 300 if (page_param.lower() in ("all", "0", "*") or max_pages_param) else 60

        logger.info("Executing Scrapy command: %s", " ".join(cmd))
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            logger.error(
                "Scrapy crawl failed with code %s:\n%s", result.returncode, result.stderr
            )
            return jsonify({
                "error": "Scraping failed",
                "details": result.stderr[-500:] if result.stderr else "Unknown error",
            }), 502

        if os.path.exists(tmp_output_path) and os.path.getsize(tmp_output_path) > 0:
            with open(tmp_output_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return jsonify(data), 200
        else:
            return jsonify([]), 200

    except subprocess.TimeoutExpired:
        logger.error("Scrapy crawl timed out for url: %s", url)
        return jsonify({
            "error": "Gateway Timeout",
            "message": "Scraper timed out while fetching reviews",
        }), 504
    except json.JSONDecodeError as e:
        logger.error("JSON decode error reading scraper output: %s", e)
        return jsonify({
            "error": "Failed to parse scraper output",
            "message": str(e),
        }), 500
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e),
        }), 500
    finally:
        if os.path.exists(tmp_output_path):
            try:
                os.remove(tmp_output_path)
            except OSError:
                pass


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
