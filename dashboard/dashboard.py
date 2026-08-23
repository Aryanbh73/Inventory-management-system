import sys
import os

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "backend")
    )
)

import streamlit as st
import pandas as pd

from database import get_db_connection

st.set_page_config(
    page_title="Smart Inventory Dashboard",
    page_icon="📦",
    layout="wide"
)


st.title("📦 Smart Inventory Management System")

st.write(
    "Real-time inventory monitoring and analytics dashboard"
)
def get_dashboard_metrics():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT

            COUNT(*) AS total_products,

            COALESCE(SUM(current_stock), 0)
            AS total_stock,

            COALESCE(
                SUM(
                    current_stock * purchase_price
                ),
                0
            ) AS inventory_value,

            SUM(
                CASE
                    WHEN current_stock > 0
                    AND current_stock <= minimum_stock
                    THEN 1
                    ELSE 0
                END
            ) AS low_stock,

            SUM(
                CASE
                    WHEN current_stock = 0
                    THEN 1
                    ELSE 0
                END
            ) AS out_of_stock

        FROM products
    """

    cursor.execute(query)

    result = cursor.fetchone()

    cursor.close()
    connection.close()

    return result

metrics = get_dashboard_metrics()
col1, col2, col3, col4, col5 = st.columns(5)
with col1:

    st.metric(
        "Total Products",
        metrics["total_products"]
    )


with col2:

    st.metric(
        "Total Stock",
        metrics["total_stock"]
    )


with col3:

    st.metric(
        "Low Stock",
        metrics["low_stock"]
    )


with col4:

    st.metric(
        "Out of Stock",
        metrics["out_of_stock"]
    )


with col5:

    st.metric(
        "Inventory Value",
        f"₹{metrics['inventory_value']:,.2f}"
    )

def get_low_stock_products():

    connection = get_db_connection()

    query = """
        SELECT
            p.product_name,
            p.category,
            s.supplier_name,
            p.current_stock,
            p.minimum_stock,
            p.location

        FROM products p

        LEFT JOIN suppliers s
            ON p.supplier_id = s.supplier_id

        WHERE p.current_stock > 0
        AND p.current_stock <= p.minimum_stock

        ORDER BY p.current_stock ASC
    """

    df = pd.read_sql(query, connection)

    connection.close()

    return df

st.subheader("⚠️ Low Stock Products")

low_stock = get_low_stock_products()

if low_stock.empty:

    st.success("No low-stock products.")

else:

    st.dataframe(
        low_stock,
        use_container_width=True
    )

def get_out_of_stock_products():

    connection = get_db_connection()

    query = """
        SELECT
            p.product_name,
            p.category,
            s.supplier_name,
            p.current_stock,
            p.location

        FROM products p

        LEFT JOIN suppliers s
            ON p.supplier_id = s.supplier_id

        WHERE p.current_stock = 0

        ORDER BY p.product_name
    """

    df = pd.read_sql(query, connection)

    connection.close()

    return df

st.subheader("🚨 Out of Stock")

out_of_stock = get_out_of_stock_products()

if out_of_stock.empty:

    st.success("No out-of-stock products.")

else:

    st.dataframe(
        out_of_stock,
        use_container_width=True
    )

def get_sales_data():

    connection = get_db_connection()

    query = """
        SELECT
            DATE(transaction_date) AS date,
            SUM(total_amount) AS sales

        FROM transactions

        WHERE transaction_type = 'SALE'

        GROUP BY DATE(transaction_date)

        ORDER BY date
    """

    df = pd.read_sql(query, connection)

    connection.close()

    return df

st.subheader("📈 Sales Overview")

sales = get_sales_data()

if not sales.empty:

    sales["date"] = pd.to_datetime(
        sales["date"]
    )

    sales = sales.set_index("date")

    st.line_chart(
        sales["sales"]
    )

else:

    st.info("No sales data available yet.")

def get_category_stock():

    connection = get_db_connection()

    query = """
        SELECT
            category,
            SUM(current_stock) AS stock

        FROM products

        GROUP BY category

        ORDER BY stock DESC
    """

    df = pd.read_sql(query, connection)

    connection.close()

    return df

st.subheader("📊 Stock by Category")

category_stock = get_category_stock()

if not category_stock.empty:

    st.bar_chart(
        category_stock.set_index("category")
    )

