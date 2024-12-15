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


class SteadyPerformanceScanner:
    def __init__(self):
        self.DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
        self.FINVIZ_EMAIL = os.getenv("FINVIZ_EMAIL")

    def download_finviz_data(self):
        """Download data from Finviz with steady performance parameters"""
        url = "https://elite.finviz.com/export.ashx"
        params = {
            "v": "152",
            "f": (
                "cap_midover,fa_sales5years_pos,fa_curratio_o1,"
                "an_recom_holdbetter,sh_avgvol_o200,sh_curvol_o200,"
                "sh_opt_optionshort,sh_price_o1,ta_highlow52w_b5h,"
                "ta_perf_13wup,ta_perf2_52wup,ta_rsi_nos50,ta_sma20_pa,"
                "ta_sma200_pa,ta_sma50_sb20"
            ),
            "ft": "4",
            "c": "1,2,3,4,5,6,7,8,9,10,11,12,13,14,65,66,67,68,69,70",
            "auth": f"{self.FINVIZ_EMAIL}",
        }
        return fetch_csv_as_dataframe(url, params)

    def process_data(self, df):
        """Process and filter the data based on steady performance requirements"""
        # Most filters are handled in Finviz parameters
        df = df[
            (df["Current Ratio"] > 1)  # Strong fundamentals
            & (df["Average Volume"] > 200000)  # Good liquidity
            & (df["Current Volume"] > 200000)  # Active trading
            & (df["Price"] > 1)  # No penny stocks
            & (df["RSI (14)"] > 50)  # Not oversold
            & (df["Sales growth past 5 years"] > 0)  # Positive sales growth
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
                "market_cap": stock["Market Cap"],
                "current_ratio": stock["Current Ratio"],
                "analyst_recom": stock["Recommendation"],
                "sales_growth": stock["Sales growth past 5 years"],
                "rsi": stock["RSI (14)"],
                "quarter_perf": stock["Perf Quarter"],
                "year_perf": stock["Perf Year"],
                "distance_from_high": stock["Distance from High"],
            }

            alerts_to_upsert.append(
                (
                    stock["Ticker"],
                    "Steady Performance Alert",
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
                    "analyst_recom": stock["Recommendation"],
                    "sales_growth": stock["Sales growth past 5 years"],
                    "rsi": stock["RSI (14)"],
                    "quarter_perf": stock["Perf Quarter"],
                    "year_perf": stock["Perf Year"],
                    "distance_from_high": stock["Distance from High"],
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
            # Determine color based on overall performance
            color = int(
                "2ecc71" if float(stock["year_perf"].strip("%")) > 20 else "3498db", 16
            )

            embed = {
                "title": f"💫 Steady Performance Alert | {stock['ticker']}",
                "description": (
                    f"**{stock['company']}** → ${stock['price']}\n\n"
                    "**📊 Performance Metrics:**\n"
                    f"• Quarter Performance: {stock['quarter_perf']} 📈\n"
                    f"• Year Performance: {stock['year_perf']} 🚀\n"
                    f"• Sales Growth (5Y): {stock['sales_growth']}% 📊\n"
                    f"• RSI(14): {stock['rsi']:.1f} ⚡\n"
                    f"• Distance from 52w High: {stock['distance_from_high']}% 📏\n\n"
                    "**💡 Fundamental Strength:**\n"
                    f"• Current Ratio: {stock['current_ratio']:.2f} 💪\n"
                    f"• Analyst Recommendation: {stock['analyst_recom']} 📋\n"
                    f"• Market Cap: ${stock['market_cap']}M\n\n"
                    "**📈 Trading Info:**\n"
                    f"• Volume: {stock['volume']:,.0f}\n"
                    f"• Avg Volume: {stock['avg_volume']:,.0f}\n"
                    f"• Sector: {stock['sector']}\n"
                    f"• Industry: {stock['industry']}\n\n"
                    "🎯 *Strong steady performer with solid fundamentals*"
                ),
                "color": color,
                "image": {
                    "url": f"https://elite.finviz.com/chart.ashx?t={stock['ticker']}&ty=c&ta=1&p=d"
                },
                "footer": {
                    "text": f"Steady Performance Scanner • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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
                print("No stocks matched the steady performance criteria")

        except Exception as e:
            print(f"Error running steady performance scanner: {str(e)}")


def main(request):
    scanner = SteadyPerformanceScanner()
    scanner.run_scanner()
    return "Steady performance scanner completed successfully", 200


if __name__ == "__main__":
    main("")
