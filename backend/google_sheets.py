import os
import gspread
import pandas as pd

from google.oauth2.service_account import Credentials

from database import get_db_connection


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CREDENTIALS_FILE = os.path.join(
    BASE_DIR,
    "credentials 2.json"
)

SPREADSHEET_NAME = "Smart Inventory Dashboard"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


# --------------------------------------------------
# CONNECT TO GOOGLE SHEETS
# --------------------------------------------------

def connect_google_sheet():

    credentials = Credentials.from_service_account_file(
        CREDENTIALS_FILE,
        scopes=SCOPES
    )

    client = gspread.authorize(credentials)

    spreadsheet = client.open(SPREADSHEET_NAME)

    return spreadsheet


# --------------------------------------------------
# CONVERT DATAFRAME TO GOOGLE SHEETS FORMAT
# --------------------------------------------------

def dataframe_to_google_values(df):

    # Convert datetime / Timestamp columns
    # into normal strings
    for column in df.columns:

        if pd.api.types.is_datetime64_any_dtype(df[column]):

            df[column] = df[column].dt.strftime(
                "%Y-%m-%d %H:%M:%S"
            )

    # Replace NaN and NaT
    df = df.fillna("")

    # Convert everything to normal Python values
    return [
        df.columns.tolist()
    ] + df.values.tolist()


# --------------------------------------------------
# PRODUCTS
# --------------------------------------------------

def get_products():

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


def update_products_sheet():

    spreadsheet = connect_google_sheet()

    worksheet = spreadsheet.worksheet("Products")

    df = get_products()

    worksheet.clear()

    worksheet.update(
        dataframe_to_google_values(df)
    )

    print("Products sheet updated!")


# --------------------------------------------------
# TRANSACTIONS
# --------------------------------------------------

def get_transactions():

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


def update_transactions_sheet():

    spreadsheet = connect_google_sheet()

    worksheet = spreadsheet.worksheet("Transactions")

    df = get_transactions()

    worksheet.clear()

    worksheet.update(
        dataframe_to_google_values(df)
    )

    print("Transactions sheet updated!")


# --------------------------------------------------
# SUPPLIERS
# --------------------------------------------------

def get_suppliers():

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


def update_suppliers_sheet():

    spreadsheet = connect_google_sheet()

    worksheet = spreadsheet.worksheet("Suppliers")

    df = get_suppliers()

    worksheet.clear()

    worksheet.update(
        dataframe_to_google_values(df)
    )

    print("Suppliers sheet updated!")


# --------------------------------------------------
# LOW STOCK
# --------------------------------------------------

def get_low_stock():

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


def update_low_stock_sheet():

    spreadsheet = connect_google_sheet()

    worksheet = spreadsheet.worksheet("Low Stock")

    df = get_low_stock()

    worksheet.clear()

    worksheet.update(
        dataframe_to_google_values(df)
    )

    print("Low Stock sheet updated!")


# --------------------------------------------------
# UPDATE ALL GOOGLE SHEETS
# --------------------------------------------------

def update_google_sheet():

    print("\nUpdating Google Sheets...\n")

    update_products_sheet()

    update_transactions_sheet()

    update_suppliers_sheet()

    update_low_stock_sheet()

    print("\nGoogle Sheets updated successfully!")


# --------------------------------------------------
# RUN PROGRAM
# --------------------------------------------------

if __name__ == "__main__":

    update_google_sheet()