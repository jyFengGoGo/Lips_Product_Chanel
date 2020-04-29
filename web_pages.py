from flask import Flask, render_template
from chanel_lips import *

app = Flask(__name__)

local_root = 'http:/127.0.0.1:5000'

@app.route('/')
def index():
    return '<h1>Welcome!</h1>'

@app.route('/product/<pk>')
def product_details(pk):
    review_url = '/review/' + pk
    pk = int(pk)
    prod_detail = search_detail_prod_info(pk, 'detail')
    return render_template('product_detail.html', prod_detail=prod_detail[0], review_url=review_url)


@app.route('/review/<pk>')
def review(pk):
    pk = int(pk)
    ProductName = search_detail_prod_info(pk, 'name')
    review_info = search_reviews(pk)
    # print(review_info)
    return render_template('review.html', review_info=review_info, ProductName=ProductName[0])


if __name__ == "__main__":
    app.run(debug=False)