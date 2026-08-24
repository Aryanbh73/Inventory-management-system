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

sys.path.insert(0, BACKEND_PATH)


import streamlit as st
import pandas as pd

from datetime import datetime

from database import get_db_connection
from excel_sync import create_excel_file  # type: ignore[import-not-found]
from google_sheets import update_google_sheet # type: ignore[import-not-found]

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

total_products = int(
    metrics["total_products"] or 0
)

total_stock = int(
    metrics["total_stock"] or 0
)

low_stock = int(
    metrics["low_stock"] or 0
)

out_of_stock = int(
    metrics["out_of_stock"] or 0
)

inventory_value = float(
    metrics["inventory_value"] or 0
)


col1, col2, col3, col4, col5 = st.columns(5)


with col1:

    st.metric(
        "Total Products",
        total_products
    )


with col2:

    st.metric(
        "Total Stock",
        total_stock
    )


with col3:

    st.metric(
        "Low Stock",
        low_stock
    )


with col4:

    st.metric(
        "Out of Stock",
        out_of_stock
    )


with col5:

    st.metric(
        "Inventory Value",
        f"₹{inventory_value:,.2f}"
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

def make_purchase(product_id, supplier_id, quantity, price):

    connection = get_db_connection()
    cursor = connection.cursor()

    # Check product
    cursor.execute(
        """
        SELECT product_id
        FROM products
        WHERE product_id = %s
        """,
        (product_id,)
    )

    product = cursor.fetchone()

    if not product:
        cursor.close()
        connection.close()
        return False, "Product not found."

    # Check supplier
    cursor.execute(
        """
        SELECT supplier_id
        FROM suppliers
        WHERE supplier_id = %s
        """,
        (supplier_id,)
    )

    supplier = cursor.fetchone()

    if not supplier:
        cursor.close()
        connection.close()
        return False, "Supplier not found."

    total_amount = quantity * price

    # Increase stock
    cursor.execute(
        """
        UPDATE products
        SET current_stock = current_stock + %s
        WHERE product_id = %s
        """,
        (quantity, product_id)
    )

    # Add transaction
    cursor.execute(
        """
        INSERT INTO transactions
        (
            product_id,
            transaction_type,
            quantity,
            price,
            total_amount,
            transaction_date
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            product_id,
            "PURCHASE",
            quantity,
            price,
            total_amount,
            datetime.now()
        )
    )

    connection.commit()

    cursor.close()
    connection.close()

    create_excel_file()

    synchronize_data()


    return True, "Purchase added successfully."

def make_sale(product_id, quantity, price):

    connection = get_db_connection()
    cursor = connection.cursor()

    # Check current stock
    cursor.execute(
        """
        SELECT current_stock
        FROM products
        WHERE product_id = %s
        """,
        (product_id,)
    )

    product = cursor.fetchone()

    if not product:
        cursor.close()
        connection.close()
        return False, "Product not found."

    current_stock = product[0]

    # Check stock availability
    if quantity > current_stock:

        cursor.close()
        connection.close()

        return False, (
            f"Not enough stock. "
            f"Available stock: {current_stock}"
        )

    total_amount = quantity * price

    # Decrease stock
    cursor.execute(
        """
        UPDATE products
        SET current_stock = current_stock - %s
        WHERE product_id = %s
        """,
        (quantity, product_id)
    )

    # Add transaction
    cursor.execute(
        """
        INSERT INTO transactions
        (
            product_id,
            transaction_type,
            quantity,
            price,
            total_amount,
            transaction_date
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            product_id,
            "SALE",
            quantity,
            price,
            total_amount,
            datetime.now()
        )
    )

    connection.commit()

    cursor.close()
    connection.close()

    create_excel_file()

    synchronize_data()


    return True, "Sale added successfully."

def get_product_list():

    connection = get_db_connection()

    query = """
        SELECT
            product_id,
            product_name,
            selling_price,
            current_stock
        FROM products
        ORDER BY product_name
    """

    df = pd.read_sql(query, connection)

    connection.close()

    return df

def get_supplier_list():

    connection = get_db_connection()

    query = """
        SELECT
            supplier_id,
            supplier_name
        FROM suppliers
        ORDER BY supplier_name
    """

    df = pd.read_sql(query, connection)

    connection.close()

    return df

st.divider()

st.header("🛒 Purchase Product")

products = get_product_list()
suppliers = get_supplier_list()

if not products.empty and not suppliers.empty:

    product_options = {
        f"{row['product_name']} (Stock: {row['current_stock']})":
        row["product_id"]
        for _, row in products.iterrows()
    }

    supplier_options = {
        row["supplier_name"]:
        row["supplier_id"]
        for _, row in suppliers.iterrows()
    }

    with st.form("purchase_form"):

        selected_product = st.selectbox(
            "Product",
            list(product_options.keys())
        )

        selected_supplier = st.selectbox(
            "Supplier",
            list(supplier_options.keys())
        )

        quantity = st.number_input(
            "Quantity",
            min_value=1,
            step=1
        )

        price = st.number_input(
            "Purchase Price",
            min_value=0.0,
            step=0.01
        )

        submitted = st.form_submit_button(
            "Add Purchase"
        )

        if submitted:

            product_id = product_options[selected_product]

            supplier_id = supplier_options[selected_supplier]

            success, message = make_purchase(
                product_id,
                supplier_id,
                quantity,
                price
            )

            if success:
                st.success(message)
                st.rerun()

            else:
                st.error(message)

else:

    st.warning(
        "Please add at least one product and supplier first."
    )

st.divider()

st.header("💰 Sell Product")

if not products.empty:

    product_options = {
        f"{row['product_name']} (Stock: {row['current_stock']})":
        row["product_id"]
        for _, row in products.iterrows()
    }

    with st.form("sale_form"):

        selected_product = st.selectbox(
            "Product",
            list(product_options.keys()),
            key="sale_product"
        )

        quantity = st.number_input(
            "Quantity",
            min_value=1,
            step=1,
            key="sale_quantity"
        )

        price = st.number_input(
            "Selling Price",
            min_value=0.0,
            step=0.01,
            key="sale_price"
        )

        submitted = st.form_submit_button(
            "Complete Sale"
        )

        if submitted:

            product_id = product_options[selected_product]

            success, message = make_sale(
                product_id,
                quantity,
                price
            )

            if success:
                st.success(message)
                st.rerun()

            else:
                st.error(message)

else:

    st.warning("No products available.")

def synchronize_data():

    try:

        create_excel_file()

        print("Excel synchronization completed.")

    except Exception as e:

        print("Excel synchronization failed:", e)


    try:

        update_google_sheet()

        print("Google Sheets synchronization completed.")

    except Exception as e:

        print("Google Sheets synchronization failed:", e)

st.sidebar.title("⚙️ System")

if st.sidebar.button("🔄 Sync Data"):

    synchronize_data()

    st.sidebar.success(
        "Excel and Google Sheets synchronized!"
    )