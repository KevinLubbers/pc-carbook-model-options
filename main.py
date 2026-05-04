import os
import sqlite3
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Load environment variables
load_dotenv()

BASE_URL = os.getenv("BASE_URL")
LOGIN_USER = os.getenv("LOGIN_USER")
LOGIN_PASS = os.getenv("LOGIN_PASS")
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
DB_URL = os.getenv("DB_URL")


# Connect to the database
conn = sqlite3.connect(DB_URL)
c = conn.cursor()

#create table if it doesn't exist
c.execute("""
        CREATE TABLE IF NOT EXISTS model_options(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_year INTEGER NOT NULL,
            division TEXT NOT NULL,
            model TEXT NOT NULL,
            model_code TEXT NOT NULL,
            option_code TEXT NOT NULL,
            option_name TEXT DEFAULT NULL,
            invoice_price REAL NOT NULL,
            msrp_price REAL NOT NULL,
            scrape_date TEXT DEFAULT (datetime('now', 'localtime'))
        )""")

#SQL query used later to insert using executemany()
sql = """INSERT INTO model_options (model_year, division, model, model_code, option_code, option_name, invoice_price, msrp_price)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""

#main loop
def run():
    with sync_playwright() as p:
        #navigate and log in
        browser = p.chromium.launch(headless=HEADLESS)
        page = browser.new_page()
        page.goto(BASE_URL)
        page.fill("#username", LOGIN_USER)
        page.fill("#password", LOGIN_PASS)
        page.click("#login-button")

        #click on Build button and wait for popup
        page.wait_for_selector(".framework-header-selector-button")
        page.click(".framework-header-selector-button")
        page.wait_for_selector(".component-selector-model-input")

        #loop through hard-coded division list. no need to scrape all divisions
        division_list = ['Hyundai']
        year_list = ['2026']
        data = []
        for each_year in year_list:
            page.select_option('.component-selector-year-input', label=each_year)
            time.sleep(3)
            divisions_of_year = page.locator('.component-selector-make-input option').all_text_contents()
            for each_division in division_list:
                if each_division not in divisions_of_year:
                    continue
                page.select_option('.component-selector-make-input', label=each_division)
                #get text of selected division
                division = page.eval_on_selector('select.component-selector-make-input','select => select.options[select.selectedIndex].textContent')
                #get text of selected year 
                year = page.eval_on_selector('select.component-selector-year-input','select => select.options[select.selectedIndex].textContent')
                time.sleep(1)
                page.wait_for_selector(".component-selector-model-input")
                #get text of all models (except the first one, which is a placeholder)
                models = page.eval_on_selector_all(".component-selector-model-input option", "options => options.slice(1).map(option=> option.textContent)")
                #loop through all models found
                for model in models[:1]:
                    page.select_option('.component-selector-model-input', label=model)
                    time.sleep(2)
                    #get dynamically generated table data after selecting model
                    table = page.query_selector("table.style-cellTableWidget tbody")
                    rows = table.query_selector_all("tr")
                    #only select rows with national pricing for all Toyota models
                    if each_division == "Toyota":
                        for i in range(len(rows)):
                            cells = row.query_selector_all("td")
                            if any("(Natl)" in cell.inner_text() for cell in cells):
                                #extracts *MDL and DFRT pricing from each row
                                row_data = [cell.inner_text().strip() for cell in cells]
                                row_data = [x.replace("$", "").replace(",", "") for x in row_data]
                                #order of query is (year, division, model, model_code, option_code, option_name, invoice_price, msrp_price )
                                full_model_name = model + " " + row_data[1]
                                model_code = row_data[0]
                                option_name = None
                                insert_tuple = (year, division, full_model_name, model_code, "*MDL", option_name, float(row_data[2]), float(row_data[3]))
                                data.append(insert_tuple)
                                insert_tuple = (year, division, full_model_name, model_code, "DFRT", option_name, float(row_data[4]), float(row_data[4]))
                                data.append(insert_tuple)
                    #otherwise, select all rows
                    else:
                        for i in range(len(rows)):
                            table = page.query_selector("table.style-cellTableWidget tbody")
                            rows = table.query_selector_all("tr")
                            row = rows[i]
                            #extracts *MDL and DFRT pricing from each row
                            cells = row.query_selector_all("td")
                            row_data = [cell.inner_text().strip() for cell in cells]
                            row_data = [x.replace("$", "").replace(",", "") for x in row_data]
                            #order of query is (year, division, model, model_code, option_code, option_name, invoice_price, msrp_price )
                            full_model_name = model + " " + row_data[1]
                            model_code = row_data[0]
                            option_name = None
                            insert_tuple = (year, division, full_model_name, model_code, "*MDL", option_name, float(row_data[2]), float(row_data[3]))
                            data.append(insert_tuple)
                            insert_tuple = (year, division, full_model_name, model_code, "DFRT", option_name, float(row_data[4]), float(row_data[4]))
                            data.append(insert_tuple)
                            #end *MDL and DFRT
                            #start enter model options
                            row.click()
                            time.sleep(1)
                            page.wait_for_selector('#select-new-vehicle-button')
                            page.click('#select-new-vehicle-button')
                            time.sleep(2)
                            option_table = page.query_selector_all("tr.dataRow")
                            for option in option_table:
                                cells = option.query_selector_all("td")
                                row_data = [cell.inner_text().strip() for cell in cells]
                                row_data = [x.replace("$", "").replace(",", "") for x in row_data]
                                #order of query is (year, division, model, model_code, option_code, option_name, invoice_price, msrp_price )
                                print(row_data)
                                insert_tuple = (year, division, full_model_name, model_code, row_data[1], row_data[2], float(row_data[4]), float(row_data[5]))
                                data.append(insert_tuple)
                            time.sleep(25)
                            page.click(".framework-header-selector-button")
                            time.sleep(3)

                
                    time.sleep(2)

        #insert data into database
        c.executemany(sql, data)

        conn.commit()
        conn.close()
        #close pop up
        page.click("img.gwt-Image[src*='close_window.gif']")
        #logout properly
        page.click("a.gwt-Anchor:has-text('Log Out')")

        time.sleep(5)
        browser.close()


if __name__ == "__main__":
    run()