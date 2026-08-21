from flask import Flask, jsonify, request
from database import get_db_connection
from products import add_product

app = Flask(__name__)


@app.route("/")
def home():

    return "Smart Inventory Management System is running!"


@app.route("/test-db")
def test_database():

    connection = get_db_connection()

    cursor = connection.cursor()

    cursor.execute("SELECT DATABASE()")

    database = cursor.fetchone()

    cursor.close()
    connection.close()

    return jsonify({
        "status": "success",
        "database": database[0]
    })


@app.route("/products", methods=["POST"])
def create_product():

    data = request.json

    add_product(
        data["product_name"],
        data["category"],
        data["purchase_price"],
        data["selling_price"],
        data["current_stock"],
        data["minimum_stock"],
        data["location"]
    )

    return jsonify({
        "message": "Product added successfully"
    })


if __name__ == "__main__":
    app.run(debug=True)