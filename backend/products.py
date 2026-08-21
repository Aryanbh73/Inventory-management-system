from database import get_db_connection


def add_product(
    product_name,
    category,
    purchase_price,
    selling_price,
    current_stock,
    minimum_stock,
    location
):

    connection = get_db_connection()

    cursor = connection.cursor()

    query = """
        INSERT INTO products
        (
            product_name,
            category,
            purchase_price,
            selling_price,
            current_stock,
            minimum_stock,
            location
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    values = (
        product_name,
        category,
        purchase_price,
        selling_price,
        current_stock,
        minimum_stock,
        location
    )

    cursor.execute(query, values)

    connection.commit()

    cursor.close()
    connection.close()