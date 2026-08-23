from database import get_db_connection


def add_sale(product_id, quantity, price):

    connection = get_db_connection()
    cursor = connection.cursor()

    try:

        # Get current stock and minimum stock
        cursor.execute(
            """
            SELECT current_stock, minimum_stock
            FROM products
            WHERE product_id = %s
            """,
            (product_id,)
        )

        product = cursor.fetchone()

        # Product does not exist
        if not product:
            return {
                "success": False,
                "message": "Product not found"
            }

        current_stock = product[0]
        minimum_stock = product[1]

        # Check available stock
        if quantity > current_stock:
            return {
                "success": False,
                "message": f"Insufficient stock. Available stock: {current_stock}"
            }

        # Reduce stock
        cursor.execute(
            """
            UPDATE products
            SET current_stock = current_stock - %s
            WHERE product_id = %s
            """,
            (quantity, product_id)
        )

        # Calculate sale amount
        total_amount = quantity * price

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
            VALUES (%s, 'SALE', %s, %s, %s)
            """,
            (
                product_id,
                quantity,
                price,
                total_amount
            )
        )

        connection.commit()

        # Get updated stock
        cursor.execute(
            """
            SELECT current_stock
            FROM products
            WHERE product_id = %s
            """,
            (product_id,)
        )

        updated_stock = cursor.fetchone()[0]

        # Check low-stock condition
        low_stock = updated_stock <= minimum_stock

        return {
            "success": True,
            "message": "Sale recorded successfully",
            "quantity_sold": quantity,
            "total_amount": total_amount,
            "updated_stock": updated_stock,
            "low_stock": low_stock
        }

    except Exception as e:

        connection.rollback()

        return {
            "success": False,
            "message": str(e)
        }

    finally:

        cursor.close()
        connection.close()

def get_sales_history():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            t.transaction_id,
            p.product_name,
            t.quantity,
            t.price,
            t.total_amount,
            t.transaction_date
        FROM transactions t

        JOIN products p
            ON t.product_id = p.product_id

        WHERE t.transaction_type = 'SALE'

        ORDER BY t.transaction_date DESC
    """

    cursor.execute(query)

    sales = cursor.fetchall()

    cursor.close()
    connection.close()

    return sales