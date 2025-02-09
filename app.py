from flask import Flask, request, jsonify, render_template, send_file
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import mysql.connector

app = Flask(__name__)

# MySQL database connection setup
def save_to_mysql(metadata, headings, paragraphs, images, links, tables):
    conn = mysql.connector.connect(
        host="localhost",  # or your MySQL server
        user="root",       # your MySQL user
        password="your_sql_password",  # your MySQL password
        database="scraper_db"
    )
    cursor = conn.cursor()

    # Insert metadata
    cursor.execute("INSERT INTO scraped_data (title, description, keywords) VALUES (%s, %s, %s)", 
                   (metadata['Title'], metadata['Description'], metadata['Keywords']))
    
    # Insert headings, paragraphs, images, links, and tables
    for heading, paragraph, image, link, table in zip(headings, paragraphs, images, links, tables):
        cursor.execute("INSERT INTO scraped_data (heading, paragraph, image_url, link_url, table_content) VALUES (%s, %s, %s, %s, %s)", 
                       (heading, paragraph, image, link, str(table)))
    
    conn.commit()
    cursor.close()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.json.get('url')
    try:
        # Set up Selenium WebDriver for rendering JavaScript
        options = Options()
        options.add_argument("--headless")  # Run in background (no GUI)
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url)
        page_source = driver.page_source
        driver.quit()

        # Parse the page source with BeautifulSoup
        soup = BeautifulSoup(page_source, 'html.parser')

        # Extract Headings, Paragraphs, etc.
        headings = [h.text.strip() for h in soup.find_all(['h1', 'h2', 'h3'])]
        paragraphs = [p.text.strip() for p in soup.find_all('p')]
        images = [img['src'] for img in soup.find_all('img') if img.get('src')]
        links = [a['href'] for a in soup.find_all('a') if a.get('href')]
        tables = []

        for table in soup.find_all('table'):
            rows = []
            for row in table.find_all('tr'):
                cells = [cell.text.strip() for cell in row.find_all(['th', 'td'])]
                rows.append(cells)
            tables.append(rows)

        # Metadata
        metadata = {
            "Title": soup.title.string if soup.title else "N/A",
            "Description": soup.find('meta', attrs={'name': 'description'})['content'] if soup.find('meta', attrs={'name': 'description'}) else "N/A",
            "Keywords": soup.find('meta', attrs={'name': 'keywords'})['content'] if soup.find('meta', attrs={'name': 'keywords'}) else "N/A"
        }

        # Ensure all lists have the same length
        max_length = max(len(headings), len(paragraphs), len(images), len(links), len(tables))

        headings += [''] * (max_length - len(headings))
        paragraphs += [''] * (max_length - len(paragraphs))
        images += [''] * (max_length - len(images))
        links += [''] * (max_length - len(links))
        tables += [['']] * (max_length - len(tables))  # For tables, ensure each is a list of empty strings

        # Save data to MySQL
        save_to_mysql(metadata, headings, paragraphs, images, links, tables)

        # Create a DataFrame for Excel
        data = {
            "Headings": headings,
            "Paragraphs": paragraphs,
            "Images": images,
            "Links": links,
            "Tables": [str(table) for table in tables]
        }
        df = pd.DataFrame(data)

        # Save to Excel
        filename = "scraped_data.xlsx"
        filepath = os.path.join(os.getcwd(), filename)
        df.to_excel(filepath, index=False)

        return jsonify({"message": "Data scraped successfully!", "file": filename, "metadata": metadata})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/download')
def download_file():
    """Endpoint to download the Excel file"""
    filepath = os.path.join(os.getcwd(), "scraped_data.xlsx")
    return send_file(filepath, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
