from database import get_db_connection
from excel_sync import create_excel_file
from google_sheets import update_google_sheet

def create_purchase_order(
    supplier_id,
    product_id,
    quantity,
    unit_price
):

    connection = get_db_connection()
    cursor = connection.cursor()

    total_price = quantity * unit_price

    # Create purchase order
    cursor.execute(
        """
        INSERT INTO purchase_orders
        (supplier_id, total_amount)
        VALUES (%s, %s)
        """,
        (supplier_id, total_price)
    )

    purchase_order_id = cursor.lastrowid

    # Add product to order
    cursor.execute(
        """
        INSERT INTO purchase_order_items
        (
            purchase_order_id,
            product_id,
            quantity,
            unit_price,
            total_price
        )
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            purchase_order_id,
            product_id,
            quantity,
            unit_price,
            total_price
        )
    )

    connection.commit()

    cursor.close()
    connection.close()

    return purchase_order_id

def receive_purchase_order(purchase_order_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Check purchase order
    cursor.execute(
        """
        SELECT *
        FROM purchase_orders
        WHERE purchase_order_id = %s
        """,
        (purchase_order_id,)
    )

    order = cursor.fetchone()

    if not order:
        cursor.close()
        connection.close()
        return False, "Purchase order not found."

    if order["status"] == "RECEIVED":
        cursor.close()
        connection.close()
        return False, "Purchase order already received."

    # Get ordered products
    cursor.execute(
        """
        SELECT
            product_id,
            quantity,
            unit_price,
            total_price
        FROM purchase_order_items
        WHERE purchase_order_id = %s
        """,
        (purchase_order_id,)
    )

    items = cursor.fetchall()

    if not items:
        cursor.close()
        connection.close()
        return False, "No products found in this purchase order."

    for item in items:

        product_id = item["product_id"]
        quantity = item["quantity"]
        unit_price = item["unit_price"]
        total_price = item["total_price"]

        # Increase stock
        cursor.execute(
            """
            UPDATE products
            SET current_stock = current_stock + %s
            WHERE product_id = %s
            """,
            (quantity, product_id)
        )

        # Record transaction
        cursor.execute(
            """
            INSERT INTO transactions
            (
                product_id,
                transaction_type,
                quantity,
                price,
                total_amount
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                product_id,
                "PURCHASE",
                quantity,
                unit_price,
                total_price
            )
        )

    # Mark order as received
    cursor.execute(
        """
        UPDATE purchase_orders
        SET status = 'RECEIVED'
        WHERE purchase_order_id = %s
        """,
        (purchase_order_id,)
    )


    connection.commit()

    cursor.close()
    connection.close()

    try:
        create_excel_file()
    except Exception as e:
        print("Excel sync failed:", e)

    try:
        update_google_sheet()
    except Exception as e:
        print("Google Sheets sync failed:", e)

    return True, "Purchase order received successfully."
