import sys
import os

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

BACKEND_PATH = os.path.join(
    PROJECT_ROOT,
    "backend"
)

sys.path.insert(0, BACKEND_PATH)


import pandas as pd

from database import get_db_connection


def get_sales_history():

    connection = get_db_connection()

    query = """
        SELECT
            DATE(t.transaction_date) AS sale_date,
            t.product_id,
            p.product_name,
            t.quantity

        FROM transactions t

        JOIN products p
            ON t.product_id = p.product_id

        WHERE t.transaction_type = 'SALE'

        ORDER BY
            sale_date,
            t.product_id
    """

    df = pd.read_sql(
        query,
        connection
    )

    connection.close()

    return df


if __name__ == "__main__":

    df = get_sales_history()

    print(df)