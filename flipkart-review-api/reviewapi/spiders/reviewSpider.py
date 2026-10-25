import json
import math
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import scrapy


class ReviewSpider(scrapy.Spider):
    name = "review"

    SORT_ORDERS = ["MOST_HELPFUL", "MOST_RECENT", "NEGATIVE_FIRST", "POSITIVE_FIRST"]

    def __init__(self, url="", page=1, max_pages=None, sort=None, all_sorts=None, *args, **kwargs):
        super(ReviewSpider, self).__init__(*args, **kwargs)
        self.start_url = (url or "").strip()
        self.sort = sort

        # Check if page is set to 'all'
        page_str = str(page).strip().lower()
        if page_str in ("all", "0", "*"):
            self.scrape_all = True
            self.start_page = 1
            self.target_max_pages = None
        else:
            self.scrape_all = False
            try:
                self.start_page = int(page)
            except (ValueError, TypeError):
                self.start_page = 1

        if max_pages is not None:
            mp_str = str(max_pages).strip().lower()
            if mp_str in ("all", "0", "*", "none"):
                self.scrape_all = True
                self.target_max_pages = None
            else:
                try:
                    self.target_max_pages = int(max_pages)
                    self.scrape_all = True
                except (ValueError, TypeError):
                    pass
        else:
            if not self.scrape_all:
                self.target_max_pages = self.start_page

        # all_sorts controls whether we crawl across all Flipkart sort filters
        if all_sorts is not None:
            self.all_sorts = str(all_sorts).strip().lower() in ("true", "1", "yes", "all")
        else:
            # By default, crawl all sort filters when full scraping (page=all and no fixed max_pages)
            self.all_sorts = self.scrape_all and (self.target_max_pages is None)

        self.summary_yielded = False
        self.seen_reviews = set()
        self.total_pages = 1

    async def start(self):
        """Asynchronous entry point for Scrapy 2.13+."""
        for request in self.start_requests():
            yield request

    def start_requests(self):
        """Synchronous entry point for Scrapy backward compatibility."""
        if not self.start_url:
            self.logger.error("No URL provided. Use -a url=<FlipkartURL>")
            return

        # If it's a product page URL (/p/), scrape product page first for price, then follow review page
        if "/p/" in self.start_url and "/product-reviews/" not in self.start_url:
            yield scrapy.Request(
                url=self.start_url,
                callback=self.parse_product,
                meta={"current_page": self.start_page},
                dont_filter=True,
            )
        else:
            # If it's already a review page URL or general URL
            if self.all_sorts:
                for s_order in self.SORT_ORDERS:
                    rev_url = self._build_review_url(self.start_url, 1, sort_order=s_order)
                    yield scrapy.Request(
                        url=rev_url,
                        callback=self.parse_reviews,
                        meta={"current_page": 1, "sort_order": s_order},
                        dont_filter=True,
                    )
            else:
                review_url = self._build_review_url(self.start_url, self.start_page, sort_order=self.sort)
                yield scrapy.Request(
                    url=review_url,
                    callback=self.parse_reviews,
                    meta={"current_page": self.start_page, "sort_order": self.sort},
                    dont_filter=True,
                )

    def _build_review_url(self, url, page=1, sort_order=None):
        parsed = urlparse(url)
        path = parsed.path
        if "/p/" in path:
            path = path.replace("/p/", "/product-reviews/")

        query = parse_qs(parsed.query)
        query["page"] = [str(page)]
        if sort_order:
            query["sortOrder"] = [str(sort_order)]
        new_query = urlencode(query, doseq=True)

        scheme = parsed.scheme or "https"
        netloc = parsed.netloc or "www.flipkart.com"
        return urlunparse((scheme, netloc, path, parsed.params, new_query, parsed.fragment))

    def _extract_initial_state(self, response):
        """Extract Flipkart React hydration state (window.__INITIAL_STATE__)."""
        script_text = response.xpath('//script[@id="is_script"]/text()').get()
        if not script_text:
            script_text = response.css("script#is_script::text").get()

        if not script_text:
            match = re.search(
                r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});?\s*</script>",
                response.text,
                re.DOTALL,
            )
            if match:
                script_text = match.group(1)

        if script_text:
            try:
                json_str = re.sub(r"^\s*window\.__INITIAL_STATE__\s*=\s*", "", script_text.strip())
                json_str = re.sub(r";\s*$", "", json_str)
                return json.loads(json_str)
            except Exception as e:
                self.logger.warning("Failed to decode __INITIAL_STATE__ JSON: %s", e)
        return None

    def parse_product(self, response):
        """Parses the Flipkart product page to extract product price and navigates to reviews."""
        price = None
        state = self._extract_initial_state(response)

        if state:
            schemas = (
                state.get("multiWidgetState", {})
                .get("pageDataResponse", {})
                .get("seoData", {})
                .get("schema", [])
            )
            for s in schemas:
                if isinstance(s, dict) and "offers" in s:
                    offers = s.get("offers", {})
                    if isinstance(offers, dict) and "price" in offers:
                        price = str(offers["price"])
                        break

            if not price:
                events = (
                    state.get("multiWidgetState", {})
                    .get("pageDataResponse", {})
                    .get("pageContext", {})
                    .get("fdpEventTracking", {})
                    .get("events", {})
                )
                ppd = events.get("psi", {}).get("ppd", {})
                if "finalPrice" in ppd:
                    price = str(ppd["finalPrice"])

        # Check JSON-LD fallback in DOM
        if not price:
            for s_tag in response.xpath('//script[@type="application/ld+json"]/text()').getall():
                try:
                    sd = json.loads(s_tag)
                    if isinstance(sd, list):
                        sd = sd[0]
                    if isinstance(sd, dict) and "offers" in sd:
                        p_val = sd["offers"].get("price")
                        if p_val:
                            price = str(p_val)
                            break
                except Exception:
                    pass

        # Regex fallback on raw HTML for price
        if not price:
            match = re.search(r"₹\s*([0-9,]+)", response.text)
            if match:
                price = match.group(1).replace(",", "")

        if price:
            formatted_price = f"₹{price}" if not price.startswith("₹") else price
            yield {
                "product_price": formatted_price,
                "requested_url": self.start_url,
            }

        # Navigate to the reviews page
        if self.all_sorts:
            for s_order in self.SORT_ORDERS:
                review_url = self._build_review_url(response.url, 1, sort_order=s_order)
                yield scrapy.Request(
                    url=review_url,
                    callback=self.parse_reviews,
                    meta={"current_page": 1, "sort_order": s_order},
                    dont_filter=True,
                )
        else:
            current_page = response.meta.get("current_page", self.start_page)
            review_url = self._build_review_url(response.url, current_page, sort_order=self.sort)
            yield scrapy.Request(
                url=review_url,
                callback=self.parse_reviews,
                meta={"current_page": current_page, "sort_order": self.sort},
                dont_filter=True,
            )

    def parse_reviews(self, response):
        """Parses Flipkart product reviews page and handles pagination if requested."""
        state = self._extract_initial_state(response)
        try:
            current_page = response.meta.get("current_page", self.start_page)
            sort_order = response.meta.get("sort_order", self.sort)
        except AttributeError:
            current_page = self.start_page
            sort_order = self.sort
        has_more = False
        reviews_found_on_page = 0

        if state:
            mws = state.get("multiWidgetState", {})
            slots = mws.get("widgetsData", {}).get("slots", [])
            if not slots:
                slots = mws.get("pageLevelSlots", [])

            pdr = mws.get("pageDataResponse", {})
            has_more = pdr.get("hasMorePages", False)

            # Extract Review Summary (yielded once per crawl)
            if not self.summary_yielded:
                seo = pdr.get("seoData", {}).get("seo", {})
                review_title = (
                    seo.get("keywords")
                    or seo.get("ogTitle")
                    or seo.get("title")
                    or response.xpath("//title/text()").get()
                    or ""
                )
                if ":" in review_title:
                    review_title = review_title.split(":")[0].strip()

                summary = {"review_title": review_title}
                rating_found = False

                for slot in slots:
                    sd = slot.get("slotData", {})
                    widget = sd.get("widget", {})
                    if widget.get("type") == "RATING":
                        r_val = widget.get("data", {}).get("rating", {}).get("value", {})
                        avg_rating = r_val.get("average")
                        rating_count = r_val.get("ratingCount")
                        review_count = r_val.get("reviewCount")
                        histogram = r_val.get("histogram", [])

                        summary["avg_rating"] = str(avg_rating) if avg_rating is not None else ""
                        summary["total_ratings"] = (
                            f"{rating_count:,} Ratings &" if rating_count is not None else ""
                        )
                        summary["total_reviews"] = (
                            f"{review_count:,} Reviews" if review_count is not None else ""
                        )

                        total_rev = review_count or 0
                        self.total_pages = math.ceil(total_rev / 10) if total_rev else 1
                        summary["total_pages"] = f"Page {current_page} of {self.total_pages:,}"

                        if len(histogram) == 5:
                            summary["5"] = f"{histogram[4]:,}"
                            summary["4"] = f"{histogram[3]:,}"
                            summary["3"] = f"{histogram[2]:,}"
                            summary["2"] = f"{histogram[1]:,}"
                            summary["1"] = f"{histogram[0]:,}"
                        rating_found = True
                        break

                if rating_found or summary.get("review_title"):
                    yield summary
                    self.summary_yielded = True

            # Extract Individual Reviews
            for slot in slots:
                sd = slot.get("slotData", {})
                widget = sd.get("widget", {})
                if widget.get("type") == "REVIEWS":
                    components = widget.get("data", {}).get("renderableComponents", [])
                    for comp in components:
                        val = comp.get("value", {})
                        if not val:
                            continue

                        reviews_found_on_page += 1

                        # Deduplicate across sort filters
                        permalink = (val.get("url") or "").strip()
                        author = (val.get("author") or "").strip()
                        title = (val.get("title") or "").strip()
                        text = (val.get("text") or "").strip()
                        rid = permalink or f"{author}_{title}_{text}"
                        if rid in self.seen_reviews:
                            continue
                        self.seen_reviews.add(rid)

                        loc = val.get("location") or {}
                        city = loc.get("city", "")
                        state_name = loc.get("state", "")
                        if city and state_name:
                            loc_str = f", {city}, {state_name}"
                        elif city:
                            loc_str = f", {city}"
                        elif state_name:
                            loc_str = f", {state_name}"
                        else:
                            loc_str = ""

                        up = val.get("upvote", {}).get("value", {}).get("count")
                        down = val.get("downvote", {}).get("value", {}).get("count")

                        yield {
                            "review_score": str(val.get("rating", "")),
                            "review_title": title,
                            "review_content": text,
                            "reviewer_name": author,
                            "reviewer_location": loc_str,
                            "reviewer_date": (val.get("created") or "").strip(),
                            "permalink": permalink,
                            "certified_buyer": val.get("certifiedBuyer", False),
                            "upvote": str(up) if up is not None else "0",
                            "downvote": str(down) if down is not None else "0",
                        }
        else:
            # Fallback DOM Parser
            self.logger.info("Falling back to DOM parsing")
            if not self.summary_yielded:
                page_title = response.xpath("//title/text()").get() or ""
                if ":" in page_title:
                    page_title = page_title.split(":")[0].strip()

                summary = {"review_title": page_title}
                match = re.search(
                    r"([0-9,]+)\s+ratings\s+and\s+([0-9,]+)\s+reviews",
                    response.text,
                    re.IGNORECASE,
                )
                if match:
                    summary["total_ratings"] = f"{match.group(1)} Ratings &"
                    summary["total_reviews"] = f"{match.group(2)} Reviews"
                yield summary
                self.summary_yielded = True

        # Pagination check
        if self.scrape_all and reviews_found_on_page > 0:
            can_continue = (
                self.target_max_pages is None or current_page < self.target_max_pages
            )
            if can_continue and (has_more or current_page < self.total_pages):
                next_page = current_page + 1
                next_url = self._build_review_url(response.url, next_page, sort_order=sort_order)
                self.logger.info("Paginating to page %s (sort=%s): %s", next_page, sort_order or "default", next_url)
                yield scrapy.Request(
                    url=next_url,
                    callback=self.parse_reviews,
                    meta={"current_page": next_page, "sort_order": sort_order},
                    dont_filter=True,
                )
