import os
import time
from datetime import datetime
from random import uniform

import pandas as pd
import requests
from common.extra_utils import (bulk_upsert_alerts, bulk_upsert_stock_info,
                                bulk_upsert_stocks)
from common.utils import (DBConnection, build_and_print_url,
                          fetch_csv_as_dataframe)


class BaseScanner:
    def __init__(self, discord_webhook):
        self.BASE_URL = "https://discord.com/api/webhooks/"
        self.NEXT_URL = discord_webhook
        self.DISCORD_WEBHOOK = self.BASE_URL + self.NEXT_URL
        self.FINVIZ_EMAIL = os.getenv("FINVIZ_EMAIL")
        self.DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

    def download_finviz_data(self, filter_params):
        """Download data from Finviz with given filter parameters"""
        url = "https://elite.finviz.com/export.ashx"
        params = {
            "v": "152",
            "f": filter_params,
            "ft": "4",
            "c": ",".join([str(num) for num in range(1, 201)]),
            "auth": f"{self.FINVIZ_EMAIL}",
        }
        df = fetch_csv_as_dataframe(url, params)
        build_and_print_url(url, params)
        print(f"Downloaded {len(df)} stocks from Finviz")
        return df

    def process_columns(self, df):
        """
        Process DataFrame columns with the following transformations:
        - Convert percentage strings to floats (as decimals).
        - Remove commas from large numbers and convert to numeric.
        - Handle financial metrics like Market Cap and Sales.
        - Preserve non-numeric and categorical columns.
        """
        for col in df.columns:
            if df[col].dtype == object:  # Only process object-type columns
                # Check for percentage values and convert to decimals
                if df[col].str.contains("%", na=False).any():
                    df[col] = (
                        df[col]
                        .str.replace("%", "", regex=True)
                        .str.replace(",", "", regex=True)
                        .astype(float)
                        / 100  # Convert percentages to decimals
                    )
                # Check for large numbers with commas
                elif df[col].str.replace(",", "", regex=True).str.isnumeric().any():
                    df[col] = pd.to_numeric(
                        df[col].str.replace(",", "", regex=True), errors="coerce"
                    )
                # Handle Market Cap (e.g., "B" for billions, "M" for millions)
                elif df[col].str.contains(r"[BM]$", na=False).any():
                    df[col] = (
                        df[col]
                        .str.replace("B", "e9", regex=True)
                        .str.replace("M", "e6", regex=True)
                        .str.replace(",", "", regex=True)
                        .astype(float)
                    )
            elif pd.api.types.is_numeric_dtype(df[col]):
                # Ensure numeric columns are clean
                df[col] = pd.to_numeric(df[col], errors="coerce")
            # Non-numeric columns remain unchanged

        # Fill missing values with a default
        return df.fillna("N/A")

    def prepare_base_data(self, stock):
        """Prepare common stock data for database operations"""
        stocks_to_upsert = (
            stock["Ticker"],
            stock["Company"],
            stock["Exchange"],
            stock["Sector"],
            stock["Industry"],
            "NOW()",
            "NOW()",
        )

        stocks_info_to_upsert = (
            stock["Ticker"],
            stock["Market Cap"],
            stock["Average Volume"],
            stock["Price"],
            stock["Volume"],
            "NOW()",
        )

        return stocks_to_upsert, stocks_info_to_upsert

    def process_data(self, df):
        """Template method for data processing
        Override get_alert_data and get_processed_stock in child classes"""
        df = self.process_columns(df)

        stocks_to_upsert = []
        stocks_info_to_upsert = []
        alerts_to_upsert = []
        processed_stocks = []

        for _, stock in df.iterrows():
            base_stock, base_info = self.prepare_base_data(stock)
            stocks_to_upsert.append(base_stock)
            stocks_info_to_upsert.append(base_info)

            alert_data = self.get_alert_data(stock)
            alerts_to_upsert.append(
                (
                    stock["Ticker"],
                    self.get_alert_type(),
                    "NOW()",
                    alert_data,
                    "NOW()",
                    "NOW()",
                )
            )

            processed_stock = self.get_processed_stock(stock)
            processed_stocks.append(processed_stock)

        self.bulk_db_operations(
            stocks_to_upsert, stocks_info_to_upsert, alerts_to_upsert
        )

        return processed_stocks

    def bulk_db_operations(self, stocks, stock_info, alerts):
        """Execute bulk database operations"""
        with DBConnection() as connection:
            with connection.cursor() as cursor:
                bulk_upsert_stocks(connection, cursor, stocks)
                bulk_upsert_stock_info(connection, cursor, stock_info)
                bulk_upsert_alerts(connection, cursor, alerts)

    def create_discord_alert(self, stocks):
        """Override this method in child classes"""
        raise NotImplementedError

    def get_alert_data(self, stock):
        """Override this method in child classes"""
        raise NotImplementedError

    def get_processed_stock(self, stock):
        return stock.to_dict()

    def get_alert_type(self):
        """Override this method in child classes"""
        raise NotImplementedError

    def send_discord_message(self, embed):
        """Common method to send Discord messages"""
        headers = {"Content-Type": "application/json"}
        payload = {"embeds": [embed]}

        response = requests.post(self.DISCORD_WEBHOOK, json=payload, headers=headers)

        if response.status_code != 204:
            print(f"Failed to send alert: {response.text}")

        time.sleep(uniform(0.5, 1.0))

    def run_scanner(self):
        """Main method to run the scanner"""
        df = self.download_finviz_data(self.get_filter_params())
        if df is None or df.empty:
            print("No data retrieved from Finviz")
            return

        stocks = self.process_data(df)
        if stocks:
            self.create_discord_alert(stocks)
            print(f"Successfully processed {len(stocks)} stocks")
        else:
            print("No stocks matched the criteria")
