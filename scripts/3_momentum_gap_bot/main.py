import json
import os
import time
from datetime import datetime
from random import uniform

import pandas as pd
import requests
from common.extra_utils import (
    bulk_upsert_alerts,
    bulk_upsert_stock_info,
    bulk_upsert_stocks,
)
from common.utils import DBConnection, build_and_print_url, fetch_csv_as_dataframe


class MomentumGapScanner:
    def __init__(self):
        self.DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1319301200780460133/2_m1P0R-V7vV__MUZWp9WfuQXgcXQKGeruKmgvte9aS0OY8wZU4X-PB85J4a8FytoZp5"
        self.FINVIZ_EMAIL = os.getenv("FINVIZ_EMAIL")

    def download_finviz_data(self):
        """Download data from Finviz with specific parameters for momentum gap up stocks"""
        url = "https://elite.finviz.com/export.ashx"
        params = {
            "v": "152",
            "f": "sh_price_u30,sh_relvol_o5,ta_perf_d15o,ta_rsi_ob70",
            "ft": "4",
            "c": ",".join([str(num) for num in range(1, 201)]),
            "auth": f"{self.FINVIZ_EMAIL}",
        }
        build_and_print_url(url, params)
        return fetch_csv_as_dataframe(url, params)

    def process_data(self, df):
        """Process and filter the data based on momentum/gap requirements"""
        # Convert numeric columns to appropriate types
        numeric_columns = [
            "Price",
            "Change",
        ]

        # Convert numeric columns
        for col in numeric_columns:
            # First convert column to string type
            df[col] = df[col].astype(str)
            # Then replace % and convert to numeric
            df[col] = pd.to_numeric(
                df[col].str.replace("%", ""),
                errors="coerce",
            )

        # Convert NaN values to "N/A" across the entire DataFrame
        df = df.fillna("N/A")

        # Prepare lists for bulk operations
        stocks_to_upsert = []
        stocks_info_to_upsert = []
        alerts_to_upsert = []
        processed_stocks = []

        for _, stock in df.iterrows():
            # Prepare stock data for database
            stocks_to_upsert.append(
                (
                    stock["Ticker"],
                    stock["Company"],
                    stock["Exchange"],
                    stock["Sector"],
                    stock["Industry"],
                    "NOW()",
                    "NOW()",
                )
            )

            # Prepare stock info data
            stocks_info_to_upsert.append(
                (
                    stock["Ticker"],
                    stock["Market Cap"],
                    stock["Average Volume"],
                    stock["Price"],
                    stock["Volume"],
                    "NOW()",
                )
            )

            # Prepare alert data
            alert_data = {
                "price": stock["Price"],
                "change": stock["Change"],
                "volume": stock["Volume"],
                "rel_volume": stock["Relative Volume"],
                # "rsi": stock["RSI"],
                "gap": stock["Change"],
                "market_cap": stock["Market Cap"],
            }

            alerts_to_upsert.append(
                (
                    stock["Ticker"],
                    "Momentum Gap Alert",
                    "NOW()",
                    json.dumps(alert_data),
                    "NOW()",
                    "NOW()",
                )
            )

            # Prepare data for Discord alert
            processed_stocks.append(
                {
                    "ticker": stock["Ticker"],
                    "company": stock["Company"],
                    "price": stock["Price"],
                    "change": stock["Change"],
                    "volume": stock["Volume"],
                    "rel_volume": stock["Relative Volume"],
                    # "rsi": stock["RSI"],
                    "market_cap": stock["Market Cap"],
                    "sector": stock["Sector"],
                    "industry": stock["Industry"],
                    "avg_volume": stock["Average Volume"],
                }
            )

        # Perform bulk database operations
        with DBConnection() as connection:
            with connection.cursor() as cursor:
                bulk_upsert_stocks(connection, cursor, stocks_to_upsert)
                bulk_upsert_stock_info(connection, cursor, stocks_info_to_upsert)
                bulk_upsert_alerts(connection, cursor, alerts_to_upsert)

        return processed_stocks

    def create_discord_alert(self, stocks):
        """Send formatted alerts to Discord"""
        headers = {"Content-Type": "application/json"}

        for stock in stocks:
            # Determine color based on gap percentage
            color = int("ff0000" if stock["change"] >= 20 else "ffa500", 16)

            embed = {
                "title": f"🚀 Momentum Gap Alert | {stock['ticker']}",
                "description": (
                    f"**{stock['company']}** → ${stock['price']}\n\n"
                    "**📊 Gap Metrics:**\n"
                    f"• Gap Up: +{stock['change']}% 📈\n"
                    # f"• RSI(14): {stock['rsi']:.1f} 🔥\n"
                    f"• Relative Volume: {stock['rel_volume']:.1f}x 📊\n"
                    f"• Current Volume: {stock['volume']:,.0f} 📈\n\n"
                    "**💡 Trading Info:**\n"
                    f"• Market Cap: ${stock['market_cap']}M\n"
                    f"• Sector: {stock['sector']}\n"
                    f"• Industry: {stock['industry']}\n\n"
                    "⚠️ *High volatility stock with significant gap up. Trade with caution!*"
                ),
                "color": color,
                "image": {
                    "url": f"https://elite.finviz.com/chart.ashx?t={stock['ticker']}&ty=c&ta=1&p=d"
                },
                "footer": {
                    "text": f"Gap Scanner Alert • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                },
            }

            payload = {"embeds": [embed]}
            response = requests.post(
                self.DISCORD_WEBHOOK, json=payload, headers=headers
            )

            if response.status_code != 204:
                print(f"Failed to send alert for {stock['ticker']}: {response.text}")

            time.sleep(uniform(0.5, 1.0))

    def run_scanner(self):
        """Main method to run the scanner"""
        df = self.download_finviz_data()
        if df is None or df.empty:
            print("No data retrieved from Finviz")
            return

        stocks = self.process_data(df)
        if stocks:
            self.create_discord_alert(stocks)
            print(f"Successfully processed {len(stocks)} stocks")
        else:
            print("No stocks matched the momentum gap criteria")


def main(request):
    scanner = MomentumGapScanner()
    scanner.run_scanner()
    return "Momentum scanner completed successfully", 200


if __name__ == "__main__":
    main("")
