from database import get_db_connection


def add_purchase(product_id, supplier_id, quantity, price):

    connection = get_db_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            "SELECT product_id FROM products WHERE product_id = %s",
            (product_id,)
        )

        product = cursor.fetchone()

        if not product:
            return {
                "success": False,
                "message": "Product not found"
            }

        cursor.execute(
            "SELECT supplier_id FROM suppliers WHERE supplier_id = %s",
            (supplier_id,)
        )

        supplier = cursor.fetchone()

        if not supplier:
            return {
                "success": False,
                "message": "Supplier not found"
            }

        cursor.execute(
            """
            UPDATE products
            SET current_stock = current_stock + %s
            WHERE product_id = %s
            """,
            (quantity, product_id)
        )

        total_amount = quantity * price

        cursor.execute(
            """
            INSERT INTO transactions
            (
                product_id,
                supplier_id,
                transaction_type,
                quantity,
                price,
                total_amount
            )
            VALUES (%s, %s, 'PURCHASE', %s, %s, %s)
            """,
            (
                product_id,
                supplier_id,
                quantity,
                price,
                total_amount
            )
        )

        connection.commit()

        cursor.execute(
            """
            SELECT current_stock
            FROM products
            WHERE product_id = %s
            """,
            (product_id,)
        )

        updated_stock = cursor.fetchone()[0]

        return {
            "success": True,
            "message": "Purchase added successfully",
            "updated_stock": updated_stock,
            "total_amount": total_amount
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

def get_purchase_history():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            t.transaction_id,
            p.product_name,
            s.supplier_name,
            t.quantity,
            t.price,
            t.total_amount,
            t.transaction_date
        FROM transactions t

        JOIN products p
            ON t.product_id = p.product_id

        LEFT JOIN suppliers s
            ON t.supplier_id = s.supplier_id

        WHERE t.transaction_type = 'PURCHASE'

        ORDER BY t.transaction_date DESC
    """

    cursor.execute(query)

    purchases = cursor.fetchall()

    cursor.close()
    connection.close()

    return purchases