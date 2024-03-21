from flask import Flask, render_template, request
from bs4 import BeautifulSoup
from urllib.request import urlopen
import ssl
import mysql.connector
import schedule
import time
import threading

ssl._create_default_https_context = ssl._create_unverified_context

app = Flask(__name__)

# Database connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="skapiec_data"
)
cursor = db.cursor()

# Add product to database
def add_product_to_database(name, price, link, img_url):
    try:
        # Tworzenie połączenia z bazą danych, jeśli nie jest już otwarte
        if not db.is_connected():
            db.reconnect()
        # Tworzenie kursora
        cursor = db.cursor()
        sql = "INSERT INTO products (name, price, link, img_url) VALUES (%s, %s, %s, %s)"
        val = (name, price, link, img_url)
        cursor.execute(sql, val)
        db.commit()
        print("Dane dodane do bazy danych.")
    except mysql.connector.Error as e:
        print("Błąd połączenia z bazą danych:", e)

# Clear previous data from the database
def clear_previous_data():
    sql = "TRUNCATE TABLE products"
    cursor.execute(sql)
    db.commit()

# Get products from the database
def get_products_from_database(query=None):
    if query:
        sql = "SELECT * FROM products WHERE name LIKE %s"
        cursor.execute(sql, ('%' + query + '%',))
    else:
        cursor.execute("SELECT * FROM products")
    return cursor.fetchall()

# Function to scrape data and update database
def scrape_and_update(query):  # Dodano argument query
    print("Rozpoczęto scrapowanie i aktualizację danych...")
    url = f"https://www.skapiec.pl/szukaj?query={query}&categoryId="
    page = urlopen(url)
    html = page.read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")
    product_elements = soup.find_all("div", class_="product-box-narrow-container")

    clear_previous_data()

    for product_element in product_elements:
        link_element = product_element.find("a", class_="product-box-narrow-link")
        name = link_element.get('aria-label')
        link = link_element.get('href')

        price_element = product_element.find("span", class_="price")
        price = price_element.text.strip()

        div_img_element = product_element.find("div", class_="product-box-narrow__photo-box-image")
        img_element = div_img_element.find('img')
        img_url = img_element.get('src')

        add_product_to_database(name, price, link, img_url)

# Schedule scraping task every 5 seconds
schedule.every(5).seconds.do(scrape_and_update, 'your_query_here')  # Podaj tutaj swoje zapytanie

# Flask route to display products
@app.route('/', methods=['GET', 'POST'])
def search_products():
    query = request.form.get('query', None)
    products = get_products_from_database(query)
    return render_template('index.html', products=products)

if __name__ == '__main__':
    # Run Flask app in a separate thread
    flask_thread = threading.Thread(target=app.run)
    flask_thread.start()

    # Run scheduling task in a separate thread
    while True:
        schedule.run_pending()
        time.sleep(1)
