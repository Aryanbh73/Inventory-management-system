from flask import Flask, jsonify, request
from database import get_db_connection
from products import add_product
from suppliers import add_supplier, get_all_suppliers
from suppliers import (
    add_supplier,
    get_all_suppliers,
    get_supplier_products
)
from purchases import add_purchase
from purchases import add_purchase, get_purchase_history
from sales import add_sale, get_sales_history

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


# ---------------- PRODUCTS ----------------

@app.route("/products", methods=["POST"])
def create_product():

    data = request.json

    add_product(
        data["product_name"],
        data["category"],
        data["supplier_id"],
        data["purchase_price"],
        data["selling_price"],
        data["current_stock"],
        data["minimum_stock"],
        data["location"]
    )

    return jsonify({
        "message": "Product added successfully"
    })


# ---------------- SUPPLIERS ----------------

@app.route("/suppliers", methods=["POST"])
def create_supplier():

    data = request.json

    supplier_id = add_supplier(
        data["supplier_name"],
        data.get("phone"),
        data.get("email"),
        data.get("address")
    )

    return jsonify({
        "message": "Supplier added successfully",
        "supplier_id": supplier_id
    })


@app.route("/suppliers", methods=["GET"])
def get_suppliers():

    suppliers = get_all_suppliers()

    return jsonify(suppliers)

@app.route("/suppliers/<int:supplier_id>/products", methods=["GET"])
def supplier_products(supplier_id):

    products = get_supplier_products(supplier_id)

    return jsonify(products)

@app.route("/purchases", methods=["POST"])
def create_purchase():

    data = request.json

    result = add_purchase(
        data["product_id"],
        data["supplier_id"],
        data["quantity"],
        data["price"]
    )

    if not result["success"]:
        return jsonify(result), 400

    return jsonify(result), 201

@app.route("/purchases", methods=["GET"])
def purchase_history():

    purchases = get_purchase_history()

    return jsonify(purchases)

@app.route("/sales", methods=["POST"])
def create_sale():

    data = request.json

    result = add_sale(
        data["product_id"],
        data["quantity"],
        data["price"]
    )

    if not result["success"]:
        return jsonify(result), 400

    return jsonify(result), 201

@app.route("/sales", methods=["GET"])
def sales_history():

    sales = get_sales_history()

    return jsonify(sales)

# ---------------- RUN SERVER ----------------

if __name__ == "__main__":
    app.run(debug=True)