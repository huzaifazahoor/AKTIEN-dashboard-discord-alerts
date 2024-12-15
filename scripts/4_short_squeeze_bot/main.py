import json
import os
import time
from datetime import datetime
from random import uniform

import requests
from common.extra_utils import (
    bulk_upsert_alerts,
    bulk_upsert_stock_info,
    bulk_upsert_stocks,
)
from common.utils import DBConnection, fetch_csv_as_dataframe


class ShortSqueezeScanner:
    def __init__(self):
        self.DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
        self.FINVIZ_EMAIL = os.getenv("FINVIZ_EMAIL")

    def download_finviz_data(self):
        """Download data from Finviz with short squeeze parameters"""
        url = "https://elite.finviz.com/export.ashx"
        params = {
            "v": "152",
            "f": "sh_avgvol_o500,sh_relvol_o1,sh_short_o30,ta_highlow50d_b10h",  # Short squeeze parameters
            "ft": "4",
            "c": "1,2,3,4,5,6,7,8,9,10,11,12,13,14,65,66,67,68,70",  # Include short float and other relevant data
            "auth": f"{self.FINVIZ_EMAIL}",
        }
        return fetch_csv_as_dataframe(url, params)

    def process_data(self, df):
        """Process and filter the data based on short squeeze requirements"""
        # Apply filters
        df = df[
            (df["Short Float"] > 30)  # Heavy short float
            & (df["Average Volume"] > 500000)  # Good liquidity
            & (df["Relative Volume"] > 1)  # Recent high volume interest
            # 10% or more below 50-day high is handled in Finviz parameters
        ]

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
                "short_float": stock["Short Float"],
                "market_cap": stock["Market Cap"],
                "fifty_day_high": stock["50D High"],
                "fifty_day_low": stock["50D Low"],
            }

            alerts_to_upsert.append(
                (
                    stock["Ticker"],
                    "Short Squeeze Alert",
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
                    "short_float": stock["Short Float"],
                    "market_cap": stock["Market Cap"],
                    "sector": stock["Sector"],
                    "industry": stock["Industry"],
                    "avg_volume": stock["Average Volume"],
                    "fifty_day_high": stock["50D High"],
                    "fifty_day_low": stock["50D Low"],
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
            # Determine color based on short float percentage
            color = int("ff0000" if stock["short_float"] >= 40 else "ffa500", 16)

            # Calculate distance from 50-day high
            high_distance = (
                (stock["fifty_day_high"] - stock["price"]) / stock["fifty_day_high"]
            ) * 100

            embed = {
                "title": f"🎯 Short Squeeze Alert | {stock['ticker']}",
                "description": (
                    f"**{stock['company']}** → ${stock['price']}\n\n"
                    "**📊 Short Squeeze Metrics:**\n"
                    f"• Short Float: {stock['short_float']}% 🎯\n"
                    f"• Distance from 50D High: {high_distance:.1f}% 📏\n"
                    f"• Relative Volume: {stock['rel_volume']:.1f}x 📊\n"
                    f"• Current Volume: {stock['volume']:,.0f} 📈\n\n"
                    "**💡 Trading Info:**\n"
                    f"• Market Cap: ${stock['market_cap']}M\n"
                    f"• Sector: {stock['sector']}\n"
                    f"• Industry: {stock['industry']}\n"
                    f"• Average Volume: {stock['avg_volume']:,.0f}\n\n"
                    "⚠️ *High short interest stock with potential squeeze setup. Trade with caution!*"
                ),
                "color": color,
                "image": {
                    "url": f"https://elite.finviz.com/chart.ashx?t={stock['ticker']}&ty=c&ta=1&p=d"
                },
                "footer": {
                    "text": f"Short Squeeze Scanner • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                },
            }

            payload = {"embeds": [embed]}
            response = requests.post(
                self.DISCORD_WEBHOOK, json=payload, headers=headers
            )

            if response.status_code != 200:
                print(f"Failed to send alert for {stock['ticker']}: {response.text}")

            time.sleep(uniform(0.5, 1.0))

    def run_scanner(self):
        """Main method to run the scanner"""
        try:
            df = self.download_finviz_data()
            if df is None or df.empty:
                print("No data retrieved from Finviz")
                return

            stocks = self.process_data(df)
            if stocks:
                self.create_discord_alert(stocks)
                print(f"Successfully processed {len(stocks)} stocks")
            else:
                print("No stocks matched the short squeeze criteria")

        except Exception as e:
            print(f"Error running short squeeze scanner: {str(e)}")


def main(request):
    scanner = ShortSqueezeScanner()
    scanner.run_scanner()
    return "Short squeeze scanner completed successfully", 200


if __name__ == "__main__":
    main("")
