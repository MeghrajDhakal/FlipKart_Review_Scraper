Flipkart Review Scraper
Python based web scraper using scrapy to scrape Flipkart "Product" or "All Reviews" pages and returns all the reviews on the page, and the associated meta data about the product and the reviewer.
It can be used as a command line tool just like any scrapy project or used as a RESTful API.
Table of Contents

·	Flipkart Review API
o	Table of Contents
o	Zero-Setup Quickstart (Mac, Windows, Linux)
o	Manual Installation Instructions
o	Usage as a command line review scraper
o	Usage as an API
§	Example Response:
o	Full API Implementation
Zero-Setup Quickstart (Mac, Windows, Linux)

No manual virtual environment setup or dependency installation required! The provided runner scripts will automatically detect your OS, create a local .venv, install the exact compatible dependencies, and launch the service:
Option 1: Universal Python Runner (Any OS)
python run.py             # Auto-creates .venv, installs dependencies, & starts API
python run.py crawl -a url="<FlipkartURL>" -o output.json  # Run scraper
python run.py test        # Run unit tests

Option 2: 1-Click / 1-Command Native Launchers
·	macOS / Linux:
·	./run.sh                # Starts API server with auto-configured venv
./run.sh test           # Runs tests

·	Windows (Command Prompt / Double Click):
·	run.bat                 # Or double-click run.bat in Windows Explorer

·	Windows PowerShell:
·	.\run.ps1

Option 3: Docker (Zero-install container)
If you have Docker installed, you don't even need Python installed on your machine:
docker compose up --build

The API will be available at http://localhost:5000.
Example Response:

[
    
    {"product_price": "\u20b99999", 
    "requested_url": "URL"},
    
    {"review_title": "Product Title", 
    "avg_rating": "4.4", 
    "total_ratings": "3,64,537 Ratings &", 
    "total_reviews": "24,907 Reviews", 
    "total_pages": "Page 1 of 2,491", 
    "5": "2,50,327", 
    "4": "67,635", 
    "3": "22,835", 
    "2": "7,656", 
    "1": "16,084"},

    {"review_score": "5", 
    "review_title": "Brilliant", 
    "review_content": "The UI is super smooth and performs really well. The quad cams are amazing. 5000 mah battery is like a cherry on top. Perfect phone for its price!", 
    "reviewer_name": "Reviewer Name", 
    "reviewer_location": "Reviewer Location", 
    "reviewer_date": "Review Date", 
    "permalink": "/reviews/permalink", 
    "upvote": "6836", 
    "downvote": "1292"}

]


Full API Implementation

The API Can be found on RapidAPI:
RapidAPI Link
If you want to use the API, replace the http://127.0.0.1:8000 to:
https://reviewdataapi.herokuapp.com/v1.0/reviews?&page={}&url={}

http://reviewdata.org/
Since its hosted above, the below will also work:
curl "http://reviewdata.org/v1.0/reviews?&page=1&url=https://www.flipkart.com/realme-5i-forest-green-64-gb/p/itmdac0da867a9fa?pid=MOBFNG3GNW3BU2XE&lid=LSTMOBFNG3GNW3BU2XERAL9TG&marketplace=FLIPKART&srno=b_1_1&otracker=nmenu_sub_Electronics_0_Realme&fm=productRecommendation%2Fsimilar&iid=ceed1ea3-d651-4cd7-81fc-90c8cf2879ba.MOBFNG3GNW3BU2XE.SEARCH&ppt=browse&ppn=browse&ssid=mtqj6s4xb2sii2o01602530157645"
