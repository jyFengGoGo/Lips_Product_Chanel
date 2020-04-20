
from bs4 import BeautifulSoup
import requests
import sqlite3
import time
import json

CACHE_FILENAME = 'chanel_cache.json'
CACHE_DICT = {}

root = "https://www.chanel.com"
BASEURL = "https://www.chanel.com/us/"

# get urls of all categories
def get_all_categories():
    resp = request_with_cache(BASEURL)
    soup = BeautifulSoup(resp.text, 'html.parser')
    all_4_ul = soup.find('ul', class_='header__primary__links header__primary__links2')
    all_makeup_li = all_4_ul.find_all('li', class_='js-header-entry ')
    all_makeup_li = all_makeup_li[2]
    makeup_list = all_makeup_li.find('div', class_='header__secondary js-header-nav-secondary')
    eyes_lips_list = makeup_list.find('div', class_='header__columns')
    eyes_lips_list = eyes_lips_list.find_all('div', class_="header__column ")
    lips_list = eyes_lips_list[3].find_all('div', class_='header__category')
    lips_list = lips_list[1].find_all('li')
    lips_prod = {}
    for product in lips_list:
        li = product.find('a', href=True)
        url = root + li['href']
        name = li.text.strip()
        lips_prod[name] = url
    return lips_prod


# get product urls
def get_products_url(category_url):
    resp = request_with_cache(category_url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    contain = soup.find('div', class_='js-main-content plp')
    grid = contain.find('div', class_='pdp-grid js-pdp-grid')
    list = grid.find('div', class_='product-grid columns-mobile-2 columns-tablet-2 columns-desktop-3')
    prod_list = list.find_all('div', class_='product-grid__item js-product-edito')
    prod_urls = []
    for prod in prod_list:
        content = prod.find('div', class_='txt-product')
        a = content.find('a', href=True)
        prod_urls.append(root + a['href'])
    return prod_urls


# get product info
def get_product_information(product_url):
    # {"product":{productName, price, shadeNum, Rating, description, pic1, pic2},
    # "review":[(body, rating, date)]}
    product_info = {}
    product_info["product"] = {}

    resp = request_with_cache(product_url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    contain = soup.find('div', class_='js-main-content pdp')
    text = contain.find('div', class_='product-details__text')
    name = text.find('span', class_='heading product-details__title ')
    product_info["product"]["ProductName"] = name.text.strip()

    price_block = text.find('div', class_='product-details__price-block')
    price = price_block.find('p', class_='product-details__price')
    product_info["product"]["Price"] = price.text.strip()

    shade_button = text.find('div', class_='product-details__option js-variant-list')
    if shade_button == None:
        product_info["product"]["ShadeNum"] = 1
    else:
        shade_block = shade_button.find('div', id='variant-Shade-shades-label')
        shade = shade_block.find('span')
        if shade.text == 'Shade available':
            product_info["product"]["ShadeNum"] = 1
        else:
            shade = shade.text.strip().split(' ')
            product_info["product"]["ShadeNum"] = int(shade[0])

    review_sum = contain.find('div', class_='TTreviewSummary')
    rating = review_sum.find('span', id='TTreviewSummaryAverageRating')
    if rating != None:
        rating = rating.text.strip()
        product_info["product"]["Rating"] = eval(rating.split('/')[0].strip())
        reviews = []
        review_block = contain.find('div', id='TTreviews')
        reviews_all = review_block.find_all('div', class_='TTreview')
        for review in reviews_all:
            body = review.find('div', class_='TTreviewBody').text.strip()
            rating = int(review["rating"])
            date = review.find('div', class_='TTrevCol3')
            date = date.find('div', itemprop='dateCreated')['datetime']
            reviews.append((body, rating, date))
        product_info["review"] = reviews
    else:
        product_info["product"]["Rating"] = 'NULL'
        product_info["review"] = []

    description_block = contain.find('div', class_='col-24 col-l-12 col-m-12 off-l-6 off-m-6')
    product_desrp = description_block.find_all('p')[0].text.strip()
    product_info["product"]["Description"] = product_desrp

    picture_slides = contain.find('ul', class_='carousel__frame js-frame')
    pics = picture_slides.find_all('li', class_='carousel__slide js-slide')
    pic_list = []
    for pic in pics:
        pic_list.append(pic.find('img')['data-src'])

    product_info["product"]["Picture1"] = pic_list[0]
    if len(pic_list) == 1:
        product_info["product"]["Picture2"] = 'NULL'
    else:
        product_info["product"]["Picture2"] = pic_list[1]

    return product_info


# create database
def create_db():
    conn = sqlite3.connect('chanel_lips.sqlite')
    cur = conn.cursor()

    drop_product_sql = 'DROP TABLE IF EXISTS "Product"'
    drop_review_sql = 'DROP TABLE IF EXISTS "Review"'

    create_product_sql = '''
        CREATE TABLE IF NOT EXISTS "Product"(
            "Id" INTEGER PRIMARY KEY AUTOINCREMENT, 
            "CategoryName" TEXT NOT NULL,
            "ProductName" TEXT NOT NULL,
            "Price" TEXT NOT NULL, 
            "ShadeNum" INTEGER NOT NULL,
            "Rating" REAL,
            "Description" TEXT,
            "Picture1" TEXT,
            "Picture2" TEXT
        )
    '''
    create_review_sql = '''
        CREATE TABLE IF NOT EXISTS "Review"(
            "Id" INTEGER PRIMARY KEY AUTOINCREMENT, 
            "ProductId" INTEGER NOT NULL,
            "ReviewBody" TEXT,
            "ReviewRating" Real,
            "dateCreated" TEXT
        )
    '''

    cur.execute(drop_product_sql)
    cur.execute(drop_review_sql)
    cur.execute(create_product_sql)
    cur.execute(create_review_sql)
    conn.commit()
    conn.close()


def insert_db(product_info, category):
    conn = sqlite3.connect('chanel_lips.sqlite')
    cur = conn.cursor()

    insert_product_sql = '''
        INSERT INTO Product 
        VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    insert_review_sql = '''
        INSERT INTO Review
        VALUES (NULL, ?, ?, ?, ?)
    '''
    pro = product_info['product']
    pro_val = [category, pro['ProductName'], pro['Price'], pro['ShadeNum'],\
           pro['Rating'], pro['Description'], pro['Picture1'], pro['Picture2']]
    cur.execute(insert_product_sql, pro_val)

    pro_id = cur.lastrowid
    if len(product_info['review']) != 0:
        for review in product_info['review']:
            rev_val = [pro_id, review[0], review[1], review[2]]
            cur.execute(insert_review_sql, rev_val)

    conn.commit()
    conn.close()
    return

def build_db(lips_categories):
    for i, (category, url) in enumerate(lips_categories.items()):
        print(category)
        prod_urls = get_products_url(lips_categories[category])
        for url in prod_urls:
            print(url)
            info = get_product_information(url)
            insert_db(info, category)
            time.sleep(2)


def open_cache():
    ''' Opens the cache file if it exists and loads the JSON into
    the CACHE_DICT dictionary.
    if the cache file doesn't exist, creates a new cache dictionary

    Parameters
    ----------
    None

    Returns
    -------
    The opened cache: dict
    '''
    try:
        cache_file = open(CACHE_FILENAME, 'r')
        cache_contents = cache_file.read()
        cache_dict = json.loads(cache_contents)
        cache_file.close()
    except:
        cache_dict = {}
    return cache_dict


def save_cache(cache_dict):
    ''' Saves the current state of the cache to disk

    Parameters
    ----------
    cache_dict: dict
        The dictionary to save

    Returns
    -------
    None
    '''
    dumped_json_cache = json.dumps(cache_dict)
    fw = open(CACHE_FILENAME, "w")
    fw.write(dumped_json_cache)
    fw.close()


def request_with_cache(url):
    if url in CACHE_DICT.keys():
        print("using cache")
        resp = CACHE_DICT[url]
    else:
        print("fetching")
        resp = requests.get(url)
        CACHE_DICT[url] = resp
    return resp


if __name__ == "__main__":
    CACHE_DICT = open_cache()

    create_db()
    lips_categories = get_all_categories()
    build_db(lips_categories)

    save_cache(CACHE_DICT)

