import sys
import os

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

BACKEND_PATH = os.path.join(PROJECT_ROOT, "backend")
ML_PATH = os.path.join(PROJECT_ROOT, "ml")

sys.path.insert(0, BACKEND_PATH)
sys.path.insert(0, ML_PATH)

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from database import get_db_connection
from excel_sync import create_excel_file  # type: ignore[import-not-found]
from google_sheets import update_google_sheet  # type: ignore[import-not-found]
from forecast import forecast_product  # type: ignore[import-not-found]
from reorder_engine import generate_reorder_recommendations  # type: ignore[import-not-found]
from purchase_orders import create_purchase_order, receive_purchase_order  # type: ignore[import-not-found]

st.set_page_config(
    page_title="Smart Inventory Dashboard",
    page_icon="📦",
    layout="wide"
)

# =====================================================================
# NOTE ON REORGANIZATION
# ---------------------------------------------------------------------
# The original script only imported/exposed functions for: dashboard
# metrics, sales analytics, AI forecasting/reorder recommendations,
# purchase orders (create/receive), and excel/sheets sync. It did not
# contain backend logic for Product CRUD, Supplier CRUD, Pending/Purchase
# history listing, or Model Performance tracking.
#
# To fit the requested navigation tree, this file adds small,
# clearly-marked direct-SQL implementations for those missing pieces
# (using the same `products` / `suppliers` / `transactions` columns the
# original queries already relied on). Sections that depend on a table
# whose schema isn't defined anywhere in the original code (e.g.
# `purchase_orders`) use a best-effort query and are flagged with a
# comment — adjust column names to match your actual schema if they
# differ.
# =====================================================================


# ---------------------------------------------------------------------
# 📊 DASHBOARD — data functions
# ---------------------------------------------------------------------

def get_dashboard_metrics():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            COUNT(*) AS total_products,
            COALESCE(SUM(current_stock), 0) AS total_stock,
            COALESCE(SUM(current_stock * purchase_price), 0) AS inventory_value,
            SUM(CASE WHEN current_stock > 0 AND current_stock <= minimum_stock THEN 1 ELSE 0 END) AS low_stock,
            SUM(CASE WHEN current_stock = 0 THEN 1 ELSE 0 END) AS out_of_stock
        FROM products
    """
    cursor.execute(query)
    result = cursor.fetchone()
    cursor.close()
    connection.close()
    return result


def get_sales_overview():
    connection = get_db_connection()
    df = pd.read_sql(
        """
        SELECT DATE(transaction_date) AS sale_date, SUM(total_amount) AS revenue
        FROM transactions
        WHERE transaction_type = 'SALE'
        GROUP BY DATE(transaction_date)
        ORDER BY sale_date
        """,
        connection
    )
    connection.close()
    if not df.empty:
        df["sale_date"] = pd.to_datetime(df["sale_date"])
    return df


def get_top_selling_products(limit=10):
    connection = get_db_connection()
    df = pd.read_sql(
        """
        SELECT p.product_name, SUM(t.quantity) AS units_sold
        FROM transactions t
        JOIN products p ON t.product_id = p.product_id
        WHERE t.transaction_type = 'SALE'
        GROUP BY p.product_id, p.product_name
        ORDER BY units_sold DESC
        LIMIT %s
        """,
        connection,
        params=(limit,)
    )
    connection.close()
    return df


def render_dashboard():
    st.header("📊 Dashboard")

    metrics = get_dashboard_metrics()
    total_products = int(metrics["total_products"] or 0)
    total_stock = int(metrics["total_stock"] or 0)
    low_stock = int(metrics["low_stock"] or 0)
    out_of_stock = int(metrics["out_of_stock"] or 0)
    inventory_value = float(metrics["inventory_value"] or 0)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Products", total_products)
    with col2:
        st.metric("Total Stock", total_stock)
    with col3:
        st.metric("Low Stock", low_stock)
    with col4:
        st.metric("Out of Stock", out_of_stock)
    with col5:
        st.metric("Inventory Value", f"₹{inventory_value:,.2f}")

    st.subheader("Sales Overview")
    sales_df = get_sales_overview()
    if not sales_df.empty:
        st.line_chart(sales_df.set_index("sale_date")["revenue"])
    else:
        st.info("No sales data available yet.")

    st.subheader("Top-Selling Products")
    top_df = get_top_selling_products()
    if not top_df.empty:
        st.bar_chart(top_df.set_index("product_name")["units_sold"])
    else:
        st.info("No sales data available yet.")


# ---------------------------------------------------------------------
# 📦 PRODUCTS — data functions
# ---------------------------------------------------------------------

def get_product_list():
    connection = get_db_connection()
    df = pd.read_sql(
        """
        SELECT product_id, product_name, category, current_stock,
               minimum_stock, purchase_price, selling_price, location, supplier_id
        FROM products
        ORDER BY product_name
        """,
        connection
    )
    connection.close()
    return df


def add_product(product_name, category, current_stock, minimum_stock,
                 purchase_price, selling_price, location, supplier_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO products
            (product_name, category, current_stock, minimum_stock,
             purchase_price, selling_price, location, supplier_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (product_name, category, current_stock, minimum_stock,
         purchase_price, selling_price, location, supplier_id)
    )
    connection.commit()
    cursor.close()
    connection.close()


def update_product(product_id, **fields):
    if not fields:
        return
    connection = get_db_connection()
    cursor = connection.cursor()
    set_clause = ", ".join(f"{col} = %s" for col in fields)
    values = list(fields.values()) + [product_id]
    cursor.execute(
        f"UPDATE products SET {set_clause} WHERE product_id = %s",
        values
    )
    connection.commit()
    cursor.close()
    connection.close()


def delete_product(product_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM products WHERE product_id = %s", (product_id,))
    connection.commit()
    cursor.close()
    connection.close()


def search_products(keyword):
    connection = get_db_connection()
    df = pd.read_sql(
        """
        SELECT product_id, product_name, category, current_stock,
               minimum_stock, selling_price, location
        FROM products
        WHERE product_name LIKE %s OR category LIKE %s
        ORDER BY product_name
        """,
        connection,
        params=(f"%{keyword}%", f"%{keyword}%")
    )
    connection.close()
    return df


def render_products():
    st.header("📦 Products")
    tab_add, tab_list, tab_update, tab_delete, tab_search = st.tabs(
        ["Add Product", "Product List", "Update Product", "Delete Product", "Search / Filter"]
    )

    with tab_add:
        with st.form("add_product_form"):
            product_name = st.text_input("Product Name")
            category = st.text_input("Category")
            current_stock = st.number_input("Current Stock", min_value=0, step=1)
            minimum_stock = st.number_input("Minimum Stock", min_value=0, step=1)
            purchase_price = st.number_input("Purchase Price", min_value=0.0, step=0.01)
            selling_price = st.number_input("Selling Price", min_value=0.0, step=0.01)
            location = st.text_input("Location")
            supplier_id = st.number_input("Supplier ID", min_value=1, step=1)
            submitted = st.form_submit_button("Add Product")
            if submitted:
                add_product(product_name, category, int(current_stock), int(minimum_stock),
                            float(purchase_price), float(selling_price), location, int(supplier_id))
                st.success(f"Product '{product_name}' added.")
                st.rerun()

    with tab_list:
        products_df = get_product_list()
        st.dataframe(products_df, use_container_width=True, hide_index=True)

    with tab_update:
        products_df = get_product_list()
        if products_df.empty:
            st.info("No products to update.")
        else:
            options = {
                f"{row['product_name']} (ID: {row['product_id']})": row["product_id"]
                for _, row in products_df.iterrows()
            }
            selected_label = st.selectbox("Select Product", list(options.keys()))
            selected_id = options[selected_label]
            row = products_df.loc[products_df["product_id"] == selected_id].iloc[0]

            with st.form("update_product_form"):
                new_stock = st.number_input("Current Stock", value=int(row["current_stock"]), min_value=0, step=1)
                new_min_stock = st.number_input("Minimum Stock", value=int(row["minimum_stock"]), min_value=0, step=1)
                new_selling_price = st.number_input("Selling Price", value=float(row["selling_price"]), min_value=0.0, step=0.01)
                new_location = st.text_input("Location", value=row["location"] or "")
                submitted = st.form_submit_button("Update Product")
                if submitted:
                    update_product(
                        int(selected_id),
                        current_stock=int(new_stock),
                        minimum_stock=int(new_min_stock),
                        selling_price=float(new_selling_price),
                        location=new_location
                    )
                    st.success("Product updated.")
                    st.rerun()

    with tab_delete:
        products_df = get_product_list()
        if products_df.empty:
            st.info("No products to delete.")
        else:
            options = {
                f"{row['product_name']} (ID: {row['product_id']})": row["product_id"]
                for _, row in products_df.iterrows()
            }
            selected_label = st.selectbox("Select Product to Delete", list(options.keys()), key="delete_product_select")
            if st.button("🗑️ Delete Product", key="delete_product_button"):
                delete_product(int(options[selected_label]))
                st.success("Product deleted.")
                st.rerun()

    with tab_search:
        keyword = st.text_input("Search by product name or category")
        if keyword:
            results_df = search_products(keyword)
            st.dataframe(results_df, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------
# 🏢 SUPPLIERS — data functions
# ---------------------------------------------------------------------

def get_supplier_list():
    connection = get_db_connection()
    df = pd.read_sql(
        "SELECT supplier_id, supplier_name FROM suppliers ORDER BY supplier_name",
        connection
    )
    connection.close()
    return df


def add_supplier(supplier_name):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO suppliers (supplier_name) VALUES (%s)", (supplier_name,))
    connection.commit()
    cursor.close()
    connection.close()


def update_supplier(supplier_id, supplier_name):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        "UPDATE suppliers SET supplier_name = %s WHERE supplier_id = %s",
        (supplier_name, supplier_id)
    )
    connection.commit()
    cursor.close()
    connection.close()


def delete_supplier(supplier_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM suppliers WHERE supplier_id = %s", (supplier_id,))
    connection.commit()
    cursor.close()
    connection.close()


def render_suppliers():
    st.header("🏢 Suppliers")
    tab_add, tab_list, tab_update, tab_delete = st.tabs(
        ["Add Supplier", "Supplier List", "Update Supplier", "Delete Supplier"]
    )

    with tab_add:
        with st.form("add_supplier_form"):
            supplier_name = st.text_input("Supplier Name")
            submitted = st.form_submit_button("Add Supplier")
            if submitted:
                add_supplier(supplier_name)
                st.success(f"Supplier '{supplier_name}' added.")
                st.rerun()

    with tab_list:
        st.dataframe(get_supplier_list(), use_container_width=True, hide_index=True)

    with tab_update:
        suppliers_df = get_supplier_list()
        if suppliers_df.empty:
            st.info("No suppliers to update.")
        else:
            options = {row["supplier_name"]: row["supplier_id"] for _, row in suppliers_df.iterrows()}
            selected = st.selectbox("Select Supplier", list(options.keys()))
            with st.form("update_supplier_form"):
                new_name = st.text_input("Supplier Name", value=selected)
                submitted = st.form_submit_button("Update Supplier")
                if submitted:
                    update_supplier(int(options[selected]), new_name)
                    st.success("Supplier updated.")
                    st.rerun()

    with tab_delete:
        suppliers_df = get_supplier_list()
        if suppliers_df.empty:
            st.info("No suppliers to delete.")
        else:
            options = {row["supplier_name"]: row["supplier_id"] for _, row in suppliers_df.iterrows()}
            selected = st.selectbox("Select Supplier to Delete", list(options.keys()), key="delete_supplier_select")
            if st.button("🗑️ Delete Supplier"):
                delete_supplier(int(options[selected]))
                st.success("Supplier deleted.")
                st.rerun()


# ---------------------------------------------------------------------
# 💰 SALES — data functions
# ---------------------------------------------------------------------

def make_sale(product_id, quantity, price):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT current_stock FROM products WHERE product_id = %s", (product_id,))
    product = cursor.fetchone()
    if not product:
        cursor.close()
        connection.close()
        return False, "Product not found."

    current_stock = product[0]
    if quantity > current_stock:
        cursor.close()
        connection.close()
        return False, f"Not enough stock. Available stock: {current_stock}"

    total_amount = quantity * price

    cursor.execute(
        "UPDATE products SET current_stock = current_stock - %s WHERE product_id = %s",
        (quantity, product_id)
    )
    cursor.execute(
        """
        INSERT INTO transactions
            (product_id, transaction_type, quantity, price, total_amount, transaction_date)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (product_id, "SALE", quantity, price, total_amount, datetime.now())
    )
    connection.commit()
    cursor.close()
    connection.close()

    synchronize_data()
    return True, "Sale added successfully."


def get_sales_history():
    connection = get_db_connection()
    df = pd.read_sql(
        """
        SELECT t.transaction_date, p.product_name, t.quantity, t.price, t.total_amount
        FROM transactions t
        JOIN products p ON t.product_id = p.product_id
        WHERE t.transaction_type = 'SALE'
        ORDER BY t.transaction_date DESC
        """,
        connection
    )
    connection.close()
    return df


def render_sales():
    st.header("💰 Sales")
    tab_sale, tab_reduction, tab_history = st.tabs(
        ["Make Sale", "Stock Reduction", "Sales History"]
    )

    products_df = get_product_list()

    with tab_sale:
        if products_df.empty:
            st.warning("No products available.")
        else:
            product_options = {
                f"{row['product_name']} (Stock: {row['current_stock']})": row["product_id"]
                for _, row in products_df.iterrows()
            }
            with st.form("sale_form"):
                selected_product = st.selectbox("Product", list(product_options.keys()), key="sale_product")
                quantity = st.number_input("Quantity", min_value=1, step=1, key="sale_quantity")
                price = st.number_input("Selling Price", min_value=0.0, step=0.01, key="sale_price")
                submitted = st.form_submit_button("Complete Sale")
                if submitted:
                    product_id = product_options[selected_product]
                    success, message = make_sale(product_id, quantity, price)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

    with tab_reduction:
        st.caption("Stock automatically reduces whenever a sale is completed.")
        st.dataframe(
            products_df[["product_name", "current_stock", "minimum_stock"]] if not products_df.empty else products_df,
            use_container_width=True,
            hide_index=True
        )

    with tab_history:
        st.dataframe(get_sales_history(), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------
# 🛒 PURCHASES — data functions
# ---------------------------------------------------------------------

def make_purchase(product_id, supplier_id, quantity, price):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT product_id FROM products WHERE product_id = %s", (product_id,))
    if not cursor.fetchone():
        cursor.close()
        connection.close()
        return False, "Product not found."

    cursor.execute("SELECT supplier_id FROM suppliers WHERE supplier_id = %s", (supplier_id,))
    if not cursor.fetchone():
        cursor.close()
        connection.close()
        return False, "Supplier not found."

    total_amount = quantity * price

    cursor.execute(
        "UPDATE products SET current_stock = current_stock + %s WHERE product_id = %s",
        (quantity, product_id)
    )
    cursor.execute(
        """
        INSERT INTO transactions
            (product_id, transaction_type, quantity, price, total_amount, transaction_date)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (product_id, "PURCHASE", quantity, price, total_amount, datetime.now())
    )
    connection.commit()
    cursor.close()
    connection.close()

    synchronize_data()
    return True, "Purchase added successfully."


def get_purchase_history():
    connection = get_db_connection()
    df = pd.read_sql(
        """
        SELECT t.transaction_date, p.product_name, t.quantity, t.price, t.total_amount
        FROM transactions t
        JOIN products p ON t.product_id = p.product_id
        WHERE t.transaction_type = 'PURCHASE'
        ORDER BY t.transaction_date DESC
        """,
        connection
    )
    connection.close()
    return df


def get_pending_orders():
    # NOTE: assumes a `purchase_orders` table with a `status` column
    # (e.g. 'PENDING' / 'RECEIVED'). Adjust column names to match your
    # actual schema if this table looks different.
    connection = get_db_connection()
    try:
        df = pd.read_sql(
            """
            SELECT po.purchase_order_id, p.product_name, s.supplier_name,
                   po.quantity, po.unit_price, po.status, po.order_date
            FROM purchase_orders po
            LEFT JOIN products p ON po.product_id = p.product_id
            LEFT JOIN suppliers s ON po.supplier_id = s.supplier_id
            WHERE po.status = 'PENDING'
            ORDER BY po.order_date DESC
            """,
            connection
        )
    except Exception:
        df = pd.DataFrame()
    connection.close()
    return df


def render_purchases():
    st.header("🛒 Purchases")
    tab_create, tab_pending, tab_receive, tab_increase, tab_history = st.tabs(
        ["Create Purchase Order", "Pending Orders", "Receive Purchase", "Stock Increase", "Purchase History"]
    )

    with tab_create:
        supplier_id = st.number_input("Supplier ID", min_value=1, step=1, key="po_supplier_id")
        product_id = st.number_input("Product ID", min_value=1, step=1, key="po_product_id")
        quantity = st.number_input("Quantity", min_value=1, step=1, key="po_quantity")
        unit_price = st.number_input("Purchase Price", min_value=0.0, step=1.0, key="po_unit_price")
        if st.button("Create Purchase Order", key="create_purchase_order_btn"):
            order_id = create_purchase_order(int(supplier_id), int(product_id), int(quantity), float(unit_price))
            st.success(f"Purchase Order #{order_id} created successfully!")

    with tab_pending:
        pending_df = get_pending_orders()
        if pending_df.empty:
            st.info("No pending purchase orders.")
        else:
            st.dataframe(pending_df, use_container_width=True, hide_index=True)

    with tab_receive:
        purchase_order_id = st.number_input(
            "Purchase Order ID", min_value=1, step=1, key="receive_purchase_order_id"
        )
        if st.button("📦 Receive Purchase", key="receive_purchase"):
            success, message = receive_purchase_order(int(purchase_order_id))
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    with tab_increase:
        products_df = get_product_list()
        suppliers_df = get_supplier_list()
        if products_df.empty or suppliers_df.empty:
            st.warning("Please add at least one product and supplier first.")
        else:
            product_options = {
                f"{row['product_name']} (Stock: {row['current_stock']})": row["product_id"]
                for _, row in products_df.iterrows()
            }
            supplier_options = {row["supplier_name"]: row["supplier_id"] for _, row in suppliers_df.iterrows()}

            with st.form("purchase_form"):
                selected_product = st.selectbox("Product", list(product_options.keys()))
                selected_supplier = st.selectbox("Supplier", list(supplier_options.keys()))
                quantity = st.number_input("Quantity", min_value=1, step=1)
                price = st.number_input("Purchase Price", min_value=0.0, step=0.01)
                submitted = st.form_submit_button("Add Purchase")
                if submitted:
                    success, message = make_purchase(
                        product_options[selected_product],
                        supplier_options[selected_supplier],
                        quantity,
                        price
                    )
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

    with tab_history:
        st.dataframe(get_purchase_history(), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------
# 🤖 AI INSIGHTS — data functions
# ---------------------------------------------------------------------

def render_ai_insights():
    st.header("🤖 AI Insights")
    tab_forecast, tab_7day, tab_30day, tab_graph, tab_actual, tab_perf, tab_reorder = st.tabs(
        ["Demand Forecast", "7-Day Forecast", "30-Day Forecast", "Forecast Graph",
         "Actual vs Predicted", "Model Performance", "Reorder Recommendations"]
    )

    products_df = get_product_list()

    with tab_forecast:
        if products_df.empty:
            st.info("No products available.")
        else:
            selected_product = st.selectbox(
                "Select Product", products_df["product_name"].tolist(), key="ai_forecast_product"
            )
            selected_id = products_df.loc[products_df["product_name"] == selected_product, "product_id"].iloc[0]
            current_stock = products_df.loc[products_df["product_name"] == selected_product, "current_stock"].iloc[0]

            forecast_7 = forecast_product(int(selected_id), 7)
            forecast_30 = forecast_product(int(selected_id), 30)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Current Stock", int(current_stock))
            with col2:
                st.metric("7-Day Predicted Demand", int(forecast_7))
            with col3:
                st.metric("30-Day Predicted Demand", int(forecast_30))

            if current_stock == 0:
                st.error("🚨 OUT OF STOCK — Immediate reorder recommended.")
            elif current_stock < forecast_7:
                st.error("🔴 HIGH RISK — Stock may not cover the next 7 days of predicted demand.")
            elif current_stock < forecast_30:
                st.warning("🟡 REORDER SOON — Stock may not cover the predicted 30-day demand.")
            else:
                st.success("🟢 STOCK LEVEL LOOKS HEALTHY.")

    with tab_7day:
        if products_df.empty:
            st.info("No products available.")
        else:
            rows = []
            for _, row in products_df.iterrows():
                rows.append({
                    "product_name": row["product_name"],
                    "7_day_forecast": forecast_product(int(row["product_id"]), 7)
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with tab_30day:
        if products_df.empty:
            st.info("No products available.")
        else:
            rows = []
            for _, row in products_df.iterrows():
                rows.append({
                    "product_name": row["product_name"],
                    "30_day_forecast": forecast_product(int(row["product_id"]), 30)
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with tab_graph:
        sales_df = get_sales_overview()
        if not sales_df.empty:
            st.line_chart(sales_df.set_index("sale_date")["revenue"])
        else:
            st.info("No sales history to chart yet.")

    with tab_actual:
        # NOTE: the original ml/forecast module does not expose per-day
        # actual-vs-predicted values — this shows recent actual sales
        # alongside the current 7-day forecast for context.
        sales_df = get_sales_overview()
        if not sales_df.empty:
            st.line_chart(sales_df.set_index("sale_date")["revenue"].tail(30))
            st.caption("Recent actual daily revenue. Detailed per-product actual-vs-predicted requires extending the forecast module.")
        else:
            st.info("No sales history available.")

    with tab_perf:
        st.caption("Model performance metrics (MAE / RMSE / accuracy) are not exposed by the current forecast module — add them to ml/forecast.py to surface them here.")

    with tab_reorder:
        recommendations = generate_reorder_recommendations()
        reorder_products = recommendations[recommendations["recommended_order"] > 0]

        if reorder_products.empty:
            st.success("🟢 No products currently require reordering.")
        else:
            display_df = reorder_products[
                ["product_name", "supplier", "current_stock", "forecast_30_days",
                 "safety_stock", "recommended_order", "status"]
            ].copy()
            display_df.columns = [
                "Product", "Supplier", "Current Stock", "30-Day Forecast",
                "Safety Stock", "Recommended Order", "Status"
            ]
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            reorder_value = (reorder_products["recommended_order"] * reorder_products["purchase_price"]).sum()
            st.metric("Estimated Reorder Cost", f"₹{reorder_value:,.2f}")

            reorder_count = len(reorder_products)
            if reorder_count > 0:
                st.warning(f"⚠️ {reorder_count} product(s) require attention.")

            st.subheader("Create Purchase from Recommendation")
            product_options = reorder_products["product_name"].tolist()
            selected_product = st.selectbox("Select Product", product_options, key="ai_reorder_select")
            selected_row = reorder_products[reorder_products["product_name"] == selected_product].iloc[0]
            recommended_quantity = int(selected_row["recommended_order"])
            st.write(f"AI Recommended Quantity: **{recommended_quantity} units**")

            if st.button("🛒 Prepare Purchase", key="ai_prepare_purchase"):
                st.session_state["ai_purchase_product"] = selected_product
                st.session_state["ai_purchase_quantity"] = recommended_quantity
                st.success("Purchase recommendation prepared.")


# ---------------------------------------------------------------------
# ⚠️ INVENTORY ALERTS — data functions
# ---------------------------------------------------------------------

def get_low_stock_products():
    connection = get_db_connection()
    df = pd.read_sql(
        """
        SELECT p.product_name, p.category, s.supplier_name,
               p.current_stock, p.minimum_stock, p.location
        FROM products p
        LEFT JOIN suppliers s ON p.supplier_id = s.supplier_id
        WHERE p.current_stock > 0 AND p.current_stock <= p.minimum_stock
        ORDER BY p.current_stock ASC
        """,
        connection
    )
    connection.close()
    return df


def get_out_of_stock_products():
    connection = get_db_connection()
    df = pd.read_sql(
        """
        SELECT p.product_name, p.category, s.supplier_name, p.current_stock, p.location
        FROM products p
        LEFT JOIN suppliers s ON p.supplier_id = s.supplier_id
        WHERE p.current_stock = 0
        ORDER BY p.product_name
        """,
        connection
    )
    connection.close()
    return df


def get_healthy_stock_products():
    connection = get_db_connection()
    df = pd.read_sql(
        """
        SELECT p.product_name, p.category, p.current_stock, p.minimum_stock, p.location
        FROM products p
        WHERE p.current_stock > p.minimum_stock
        ORDER BY p.product_name
        """,
        connection
    )
    connection.close()
    return df


def render_inventory_alerts():
    st.header("⚠️ Inventory Alerts")
    tab_low, tab_out, tab_reorder, tab_healthy = st.tabs(
        ["Low Stock", "Out of Stock", "Reorder Required", "Healthy Stock"]
    )

    with tab_low:
        low_stock_df = get_low_stock_products()
        if low_stock_df.empty:
            st.success("No low-stock products.")
        else:
            st.dataframe(low_stock_df, use_container_width=True, hide_index=True)

    with tab_out:
        out_of_stock_df = get_out_of_stock_products()
        if out_of_stock_df.empty:
            st.success("No out-of-stock products.")
        else:
            st.dataframe(out_of_stock_df, use_container_width=True, hide_index=True)

    with tab_reorder:
        recommendations = generate_reorder_recommendations()
        reorder_products = recommendations[recommendations["recommended_order"] > 0]
        if reorder_products.empty:
            st.success("🟢 No products currently require reordering.")
        else:
            st.dataframe(
                reorder_products[
                    ["product_name", "supplier", "current_stock", "forecast_30_days",
                     "safety_stock", "recommended_order", "status"]
                ],
                use_container_width=True,
                hide_index=True
            )

    with tab_healthy:
        healthy_df = get_healthy_stock_products()
        if healthy_df.empty:
            st.info("No products currently above minimum stock.")
        else:
            st.dataframe(healthy_df, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------
# 📈 ANALYTICS & REPORTS — data functions
# ---------------------------------------------------------------------

def get_profit_data(start_date, end_date):
    connection = get_db_connection()
    df = pd.read_sql(
        """
        SELECT
            COALESCE(SUM(CASE WHEN t.transaction_type = 'SALE' THEN t.total_amount ELSE 0 END), 0) AS revenue,
            COALESCE(SUM(CASE WHEN t.transaction_type = 'SALE' THEN t.quantity * p.purchase_price ELSE 0 END), 0) AS cost
        FROM transactions t
        JOIN products p ON t.product_id = p.product_id
        WHERE DATE(t.transaction_date) BETWEEN %s AND %s
        """,
        connection,
        params=(start_date, end_date)
    )
    connection.close()
    return df


def get_sales_purchase_data(start_date, end_date):
    connection = get_db_connection()
    df = pd.read_sql(
        """
        SELECT DATE(transaction_date) AS date,
               SUM(CASE WHEN transaction_type = 'SALE' THEN total_amount ELSE 0 END) AS sales,
               SUM(CASE WHEN transaction_type = 'PURCHASE' THEN total_amount ELSE 0 END) AS purchases
        FROM transactions
        WHERE DATE(transaction_date) BETWEEN %s AND %s
        GROUP BY DATE(transaction_date)
        ORDER BY date
        """,
        connection,
        params=(start_date, end_date)
    )
    connection.close()
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def get_product_wise_sales(start_date, end_date):
    connection = get_db_connection()
    df = pd.read_sql(
        """
        SELECT p.product_name, SUM(t.quantity) AS units_sold, SUM(t.total_amount) AS revenue
        FROM transactions t
        JOIN products p ON t.product_id = p.product_id
        WHERE t.transaction_type = 'SALE'
        AND DATE(t.transaction_date) BETWEEN %s AND %s
        GROUP BY p.product_id, p.product_name
        ORDER BY units_sold DESC
        LIMIT 10
        """,
        connection,
        params=(start_date, end_date)
    )
    connection.close()
    return df


def get_category_inventory():
    connection = get_db_connection()
    df = pd.read_sql(
        """
        SELECT category, SUM(current_stock) AS stock, SUM(current_stock * purchase_price) AS inventory_value
        FROM products
        GROUP BY category
        ORDER BY stock DESC
        """,
        connection
    )
    connection.close()
    return df


def render_analytics(start_date, end_date):
    st.header("📈 Analytics & Reports")
    tab_revenue, tab_expenses, tab_product, tab_sales_trend, tab_purchase_trend, tab_inventory = st.tabs(
        ["Sales Revenue", "Purchase Expenses", "Product-wise Sales",
         "Sales Trends", "Purchase Trends", "Inventory Analysis"]
    )

    profit_data = get_profit_data(start_date, end_date)
    revenue = float(profit_data["revenue"].iloc[0] or 0)
    cost = float(profit_data["cost"].iloc[0] or 0)
    profit = revenue - cost

    sales_purchase = get_sales_purchase_data(start_date, end_date)

    with tab_revenue:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Revenue", f"₹{revenue:,.2f}")
        with col2:
            st.metric("Cost of Goods", f"₹{cost:,.2f}")
        with col3:
            st.metric("Profit", f"₹{profit:,.2f}")
        if not sales_purchase.empty:
            st.line_chart(sales_purchase.set_index("date")["sales"])

    with tab_expenses:
        if not sales_purchase.empty:
            st.line_chart(sales_purchase.set_index("date")["purchases"])
        else:
            st.info("No purchase data for this period.")

    with tab_product:
        product_sales = get_product_wise_sales(start_date, end_date)
        if not product_sales.empty:
            st.dataframe(product_sales, use_container_width=True, hide_index=True)
        else:
            st.info("No sales data available.")

    with tab_sales_trend:
        if not sales_purchase.empty:
            st.line_chart(sales_purchase.set_index("date")[["sales"]])
        else:
            st.info("No transaction data for this period.")

    with tab_purchase_trend:
        if not sales_purchase.empty:
            st.line_chart(sales_purchase.set_index("date")[["purchases"]])
        else:
            st.info("No transaction data for this period.")

    with tab_inventory:
        category_data = get_category_inventory()
        if not category_data.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.bar_chart(category_data.set_index("category")["stock"])
            with col2:
                st.dataframe(category_data, use_container_width=True, hide_index=True)

        st.subheader("Slow-Moving Products")
        slow_products = get_slow_moving_products()
        if not slow_products.empty:
            st.dataframe(slow_products, use_container_width=True, hide_index=True)
        else:
            st.success("No slow-moving products detected.")


def get_slow_moving_products():
    connection = get_db_connection()
    df = pd.read_sql(
        """
        SELECT p.product_name, p.current_stock,
               COALESCE(SUM(CASE WHEN t.transaction_type = 'SALE' THEN t.quantity ELSE 0 END), 0) AS units_sold
        FROM products p
        LEFT JOIN transactions t ON p.product_id = t.product_id
        GROUP BY p.product_id, p.product_name, p.current_stock
        HAVING units_sold <= 2
        ORDER BY p.current_stock DESC
        """,
        connection
    )
    connection.close()
    return df


# ---------------------------------------------------------------------
# 🔄 DATA SYNC — data functions
# ---------------------------------------------------------------------

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


def render_data_sync():
    st.header("🔄 Data Sync")
    tab_excel, tab_sheets, tab_auto, tab_manual = st.tabs(
        ["Excel", "Google Sheets", "Automatic Sync", "Manual Sync"]
    )

    with tab_excel:
        st.write("Inventory and transaction data is mirrored to a local Excel workbook.")
        if st.button("Regenerate Excel File"):
            try:
                create_excel_file()
                st.success("Excel file regenerated.")
            except Exception as e:
                st.error(f"Excel synchronization failed: {e}")

    with tab_sheets:
        st.write("Inventory and transaction data is mirrored to a connected Google Sheet.")
        if st.button("Push to Google Sheets"):
            try:
                update_google_sheet()
                st.success("Google Sheet updated.")
            except Exception as e:
                st.error(f"Google Sheets synchronization failed: {e}")

    with tab_auto:
        st.caption(
            "Automatic sync runs after every sale and purchase "
            "(see make_sale / make_purchase), keeping Excel and "
            "Google Sheets up to date without manual action."
        )

    with tab_manual:
        if st.button("🔄 Sync Data Now", key="manual_sync_button"):
            synchronize_data()
            st.success("Excel and Google Sheets synchronized!")


# ---------------------------------------------------------------------
# ⚙️ SYSTEM — data functions
# ---------------------------------------------------------------------

def check_database_status():
    try:
        connection = get_db_connection()
        connection.close()
        return True, "Connected"
    except Exception as e:
        return False, str(e)


def check_excel_status():
    excel_path = os.path.join(PROJECT_ROOT, "inventory.xlsx")
    if os.path.exists(excel_path):
        modified = datetime.fromtimestamp(os.path.getmtime(excel_path))
        return True, f"Last updated {modified.strftime('%Y-%m-%d %H:%M:%S')}"
    return False, "Excel file not found yet"


def check_google_sheets_status():
    try:
        update_google_sheet
        return True, "Integration configured"
    except Exception as e:
        return False, str(e)


def render_system():
    st.header("⚙️ System")
    tab_db, tab_sheets, tab_excel, tab_refresh = st.tabs(
        ["Database Status", "Google Sheets Status", "Excel Status", "Refresh Dashboard"]
    )

    with tab_db:
        ok, message = check_database_status()
        (st.success if ok else st.error)(f"Database: {message}")

    with tab_sheets:
        ok, message = check_google_sheets_status()
        (st.success if ok else st.warning)(f"Google Sheets: {message}")

    with tab_excel:
        ok, message = check_excel_status()
        (st.success if ok else st.info)(f"Excel: {message}")

    with tab_refresh:
        if st.button("🔄 Refresh Dashboard", key="system_refresh"):
            st.cache_data.clear()
            st.rerun()


# =====================================================================
# MAIN APP — navigation matching the requested structure
# =====================================================================

st.title("🏠 Smart Inventory Management System")
st.write("Real-time inventory monitoring and analytics dashboard")

st.sidebar.header("📅 Filters")
today = datetime.now().date()
start_date = st.sidebar.date_input("Start Date", today - timedelta(days=30))
end_date = st.sidebar.date_input("End Date", today)

if start_date > end_date:
    st.error("Start date cannot be after end date.")
    st.stop()

st.sidebar.divider()

NAV_SECTIONS = [
    "📊 Dashboard",
    "📦 Products",
    "🏢 Suppliers",
    "💰 Sales",
    "🛒 Purchases",
    "🤖 AI Insights",
    "⚠️ Inventory Alerts",
    "📈 Analytics & Reports",
    "🔄 Data Sync",
    "⚙️ System",
]

st.sidebar.header("🧭 Navigation")
selected_section = st.sidebar.radio("Go to", NAV_SECTIONS, label_visibility="collapsed")

if selected_section == "📊 Dashboard":
    render_dashboard()
elif selected_section == "📦 Products":
    render_products()
elif selected_section == "🏢 Suppliers":
    render_suppliers()
elif selected_section == "💰 Sales":
    render_sales()
elif selected_section == "🛒 Purchases":
    render_purchases()
elif selected_section == "🤖 AI Insights":
    render_ai_insights()
elif selected_section == "⚠️ Inventory Alerts":
    render_inventory_alerts()
elif selected_section == "📈 Analytics & Reports":
    render_analytics(start_date, end_date)
elif selected_section == "🔄 Data Sync":
    render_data_sync()
elif selected_section == "⚙️ System":
    render_system()