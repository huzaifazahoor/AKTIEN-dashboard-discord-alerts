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


class StrongEarningsScanner:
    def __init__(self):
        self.DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
        self.FINVIZ_EMAIL = os.getenv("FINVIZ_EMAIL")

    def download_finviz_data(self):
        """Download data from Finviz with specific parameters for strong post-earnings stocks"""
        url = "https://elite.finviz.com/export.ashx"
        params = {
            "v": "152",
            "f": "earningsdate_prevdays5,sh_avgvol_o500,sh_curvol_o500,sh_price_u50,sh_relvol_o1,ta_perf_1wup",
            "ft": "4",
            "c": "1,2,3,4,5,6,7,8,9,10,11,12,13,14,65,66,67",  # Columns to fetch
            "auth": f"{self.FINVIZ_EMAIL}",
        }
        return fetch_csv_as_dataframe(url, params)

    def process_data(self, df):
        """Process and filter the data based on requirements"""
        # Additional filtering if needed
        df = df[
            (df["Price"] < 50)
            & (df["Avg Volume"] > 500000)
            & (df["Relative Volume"] > 1)
            & (df["Current Volume"] > 500000)
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
                    stock["Avg Volume"],
                    stock["Price"],
                    stock["Volume"],
                    "NOW()",
                )
            )

            # Prepare alert data
            alert_data = {
                "price": stock["Price"],
                "volume": stock["Volume"],
                "avg_volume": stock["Avg Volume"],
                "rel_volume": stock["Relative Volume"],
                "week_performance": stock["Week Performance"],
                "market_cap": stock["Market Cap"],
            }

            alerts_to_upsert.append(
                (
                    stock["Ticker"],
                    "Strong Post-Earnings Alert",
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
                    "avg_volume": stock["Avg Volume"],
                    "rel_volume": stock["Relative Volume"],
                    "market_cap": stock["Market Cap"],
                    "sector": stock["Sector"],
                    "industry": stock["Industry"],
                    "week_change": stock["Week Performance"],
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
            embed = {
                "title": f"💪 Strong Post-Earnings Alert | {stock['ticker']}",
                "description": (
                    f"**{stock['company']}** → ${stock['price']}\n\n"
                    "**📊 Key Metrics:**\n"
                    f"• Week Performance: {stock['week_change']} 📈\n"
                    f"• Current Volume: {stock['volume']:,.0f} 📊\n"
                    f"• Relative Volume: {stock['rel_volume']:.2f}x 🔄\n"
                    f"• Average Volume: {stock['avg_volume']:,.0f} 📈\n\n"
                    "**🏢 Company Info:**\n"
                    f"• Sector: {stock['sector']}\n"
                    f"• Industry: {stock['industry']}\n"
                    f"• Market Cap: ${stock['market_cap']}M\n\n"
                    "🎯 *Potential day/swing trading candidate showing strength after earnings*"
                ),
                "color": int("2ecc71", 16),
                "image": {
                    "url": f"https://elite.finviz.com/chart.ashx?t={stock['ticker']}&ty=c&ta=1&p=d"
                },
                "footer": {
                    "text": f"Scanner Alert • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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
                print("No stocks matched the criteria")

        except Exception as e:
            print(f"Error running scanner: {str(e)}")


def main(request):
    scanner = StrongEarningsScanner()
    scanner.run_scanner()
    return "Scanner completed successfully", 200


if __name__ == "__main__":
    main("")
