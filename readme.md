# Car Data Scraper

A Python tool to scrape car data from a specific website and organize it in a SQLite database for later analysis and comparison.

Runtime of 2m 29s

## Features

Logs into a website using credentials stored in environment variables.

Navigates the car selection interface by division, year, and model.

Extracts pricing and model data, including invoice price, MSRP, and cost of delivery (DFRT).

Supports filtering for specific divisions, e.g., Toyota, Honda, Chevy Cars, and Chevy Utility Vehicles.

Stores structured data in a SQLite database for easy querying and analysis.

## Setup

Clone the repository
```
clone https://github.com/KevinLubbers/pc-carbook-playwright.git
```

Install dependencies:

```
pip install requirements.txt
playwright install
```

Create a .env file in the project root with the following variables:

```
BASE_URL=<login page URL>
LOGIN_USER=<your username>
LOGIN_PASS=<your password>
HEADLESS=false 
DB_URL=db/your_db.db
```

## Usage

Run the scraper:

```
python main.py
```
The scraper will:

- Open a browser. 
- Log in to the website.
- Loop through the specified divisions and models.
- Extract table data for each model.
- Insert data into the SQLite database specified in DB_URL.

## Database Schema

Table: mdl_dfrt_check

| Column | Type | Description |
| -------| -----| ----------- |
| id |	INTEGER |	Primary key |
| model_year |	INTEGER | Year of the model |
| division | TEXT | Car division (e.g., Toyota) |
|model | TEXT |	Model name |
|model_code | TEXT |	Model code from the website |
|style_name | TEXT |	Style/trim name |
|invoice_price | REAL |	Invoice price |
|msrp_price | REAL |	MSRP price |
|dfrt_price | REAL |	Delivery price |
|scrape_date | TEXT |	Timestamp of data scraping |

### Notes
The scraper includes special handling for Toyota models to only capture rows labeled (Natl).

Be mindful of the website’s terms of service and scraping limits.