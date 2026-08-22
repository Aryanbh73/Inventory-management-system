from database import get_db_connection


def add_supplier(name, phone, email, address):

    connection = get_db_connection()
    cursor = connection.cursor()

    query = """
        INSERT INTO suppliers
        (supplier_name, phone, email, address)
        VALUES (%s, %s, %s, %s)
    """

    values = (name, phone, email, address)

    cursor.execute(query, values)

    connection.commit()

    supplier_id = cursor.lastrowid

    cursor.close()
    connection.close()

    return supplier_id


def get_all_suppliers():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM suppliers
        ORDER BY supplier_id DESC
    """)

    suppliers = cursor.fetchall()

    cursor.close()
    connection.close()

    return suppliers

def get_supplier_products(supplier_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            p.product_id,
            p.product_name,
            p.category,
            p.current_stock,
            p.purchase_price,
            p.selling_price
        FROM products p
        WHERE p.supplier_id = %s
    """

    cursor.execute(query, (supplier_id,))

    products = cursor.fetchall()

    cursor.close()
    connection.close()

    return products