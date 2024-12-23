import json
import os
import time
from datetime import datetime
from random import uniform

import pandas as pd
import requests
import yfinance as yf
from common.extra_utils import (
    bulk_upsert_alerts,
    bulk_upsert_stock_info,
    bulk_upsert_stocks,
)
from common.utils import DBConnection, build_and_print_url, fetch_csv_as_dataframe


class CNBCGrowthScanner:
    def __init__(self):
        self.DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1320815995035844719/ZLS1Y5Jk8i6koHn0LCQNdDX0-HZ3HCCO2-Nos7HWu8u9IWd8glpTM_NybK_McAK5GnvZ"
        self.FINVIZ_EMAIL = os.getenv("FINVIZ_EMAIL")

    def download_finviz_data(self):
        """Download data from Finviz with CNBC growth parameters"""
        url = "https://elite.finviz.com/export.ashx"
        params = {
            "v": "152",
            "f": (
                "fa_epsyoy_o20,"
                "fa_curratio_o15,"
                "fa_netmargin_o15,"
                "fa_sales5years_o15"
                "fa_salesqoq_o15"
            ),
            "ft": "4",
            "c": ",".join([str(num) for num in range(1, 201)]),
            "auth": f"{self.FINVIZ_EMAIL}",
        }
        build_and_print_url(url, params)
        return fetch_csv_as_dataframe(url, params)

    def process_data(self, df):
        """Process and filter the data based on CNBC growth requirements"""
        # Convert numeric columns
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
            df[col] = df[col].astype(str)
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
            # Get revenue change from Yahoo Finance
            revenue_change = self.get_current_revenue_change(stock["Ticker"])

            # Only process if revenue change meets criteria
            if revenue_change is not None and revenue_change > 15:
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
                    "market_cap": stock["Market Cap"],
                    "current_ratio": stock["Current Ratio"],
                    "revenue_change": revenue_change,
                    "sales_growth": stock["Sales growth past 5 years"],
                    "eps_growth": stock["EPS growth this year"],
                    "net_margin": stock["Net Profit Margin"],
                }

                alerts_to_upsert.append(
                    (
                        stock["Ticker"],
                        "CNBC Growth Alert",
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
                        "market_cap": stock["Market Cap"],
                        "sector": stock["Sector"],
                        "industry": stock["Industry"],
                        "current_ratio": stock["Current Ratio"],
                        "revenue_change": revenue_change,
                        "sales_growth": stock["Sales growth past 5 years"],
                        "eps_growth": stock["EPS growth this year"],
                        "net_margin": stock["Net Profit Margin"],
                        "avg_volume": stock["Average Volume"],
                        "country": stock["Country"],
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
                "title": f"🎯 CNBC Growth Scanner Alert | {stock['ticker']}",
                "description": (
                    f"**{stock['company']}** → ${stock['price']}\n\n"
                    "**📊 Growth Metrics:**\n"
                    f"• EPS Growth (1Y): {stock['eps_growth']:.1f}% 📈\n"
                    f"• Current Revenue Change: {stock['revenue_change']:.1f}% 💰\n"
                    f"• 5Y Revenue Growth: {stock['sales_growth']}% 📊\n\n"
                    "**💪 Financial Strength:**\n"
                    f"• Current Ratio: {stock['current_ratio']:.2f} 💪\n"
                    f"• Net Profit Margin: {stock['net_margin']}% 📈\n\n"
                    "**📈 Trading Info:**\n"
                    f"• Volume: {stock['volume']:,.0f}\n"
                    f"• Avg Volume: {stock['avg_volume']:,.0f}\n"
                    f"• Market Cap: ${stock['market_cap']}M\n"
                    f"• Sector: {stock['sector']}\n"
                    f"• Industry: {stock['industry']}\n"
                ),
                "color": int("2ecc71", 16),
                "image": {
                    "url": f"https://elite.finviz.com/chart.ashx?t={stock['ticker']}&ty=c&ta=1&p=d"
                },
                "footer": {
                    "text": f"CNBC Growth Scanner • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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
            print("No stocks matched the CNBC growth criteria")


def main(request):
    scanner = CNBCGrowthScanner()
    scanner.run_scanner()
    return "CNBC growth scanner completed successfully", 200


if __name__ == "__main__":
    main("")
