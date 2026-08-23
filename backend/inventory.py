from database import get_db_connection


def get_inventory():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            p.product_id,
            p.product_name,
            p.category,
            s.supplier_name,
            p.current_stock,
            p.minimum_stock,
            p.purchase_price,
            p.selling_price,
            p.location,

            CASE
                WHEN p.current_stock = 0
                    THEN 'OUT_OF_STOCK'

                WHEN p.current_stock <= p.minimum_stock
                    THEN 'LOW_STOCK'

                ELSE 'IN_STOCK'
            END AS stock_status

        FROM products p

        LEFT JOIN suppliers s
            ON p.supplier_id = s.supplier_id

        ORDER BY p.product_name
    """

    cursor.execute(query)

    inventory = cursor.fetchall()

    cursor.close()
    connection.close()

    return inventory

def get_low_stock_products():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

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

    cursor.execute(query)

    products = cursor.fetchall()

    cursor.close()
    connection.close()

    return products

def get_out_of_stock_products():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

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

        WHERE p.current_stock = 0

        ORDER BY p.product_name
    """

    cursor.execute(query)

    products = cursor.fetchall()

    cursor.close()
    connection.close()

    return products

def get_reorder_list():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            p.product_id,
            p.product_name,
            p.category,
            s.supplier_name,
            p.current_stock,
            p.minimum_stock,

            (p.minimum_stock * 3) AS recommended_stock,

            ((p.minimum_stock * 3) - p.current_stock)
            AS recommended_order_quantity

        FROM products p

        LEFT JOIN suppliers s
            ON p.supplier_id = s.supplier_id

        WHERE p.current_stock <= p.minimum_stock

        ORDER BY recommended_order_quantity DESC
    """

    cursor.execute(query)

    products = cursor.fetchall()

    cursor.close()
    connection.close()

    return products