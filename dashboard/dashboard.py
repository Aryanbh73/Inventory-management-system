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


import streamlit as st
import pandas as pd

from datetime import datetime, timedelta

from database import get_db_connection
from excel_sync import create_excel_file  # type: ignore[import-not-found]
from google_sheets import update_google_sheet # type: ignore[import-not-found]
from forecast import forecast_product # type: ignore[import-not-found]
from reorder_engine import (generate_reorder_recommendations) # type: ignore[import-not-found]

st.set_page_config(
    page_title="Smart Inventory Dashboard",
    page_icon="📦",
    layout="wide"
)

st.title("📦 Smart Inventory Management System")

st.sidebar.header("📅 Filters")

today = datetime.now().date()

start_date = st.sidebar.date_input(
    "Start Date",
    today - timedelta(days=30)
)

end_date = st.sidebar.date_input(
    "End Date",
    today
)

st.sidebar.divider()

if st.sidebar.button("🔄 Refresh Dashboard"):

    st.cache_data.clear()

    st.rerun()

if start_date > end_date:
    st.error("Start date cannot be after end date.")
    st.stop()

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

st.subheader("🤖 AI Demand Forecasting")
connection = get_db_connection()

products_df = pd.read_sql(
    """
    SELECT
        product_id,
        product_name,
        current_stock
    FROM products
    ORDER BY product_name
    """,
    connection
)

connection.close()

selected_product = st.selectbox(
    "Select Product",
    products_df["product_name"].tolist(),
    key="ai_reorder_product"
)

selected_product_id = products_df.loc[
    products_df["product_name"] == selected_product,
    "product_id"
].iloc[0]

current_stock = products_df.loc[
    products_df["product_name"] == selected_product,
    "current_stock"
].iloc[0]

forecast_7 = forecast_product(
    int(selected_product_id),
    7
)

forecast_30 = forecast_product(
    int(selected_product_id),
    30
)

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "Current Stock",
        int(current_stock)
    )

with col2:

    st.metric(
        "7-Day Predicted Demand",
        int(forecast_7)
    )

with col3:

    st.metric(
        "30-Day Predicted Demand",
        int(forecast_30)
    )

if current_stock == 0:

    st.error(
        "🚨 OUT OF STOCK — Immediate reorder recommended."
    )

elif current_stock < forecast_7:

    st.error(
        "🔴 HIGH RISK — Stock may not cover "
        "the next 7 days of predicted demand."
    )

elif current_stock < forecast_30:

    st.warning(
        "🟡 REORDER SOON — Stock may not cover "
        "the predicted 30-day demand."
    )

else:

    st.success(
        "🟢 STOCK LEVEL LOOKS HEALTHY."
    )

st.subheader(
    "🤖 AI Reorder Recommendations"
)

recommendations = (
    generate_reorder_recommendations()
)
reorder_products = recommendations[
    recommendations["recommended_order"] > 0
]
if reorder_products.empty:

    st.success(
        "🟢 No products currently require reordering."
    )

else:

    st.dataframe(
        reorder_products[
            [
                "product_name",
                "supplier",
                "current_stock",
                "forecast_30_days",
                "safety_stock",
                "recommended_order",
                "status"
            ]
        ],
        use_container_width=True
    )

reorder_value = (
    reorder_products[
        "recommended_order"
    ]
    *
    reorder_products[
        "purchase_price"
    ]
).sum()

st.metric(
    "Estimated Reorder Cost",
    f"₹{reorder_value:,.2f}"
)

reorder_count = len(
    reorder_products
)

if reorder_count > 0:

    st.warning(
        f"⚠️ {reorder_count} "
        "product(s) require attention."
    )

display_df = reorder_products[
    [
        "product_name",
        "supplier",
        "current_stock",
        "forecast_30_days",
        "safety_stock",
        "recommended_order",
        "status"
    ]
].copy()

display_df.columns = [
    "Product",
    "Supplier",
    "Current Stock",
    "30-Day Forecast",
    "Safety Stock",
    "Recommended Order",
    "Status"
]

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)

st.subheader(
    "🛒 Create Purchase from AI Recommendation"
)

if not reorder_products.empty:

    product_options = (
        reorder_products["product_name"]
        .tolist()
    )

    selected_product = st.selectbox(
        "Select Product",
        product_options
    )

    selected_row = reorder_products[
        reorder_products["product_name"]
        == selected_product
    ].iloc[0]

    recommended_quantity = int(
        selected_row["recommended_order"]
    )

    st.write(
        f"AI Recommended Quantity: "
        f"**{recommended_quantity} units**"
    )

if st.button(
    "🛒 Prepare Purchase"
):

    st.session_state[
        "ai_purchase_product"
    ] = selected_product

    st.session_state[
        "ai_purchase_quantity"
    ] = recommended_quantity

    st.success(
        "Purchase recommendation prepared."
    )

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

st.sidebar.title("⚙️ System")

if st.sidebar.button("🔄 Sync Data"):

    synchronize_data()

    st.sidebar.success(
        "Excel and Google Sheets synchronized!"
    )

def get_sales_purchase_data(start_date, end_date):

    connection = get_db_connection()

    query = """
        SELECT
            DATE(transaction_date) AS date,

            SUM(
                CASE
                    WHEN transaction_type = 'SALE'
                    THEN total_amount
                    ELSE 0
                END
            ) AS sales,

            SUM(
                CASE
                    WHEN transaction_type = 'PURCHASE'
                    THEN total_amount
                    ELSE 0
                END
            ) AS purchases

        FROM transactions

        WHERE DATE(transaction_date)
        BETWEEN %s AND %s

        GROUP BY DATE(transaction_date)

        ORDER BY date
    """

    df = pd.read_sql(
        query,
        connection,
        params=(start_date, end_date)
    )

    connection.close()

    return df

st.subheader("📈 Sales vs Purchases")

sales_purchase = get_sales_purchase_data(
    start_date,
    end_date
)

if not sales_purchase.empty:

    sales_purchase["date"] = pd.to_datetime(
        sales_purchase["date"]
    )

    sales_purchase = sales_purchase.set_index("date")

    st.line_chart(
        sales_purchase[
            ["sales", "purchases"]
        ]
    )

else:

    st.info("No transaction data for this period.")

def get_profit_data(start_date, end_date):

    connection = get_db_connection()

    query = """
        SELECT

            COALESCE(
                SUM(
                    CASE
                        WHEN t.transaction_type = 'SALE'
                        THEN t.total_amount
                        ELSE 0
                    END
                ),
                0
            ) AS revenue,

            COALESCE(
                SUM(
                    CASE
                        WHEN t.transaction_type = 'SALE'
                        THEN
                            t.quantity * p.purchase_price
                        ELSE 0
                    END
                ),
                0
            ) AS cost

        FROM transactions t

        JOIN products p
            ON t.product_id = p.product_id

        WHERE DATE(t.transaction_date)
        BETWEEN %s AND %s
    """

    df = pd.read_sql(
        query,
        connection,
        params=(start_date, end_date)
    )

    connection.close()

    return df

profit_data = get_profit_data(
    start_date,
    end_date
)

revenue = float(
    profit_data["revenue"].iloc[0] or 0
)

cost = float(
    profit_data["cost"].iloc[0] or 0
)

profit = revenue - cost

st.subheader("💰 Financial Overview")

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "Revenue",
        f"₹{revenue:,.2f}"
    )

with col2:

    st.metric(
        "Cost of Goods",
        f"₹{cost:,.2f}"
    )

with col3:

    st.metric(
        "Profit",
        f"₹{profit:,.2f}"
    )

def get_top_products(start_date, end_date):

    connection = get_db_connection()

    query = """
        SELECT

            p.product_name,

            SUM(t.quantity) AS units_sold,

            SUM(t.total_amount) AS revenue

        FROM transactions t

        JOIN products p
            ON t.product_id = p.product_id

        WHERE t.transaction_type = 'SALE'

        AND DATE(t.transaction_date)
        BETWEEN %s AND %s

        GROUP BY
            p.product_id,
            p.product_name

        ORDER BY units_sold DESC

        LIMIT 10
    """

    df = pd.read_sql(
        query,
        connection,
        params=(start_date, end_date)
    )

    connection.close()

    return df

st.subheader("🏆 Top Selling Products")

top_products = get_top_products(
    start_date,
    end_date
)

if not top_products.empty:

    st.dataframe(
        top_products,
        use_container_width=True
    )

else:

    st.info("No sales data available.")

def get_category_inventory():

    connection = get_db_connection()

    query = """
        SELECT
            category,
            SUM(current_stock) AS stock,
            SUM(
                current_stock * purchase_price
            ) AS inventory_value

        FROM products

        GROUP BY category

        ORDER BY stock DESC
    """

    df = pd.read_sql(
        query,
        connection
    )

    connection.close()

    return df

st.subheader("📦 Inventory by Category")

category_data = get_category_inventory()

if not category_data.empty:

    col1, col2 = st.columns(2)

    with col1:

        st.bar_chart(
            category_data.set_index(
                "category"
            )["stock"]
        )

    with col2:

        st.dataframe(
            category_data,
            use_container_width=True
        )

def get_slow_moving_products():

    connection = get_db_connection()

    query = """
        SELECT

            p.product_name,

            p.current_stock,

            COALESCE(
                SUM(
                    CASE
                        WHEN t.transaction_type = 'SALE'
                        THEN t.quantity
                        ELSE 0
                    END
                ),
                0
            ) AS units_sold

        FROM products p

        LEFT JOIN transactions t
            ON p.product_id = t.product_id

        GROUP BY
            p.product_id,
            p.product_name,
            p.current_stock

        HAVING units_sold <= 2

        ORDER BY
            p.current_stock DESC
    """

    df = pd.read_sql(
        query,
        connection
    )

    connection.close()

    return df

st.subheader("🐌 Slow-Moving Products")

slow_products = get_slow_moving_products()

if not slow_products.empty:

    st.dataframe(
        slow_products,
        use_container_width=True
    )

else:

    st.success(
        "No slow-moving products detected."
    )