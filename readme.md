# Car Data Scraper

A Python tool to scrape car data from a specific website and organize it in a SQLite database for later analysis and comparison.

Runtime varies based on selected Manufacturer.

## Features

Logs into a website using credentials stored in environment variables.

Navigates the car selection interface by division, year, and model.

Extracts pricing for all options in all models of the selected Manufacturer. Includes base price and cost of delivery.

Requires changes to the code to set up other Manufacturers. Currently only set up for Hyundai.

Stores structured data in a SQLite database for easy querying and analysis.

## Setup

Clone the repository
```
clone https://github.com/KevinLubbers/pc-carbook-model-options.git
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

### Table: Model Option Pricing

| Column | Type | Description |
| -------| -----| ----------- |
|id |	INTEGER |	Primary key |
|model_year |	INTEGER | Year of the model |
|division | TEXT | Car division (e.g., Toyota) |
|model | TEXT |	Model name |
|model_code | TEXT |	Model code from the website |
|option_code | TEXT |	3-4 digit Manufacturer identifier |
|option_category | TEXT | Type of option - groups of commons(paints, equipment, interior, etc)
|invoice_price | REAL |	Invoice price |
|msrp_price | REAL |	MSRP price |
|scrape_date | TEXT |	Timestamp of data scraping |

### Notes
The scraper includes special handling for Toyota models to only capture rows labeled (Natl).

Be mindful of the website’s terms of service and scraping limits.