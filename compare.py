import sqlite3
import os
import requests
import sys
from datetime import date, timedelta
from dotenv import load_dotenv

#load env variables and connect to DB
load_dotenv()
DB_URL = os.getenv("DB_URL")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
NO_UPDATES_WEBHOOK = os.getenv("NO_UPDATES_WEBHOOK")
CHANGE_QUERY_WEBHOOK_URL = os.getenv("CHANGE_QUERY_WEBHOOK_URL")

conn = sqlite3.connect(DB_URL)
conn.row_factory = sqlite3.Row
c = conn.cursor()

count_models_query = """
    SELECT
    division,
    COUNT(DISTINCT CASE WHEN DATE(scrape_date) = :date1 THEN model END) AS "Day 1 Model Count",
    COUNT(DISTINCT CASE WHEN DATE(scrape_date) = :date2 THEN model END) AS "Day 2 Model Count",
    COUNT(DISTINCT CASE WHEN DATE(scrape_date) = :date1 THEN model END)
      - COUNT(DISTINCT CASE WHEN DATE(scrape_date) = :date2 THEN model END) AS "Day 1 - Day 2"
FROM mdl_dfrt_check
GROUP BY division
ORDER BY division
        """

count_models_lag_query = """
WITH daily_models AS (
    SELECT
        division,
        DATE(scrape_date) AS scrape_day,
        model_year || '-' || model AS model_id
    FROM mdl_dfrt_check
    GROUP BY division, DATE(scrape_date), model_id
),
daily_counts AS (
    SELECT
        division,
        scrape_day,
        COUNT(*) AS model_count
    FROM daily_models
    GROUP BY division, scrape_day
)
SELECT
    division,
    scrape_day,
    model_count AS "Day Model Count",
    model_count - LAG(model_count) OVER (PARTITION BY division ORDER BY scrape_day) AS "Day-over-Day Change"
FROM daily_counts
ORDER BY division, scrape_day;
"""

show_month_range_query = """
    SELECT DISTINCT scrape_date
        FROM mdl_dfrt_check
        WHERE scrape_date >= datetime('now', '-100 days')
        ORDER BY scrape_date DESC
        """
#added final AND to hide records with no diff
#remove to show all records 
compare_query = """
    SELECT
        a.model_year,
        a.division,
        a.model,
        a.model_code,
        a.style_name,

        a.invoice_price AS invoice_old,
        b.invoice_price AS invoice_new,
        (b.invoice_price - a.invoice_price) AS invoice_diff,

        a.msrp_price AS msrp_old,
        b.msrp_price AS msrp_new,
        (b.msrp_price - a.msrp_price) AS msrp_diff,

        a.dfrt_price AS dfrt_old,
        b.dfrt_price AS dfrt_new,
        (b.dfrt_price - a.dfrt_price) AS dfrt_diff

    FROM mdl_dfrt_check a
    JOIN mdl_dfrt_check b
      ON a.model_code = b.model_code
     AND a.style_name = b.style_name
     AND a.model_year = b.model_year

    WHERE date(a.scrape_date) = date(?)
      AND date(b.scrape_date) = date(?)
      AND (
        invoice_diff != 0 OR
        msrp_diff != 0 OR
        dfrt_diff != 0
      )

    ORDER BY a.division, a.model, a.style_name
    """

optimized_compare_query = """
WITH old_day AS (
    SELECT *
    FROM mdl_dfrt_check
    WHERE date(scrape_date) = date(?)
),
new_day AS (
    SELECT *
    FROM mdl_dfrt_check
    WHERE date(scrape_date) = date(?)
)

SELECT
    a.model_year,
    a.division,
    a.model,
    a.model_code,
    a.style_name,

    a.invoice_price AS invoice_old,
    b.invoice_price AS invoice_new,
    (b.invoice_price - a.invoice_price) AS invoice_diff,

    a.msrp_price AS msrp_old,
    b.msrp_price AS msrp_new,
    (b.msrp_price - a.msrp_price) AS msrp_diff,

    a.dfrt_price AS dfrt_old,
    b.dfrt_price AS dfrt_new,
    (b.dfrt_price - a.dfrt_price) AS dfrt_diff

FROM old_day a
JOIN new_day b
  ON a.model_code = b.model_code
 AND a.style_name = b.style_name
 AND a.model_year = b.model_year

WHERE
    (b.invoice_price - a.invoice_price) != 0 OR
    (b.msrp_price - a.msrp_price) != 0 OR
    (b.dfrt_price - a.dfrt_price) != 0

ORDER BY a.division, a.model, a.style_name
"""
#creates a nicely formatted table of results with headers and column widths
def print_sql_table(cursor, max_width=40):
    returnText = []
    rows = cursor.fetchall()
    if not rows:
        print("No results found")
        send = input("Send results to Teams? (y/n): ").strip().lower()
        if send == "y":
            try:
                data = {"name": "PC Carbook | No Updates Found"}
                requests.post(NO_UPDATES_WEBHOOK, json=data)
            except ValueError as e:
                print(e)
        else:
            print("Results not sent to Teams")
        sys.exit(0)


    columns = [desc[0] for desc in cursor.description]

    # Convert rows to lists so we can measure values
    table = []
    for row in rows:
        if isinstance(row, dict) or hasattr(row, "keys"):  # sqlite3.Row
            table.append([str(row[col]) for col in columns])
        else:
            table.append([str(val) for val in row])

    # Determine column widths
    widths = []
    for i, col in enumerate(columns):
        max_cell = max(len(r[i]) for r in table)
        width = min(max(len(col), max_cell), max_width)
        widths.append(width)

    # Helper for trimming long values
    def trim(val, w):
        return val if len(val) <= w else val[:w-3] + "..."

    # Print header
    header = " | ".join(f"{col:<{widths[i]}}" for i, col in enumerate(columns))
    print(header)
    print("-" * len(header))
    returnText.append(header) 
    returnText.append("-" * len(header))

    # Print rows
    for row in table:
        line = " | ".join(
            f"{trim(row[i], widths[i]):<{widths[i]}}"
            for i in range(len(columns))
        )
        print(line)
        returnText.append(line)
    return "\n".join(returnText)
#end print_sql_table


#start text to HTML conversion
def text_to_html_table(table_text):
    lines = table_text.strip().split("\n")
    html = f"<p>Previous Run Date: {date1}</p><p>Today's Run Date: {date2}</p>"

    # First line is header
    headers = [h.strip() for h in lines[0].split("|")]
    html += '<table border="1" style="border-collapse: collapse; font-size:12px;">'

    # Header row
    html += "<tr>"
    for h in headers:
        html += f"<th style='padding:4px;background:#f2f2f2'>{h}</th>"
    html += "</tr>"

    # Data rows (skip separator line)
    for line in lines[1:]:
        if set(line.strip()) <= {"-", " "}:
            continue  # skip the dashed line
        cells = [c.strip() for c in line.split("|")]
        html += "<tr>"
        for c in cells:
            # Optional: highlight diff columns
            if "diff" in headers[cells.index(c)].lower():
                try:
                    val = float(c)
                    if val > 0:
                        html += f"<td style='color:green;font-weight:bold'>{c}</td>"
                    elif val < 0:
                        html += f"<td style='color:red;font-weight:bold'>{c}</td>"
                    else:
                        html += f"<td>{c}</td>"
                except:
                    html += f"<td>{c}</td>"
            else:
                html += f"<td>{c}</td>"
        html += "</tr>"

    html += "</table>"
    return html
#end text_to_html

#start rows_only
def rows_only(table_text):
    lines = table_text.strip().split("\n")
    # list to store all rows and be returned
    html = []
    # getting headers from first line so I can determine which columns to highlight
    headers = [h.strip() for h in lines[0].split("|")]

    # Data rows (skip separator line)
    for line in lines[2:]:
        html_string = "<tr>"
        cells = [c.strip() for c in line.split("|")]
        for c in cells:
            if "diff" in headers[cells.index(c)].lower():
                try:
                    val = float(c)
                    if val > 0:
                        html_string += f"<td style='color:green;font-weight:bold'>{c}</td>"
                    elif val < 0:
                        html_string += f"<td style='color:red;font-weight:bold'>{c}</td>"
                    else:
                        html_string += f"<td>{c}</td>"
                except:
                    html_string += f"<td>{c}</td>"
            else:
                html_string += f"<td>{c}</td>"
        html_string += "</tr>"
        html.append(html_string)

    return html

#start input menu
print("Select run range:")
print("1) Compare today with yesterday (or most recent day)")
print("2) Compare today with 7 days ago")
print("3) Compare today with 30 days ago")
print("4) Custom date range")

#input menu logic
while True:
    choice = input("Choice: ")
    today = date.today()
    match choice:
        case "1":
            yesterday = today - timedelta(days=1)
            date1 = yesterday.strftime("%Y-%m-%d")
            date2 = today.strftime("%Y-%m-%d")
            break
        case "2":
            seven_days_ago = today - timedelta(days=7)
            date1 = seven_days_ago.strftime("%Y-%m-%d")
            date2 = today.strftime("%Y-%m-%d")
            break
        case "3":
            thirty_days_ago = today - timedelta(days=30)
            date1 = thirty_days_ago.strftime("%Y-%m-%d")
            date2 = today.strftime("%Y-%m-%d")
            break
        case "4":
            c.execute(show_month_range_query)
            rows = c.fetchall()
            print("Select any two dates:")
            for i, row in enumerate(rows, start=1):
                print(f"{i}) {row['scrape_date']}")
                      
            date1 = input("Start date (YYYY-MM-DD): ")
            date2 = input("End date (YYYY-MM-DD): ")
            break
        case _:
            print("Please select 1–4.")

#start count and count diff query + display output
lag_query_text = []
c.execute(count_models_lag_query)
rows = c.fetchall()

# Print a header
print(f"{'Division':<12} | {'Scrape Date':<12} | {'Model Count':<12} | {'Day-over-Day Change':<20}")
print("-" * 65)
lag_query_text.append(f"{'Division':<12} | {'Scrape Date':<12} | {'Model Count':<12} | {'Day-over-Day Change':<20}")
lag_query_text.append("-" * 65)

# Print each row
for row in rows:
    division, scrape_day, model_count, day_diff = row
    # Replace None with 0 or '-' for first day
    day_diff_display = day_diff if day_diff is not None else '-'
    print(f"{division:<12} | {scrape_day:<12} | {model_count:<12} | {day_diff_display:<20}")
    lag_query_text.append(f"{division:<12} | {scrape_day:<12} | {model_count:<12} | {day_diff_display:<20}")

lag_query_text = "\n".join(lag_query_text)
"""
c.execute(count_models_query, {"date1": date1, "date2": date2})
count = c.fetchall()
print(f"{'Day 1 Model Count':<18} | {'Day 2 Model Count':<18} | {'Count Diff':<12} | {'Division':<12}")
print("-" * 70)
for row in count:
    day1_count, day2_count, diff, division = row[1], row[2], row[3], row[0]
    print(f"{day1_count:<18} | {day2_count:<18} | {diff:<12} | {division:<14}")
"""
#start compare query and text display table creation
c.execute(optimized_compare_query, (date1, date2))
string_output = print_sql_table(c)
conn.close()

#convert text table to HTML
price_html_output = text_to_html_table(string_output)
change_html_output = text_to_html_table(lag_query_text)

#new row only function
price_rows_only = rows_only(string_output)
#change_rows_only = rows_only(lag_query_text)

#send results to webhook
send = input("Send price results to Teams? (y/n): ").strip().lower()
if send == "y":
    try:
        data = {"content": price_rows_only}
        requests.post(WEBHOOK_URL, json=data)
    except ValueError as e:
        print(e)
else:
    print("Results not sent to Teams")

send = input("Send change results to Teams? (y/n): ").strip().lower()
if send == "y":
    try:
        data = {"content": f"{change_html_output}"}
        requests.post(CHANGE_QUERY_WEBHOOK_URL, json=data)
    except ValueError as e:
        print(e)
else:
    print("Results not sent to Teams")