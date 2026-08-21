import mysql.connector


def get_db_connection():

    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="WEFG@2468",
        database="smart_inventory"
    )

    return connection