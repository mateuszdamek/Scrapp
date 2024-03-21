from flask import Flask, render_template, request
from bs4 import BeautifulSoup
from urllib.request import urlopen
import ssl
import mysql.connector
import schedule
import threading
import time

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

def add_product_to_database(name, price, link, img_url):
    sql = "INSERT INTO products (name, price, link, img_url) VALUES (%s, %s, %s, %s)"
    val = (name, price, link, img_url)
    cursor.execute(sql, val)
    db.commit()

def clear_previous_data():
    sql = "TRUNCATE TABLE products"
    cursor.execute(sql)
    db.commit()

def get_products_from_database(query=None):
    if query:
        sql = "SELECT * FROM products WHERE name LIKE %s"
        cursor.execute(sql, ('%' + query + '%',))
    else:
        cursor.execute("SELECT * FROM products")
    return cursor.fetchall()

def scrape_and_update(query=None):
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

    print("Data added to the database successfully")

#uruchamia harmonogram w osobnym wątku
def run_schedule():
    print("Harmonogram został uruchomiony.")
    while True:
        schedule.run_pending()
        time.sleep(1)

schedule.every(5).seconds.do(scrape_and_update)

def start_schedule_thread():
    schedule_thread = threading.Thread(target=run_schedule)
    schedule_thread.start()

start_schedule_thread()

# Endpoint Flask
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        scrape_and_update(request.form.get('query'))  #zapytanie jako argument
        return search_products()
    return render_template('index.html')

def search_products():
    query = request.form.get('query', None)
    products = get_products_from_database(query)
    return render_template('index.html', products=products)

if __name__ == '__main__':
    app.run()
