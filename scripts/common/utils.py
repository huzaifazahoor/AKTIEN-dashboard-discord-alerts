import logging
import os
import time
from io import BytesIO

import pandas as pd
import psycopg2
import requests
from dotenv import load_dotenv
from psycopg2 import OperationalError, extras

# Set up logging
load_dotenv()

logging.basicConfig(level=logging.INFO)


def fetch_api_data(url):
    """Fetch data from API."""
    try:
        logging.info(url)
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logging.error(f"API Call Error: '{e}'")
    return None


class DBConnection:
    def __enter__(self):
        try:
            self.connection = psycopg2.connect(
                dbname=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PWD"),
                host=os.getenv("DB_HOST"),
                port="5432",
            )
            return self.connection
        except OperationalError as e:
            print(e)
            logging.error(f"The error '{e}' occurred")
            return None

    def __exit__(self, exc_type, exc_value, traceback):
        if self.connection:
            self.connection.close()


def execute_select_query(cursor, query, values=None):
    """
    Execute a SELECT query using the given cursor, query, and optional values.
    Parameters:
        cursor (psycopg2.cursor): The database cursor.
        query (str): SQL query string.
        values (list, optional): Parameters to substitute into the query.
    Returns:
        list: The fetched rows as a list of tuples.
    """
    if isinstance(values, list):
        values = tuple(values)

    cursor.execute(query, values)
    return cursor.fetchall()


def execute_non_select_query(connection, cursor, query, values=None, batch=False):
    """
    Execute a non-SELECT SQL query on the database.
    Parameters:
        connection (psycopg2.connection): The database connection.
        cursor (psycopg2.cursor): The database cursor.
        query (str): SQL query string.
        values (list, optional): Parameters to substitute into the query.
        batch (bool): True if executemany should be used for batch processing.
    """
    if batch and isinstance(values, list):
        # For batch processing, use executemany
        cursor.executemany(query, values)
    else:
        # For individual execution, ensure values are in the correct format
        if isinstance(values, list):
            values = tuple(values)
        cursor.execute(query, values)
    connection.commit()


def get_stock_symbols(
    cursor=None,
    query="SELECT symbol FROM stock_data_stock ORDER BY symbol;",
    only_symbols=False,
):
    """
    Fetch stock symbols from the database using the provided cursor and query.
    Parameters:
        cursor (psycopg2.cursor, optional): The database cursor. If None, a new connection is created.
        query (str): SQL query to fetch stock symbols.
        only_symbols (bool): If True, return only symbols; otherwise, return complete fetched data.
    Returns:
        list: A list of symbols or full query results.
    """
    if cursor is None:
        connection = DBConnection()
        cursor = connection.cursor()

    symbol_data = execute_select_query(cursor, query)

    if cursor is None:
        connection.close()
        cursor.close()

    if symbol_data is not None:
        if only_symbols:
            # Extracting the 'symbol' from each tuple in the list
            symbols = [item[0] for item in symbol_data]
            return symbols
        else:
            return symbol_data
    else:
        logging.error("No data found or there was an error fetching the data.")
        return []


def chunk_list(data_list, chunk_size):
    """Yield successive chunk_size-sized chunks from data_list."""
    for i in range(0, len(data_list), chunk_size):
        yield data_list[i : i + chunk_size]  # noqa


def execute_bulk_insert(connection, cursor, query, values, page_size=1000):
    """
    Execute a bulk insert operation using psycopg2's execute_values method.

    :param connection: The database connection object.
    :param cursor: The database cursor object.
    :param query: The SQL insert query string.
    :param values: A list of tuples containing the data to be inserted.
    :param page_size: The number of records to insert in each batch (default 1000).
    """
    # Execute the query using execute_values
    extras.execute_values(cursor, query, values, page_size=page_size)

    # Commit the changes
    connection.commit()


def execute_direct_query(connection, cursor, query):
    """
    Execute a direct SQL query on the database without expecting any return.
    Parameters:
        connection (psycopg2.connection): The database connection.
        cursor (psycopg2.cursor): The database cursor.
        query (str): SQL query string.
    """
    cursor.execute(query)
    connection.commit()


class MockRequest:
    def __init__(self, json_body=None, args=None):
        self._json = json_body or {"hello": "world"}
        self.args = args or {"hello": "world"}

    def get_json(self, silent=False):
        return self._json


def add_delay():
    time.sleep(2)


def convert_to_float(value):
    """
    Convert a value to float if it is not None or a string.
    Returns:
        float: The converted float value if conversion is possible.
        None: If the input value is None or a string.
    """
    if value is not None and not pd.isna(value):
        try:
            return float(value)
        except (ValueError, TypeError):
            # Handle the case where the conversion is not possible
            return None
    return None


def fetch_csv_as_dataframe(url, params):
    try:
        # Build full URL with params for logging
        param_string = "&".join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{param_string}"
        print(f"Fetching data from: {full_url}")

        # Fetch the data from the URL
        response = requests.get(url, params=params)
        response.raise_for_status()  # Ensure we got a valid response

        # Load the data into a DataFrame
        df = pd.read_csv(BytesIO(response.content))

        return df
    except requests.exceptions.RequestException:
        return pd.DataFrame([])
