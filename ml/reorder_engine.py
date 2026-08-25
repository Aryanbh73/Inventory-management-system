import sys
import os

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

BACKEND_PATH = os.path.join(
    PROJECT_ROOT,
    "backend"
)

ML_PATH = os.path.join(
    PROJECT_ROOT,
    "ml"
)

sys.path.insert(0, BACKEND_PATH)
sys.path.insert(0, ML_PATH)


import pandas as pd

from database import get_db_connection
from forecast import forecast_product

def get_all_products():

    connection = get_db_connection()

    query = """
        SELECT
            p.product_id,
            p.product_name,
            p.category,
            p.current_stock,
            p.minimum_stock,
            p.purchase_price,
            s.supplier_name

        FROM products p

        LEFT JOIN suppliers s
            ON p.supplier_id = s.supplier_id

        ORDER BY p.product_name
    """

    df = pd.read_sql(
        query,
        connection
    )

    connection.close()

    return df

def calculate_reorder_quantity(
    current_stock,
    forecast_demand,
    safety_stock
):

    required_stock = (
        forecast_demand +
        safety_stock
    )

    reorder_quantity = (
        required_stock -
        current_stock
    )

    return max(
        0,
        round(reorder_quantity)
    )

def generate_reorder_recommendations():

    products = get_all_products()

    recommendations = []

    for _, product in products.iterrows():

        product_id = int(
            product["product_id"]
        )

        current_stock = int(
            product["current_stock"] or 0
        )

        minimum_stock = int(
            product["minimum_stock"] or 0
        )

        # Safety stock
        safety_stock = max(
            minimum_stock,
            5
        )

        # AI forecast
        forecast_30 = forecast_product(
            product_id,
            30
        )

        reorder_quantity = calculate_reorder_quantity(
            current_stock,
            forecast_30,
            safety_stock
        )

        if current_stock == 0:

            status = "OUT OF STOCK"

        elif reorder_quantity > 0:

            status = "REORDER"

        else:

            status = "HEALTHY"

        recommendations.append({

            "product_id": product_id,

            "product_name":
                product["product_name"],

            "category":
                product["category"],

            "supplier":
                product["supplier_name"],

            "current_stock":
                current_stock,

            "minimum_stock":
                minimum_stock,

            "forecast_30_days":
                forecast_30,

            "safety_stock":
                safety_stock,

            "recommended_order":
                reorder_quantity,

            "purchase_price":
                float(
                    product["purchase_price"] or 0
                ),

            "status":
                status
        })

    return pd.DataFrame(
        recommendations
    )

if __name__ == "__main__":

    recommendations = (
        generate_reorder_recommendations()
    )

    print(
        recommendations.to_string(
            index=False
        )
    )