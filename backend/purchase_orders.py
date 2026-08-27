from database import get_db_connection


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