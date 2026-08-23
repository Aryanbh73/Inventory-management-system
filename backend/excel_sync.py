import os
import pandas as pd
from database import get_db_connection

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCEL_FILE = os.path.join(BASE_DIR, "inventory_data.xlsx")


def export_products():

    connection = get_db_connection()

    query = """
        SELECT
            p.product_id,
            p.product_name,
            p.category,
            s.supplier_name,
            p.purchase_price,
            p.selling_price,
            p.current_stock,
            p.minimum_stock,
            p.location
        FROM products p
        LEFT JOIN suppliers s
            ON p.supplier_id = s.supplier_id
        ORDER BY p.product_id
    """

    df = pd.read_sql(query, connection)

    connection.close()

    return df


def export_transactions():

    connection = get_db_connection()

    query = """
        SELECT
            t.transaction_id,
            p.product_name,
            t.transaction_type,
            t.quantity,
            t.price,
            t.total_amount,
            t.transaction_date
        FROM transactions t
        JOIN products p
            ON t.product_id = p.product_id
        ORDER BY t.transaction_date DESC
    """

    df = pd.read_sql(query, connection)

    connection.close()

    return df


def export_suppliers():

    connection = get_db_connection()

    query = """
        SELECT
            supplier_id,
            supplier_name,
            phone,
            email,
            address
        FROM suppliers
        ORDER BY supplier_id
    """

    df = pd.read_sql(query, connection)

    connection.close()

    return df


def export_low_stock():

    connection = get_db_connection()

    query = """
        SELECT
            p.product_id,
            p.product_name,
            p.category,
            s.supplier_name,
            p.current_stock,
            p.minimum_stock,
            p.purchase_price,
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


def create_excel_file():

    print("Starting Excel update...")

    products = export_products()
    transactions = export_transactions()
    suppliers = export_suppliers()
    low_stock = export_low_stock()

    print("Products:", len(products))
    print("Transactions:", len(transactions))
    print("Suppliers:", len(suppliers))
    print("Low Stock:", len(low_stock))

    with pd.ExcelWriter(
        EXCEL_FILE,
        engine="openpyxl"
    ) as writer:

        products.to_excel(
            writer,
            sheet_name="Products",
            index=False
        )

        transactions.to_excel(
            writer,
            sheet_name="Transactions",
            index=False
        )

        suppliers.to_excel(
            writer,
            sheet_name="Suppliers",
            index=False
        )

        low_stock.to_excel(
            writer,
            sheet_name="Low Stock",
            index=False
        )

    print("Excel file updated successfully!")
    print("File location:", EXCEL_FILE)


if __name__ == "__main__":
    create_excel_file()