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


class TechnicalMAScanner:
    def __init__(self):
        self.DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1319332546936311869/_j_BYfTpA6kUHtJEEVLMCD913b2siLxo0c30CW9TOl9_QnMu7pQwx0NWaquQtWFIXdtu"
        self.FINVIZ_EMAIL = os.getenv("FINVIZ_EMAIL")

    def download_finviz_data(self):
        """Download data from Finviz with technical MA parameters"""
        url = "https://elite.finviz.com/export.ashx"
        params = {
            "v": "152",
            "f": (
                "cap_largeunder,fa_curratio_o1,sh_avgvol_o500,sh_price_10to50,"
                "sh_relvol_o1,ta_perf_13wup,ta_perf2_52wup,ta_sma20_pa,"
                "ta_sma200_pa,ta_sma50_sa200"
            ),
            "ft": "4",
            "c": ",".join([str(num) for num in range(1, 201)]),
            "auth": f"{self.FINVIZ_EMAIL}",
        }
        build_and_print_url(url, params)
        return fetch_csv_as_dataframe(url, params)

    def process_data(self, df):
        """Process and filter the data based on technical MA requirements"""
        # Convert numeric columns to appropriate types
        numeric_columns = [
            "Price",
            "Change",
            "Short Float",
            "50-Day High",
            "50-Day Low",
            "Relative Volume",
            "Volume",
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
                "market_cap": stock["Market Cap"],
                "current_ratio": stock["Current Ratio"],
                "quarter_perf": stock["Performance (Quarter)"],
                "year_perf": stock["Performance (Year)"],
                "sma20": stock["20-Day Simple Moving Average"],
                "sma50": stock["50-Day Simple Moving Average"],
                "sma200": stock["200-Day Simple Moving Average"],
            }

            alerts_to_upsert.append(
                (
                    stock["Ticker"],
                    "Technical MA Alert",
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
                    "market_cap": stock["Market Cap"],
                    "sector": stock["Sector"],
                    "industry": stock["Industry"],
                    "avg_volume": stock["Average Volume"],
                    "current_ratio": stock["Current Ratio"],
                    "quarter_perf": stock["Performance (Quarter)"],
                    "year_perf": stock["Performance (Year)"],
                    "sma20": stock["20-Day Simple Moving Average"],
                    "sma50": stock["50-Day Simple Moving Average"],
                    "sma200": stock["200-Day Simple Moving Average"],
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
            # Determine color based on performance
            color = int(
                "2ecc71" if float(stock["quarter_perf"].strip("%")) > 15 else "3498db",
                16,
            )

            embed = {
                "title": f"📈 Technical MA Alert | {stock['ticker']}",
                "description": (
                    f"**{stock['company']}** → ${stock['price']}\n\n"
                    "**📊 Technical Metrics:**\n"
                    f"• Quarter Performance: {stock['quarter_perf']} 📈\n"
                    f"• Year Performance: {stock['year_perf']} 🚀\n"
                    f"• Current Ratio: {stock['current_ratio']:.2f} 💪\n"
                    f"• Relative Volume: {stock['rel_volume']:.1f}x 📊\n\n"
                    "**🎯 Moving Averages:**\n"
                    f"• Price > SMA20 ✅\n"
                    f"• Price > SMA200 ✅\n"
                    f"• SMA50 > SMA200 ✅\n\n"
                    "**💡 Trading Info:**\n"
                    f"• Market Cap: ${stock['market_cap']}M\n"
                    f"• Volume: {stock['volume']:,.0f}\n"
                    f"• Sector: {stock['sector']}\n"
                    f"• Industry: {stock['industry']}\n\n"
                    "🎯 *Strong technical setup with bullish moving averages*"
                ),
                "color": color,
                "image": {
                    "url": f"https://elite.finviz.com/chart.ashx?t={stock['ticker']}&ty=c&ta=1&p=d"
                },
                "footer": {
                    "text": f"Technical Scanner • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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
            print("No stocks matched the technical MA criteria")


def main(request):
    scanner = TechnicalMAScanner()
    scanner.run_scanner()
    return "Technical MA scanner completed successfully", 200


if __name__ == "__main__":
    main("")
