import json
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


class StrongEarningsScanner:
    def __init__(self):
        self.DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1319295673455349852/cRcFy-LCk82p9o0EcmEay1JLZJdVWqnj_2v-n12FtINsKEOF66v6Qe9Q1uQNQikfivzp"
        self.FINVIZ_EMAIL = os.getenv("FINVIZ_EMAIL")

    def download_finviz_data(self):
        """Download data from Finviz with specific parameters for strong post-earnings stocks"""
        url = "https://elite.finviz.com/export.ashx"
        params = {
            "v": "152",
            "f": "earningsdate_prevdays5,sh_avgvol_o500,sh_curvol_o500,sh_price_u50,sh_relvol_o1,ta_perf_1wup",
            "ft": "4",
            "c": "0,1,2,3,4,5,129,6,7,9,13,16,20,21,33,38,39,42,63,64,67,65,66",
            "auth": f"{self.FINVIZ_EMAIL}",
        }
        build_and_print_url(url, params)
        return fetch_csv_as_dataframe(url, params)

    def process_data(self, df):
        """Process and filter the data based on requirements"""
        numeric_columns = [
            "P/E",
            "PEG",
            "P/Free Cash Flow",
            "EPS (ttm)",
            "EPS growth next 5 years",
            "Sales growth past 5 years",
            "Return on Equity",
            "Total Debt/Equity",
            "Gross Margin",
        ]

        # Convert numeric columns to float first
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col].replace({"N/A": None}), errors="coerce")

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
                "volume": stock["Volume"],
                "avg_volume": stock["Average Volume"],
                "rel_volume": stock["Relative Volume"],
                "week_performance": stock["Performance (Week)"],
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

            # Prepare data for Discord alert with additional metrics
            processed_stocks.append(
                {
                    "ticker": stock["Ticker"],
                    "company": stock["Company"],
                    "price": stock["Price"],
                    "change": stock["Change"],
                    "volume": stock["Volume"],
                    "avg_volume": stock["Average Volume"],
                    "rel_volume": stock["Relative Volume"],
                    "market_cap": stock["Market Cap"],
                    "sector": stock["Sector"],
                    "industry": stock["Industry"],
                    "week_performance": stock["Performance (Week)"],
                    "pe_ratio": stock["P/E"],
                    "peg_ratio": stock["PEG"],
                    "fcf_ratio": stock["P/Free Cash Flow"],
                    "eps_ttm": stock["EPS (ttm)"],
                    "eps_growth_5y": stock["EPS growth next 5 years"],
                    "sales_growth_5y": stock["Sales growth past 5 years"],
                    "roe": stock["Return on Equity"],
                    "debt_equity": stock["Total Debt/Equity"],
                    "gross_margin": stock["Gross Margin"],
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
                "title": f"💪 Strong Post-Earnings Alert | {stock['ticker']}",
                "description": (
                    f"**{stock['company']}** → ${stock['price']} ({stock['change']})\n\n"
                    "**📊 Trading Metrics:**\n"
                    f"• Week Performance: {stock['week_performance']} 📈\n"
                    f"• Current Volume: {stock['volume']:,.0f} 📊\n"
                    f"• Relative Volume: {stock['rel_volume']:.2f}x 🔄\n"
                    f"• Average Volume: {stock['avg_volume']:,.0f} 📈\n\n"
                    "**📈 Valuation & Growth:**\n"
                    f"• P/E Ratio: {stock['pe_ratio']}\n"
                    f"• PEG Ratio: {stock['peg_ratio']}\n"
                    f"• P/FCF: {stock['fcf_ratio']}\n"
                    f"• EPS (TTM): ${stock['eps_ttm']}\n"
                    f"• EPS Growth (5Y): {stock['eps_growth_5y']}\n"
                    f"• Sales Growth (5Y): {stock['sales_growth_5y']}\n\n"
                    "**💰 Financial Health:**\n"
                    f"• Return on Equity: {stock['roe']}\n"
                    f"• Debt/Equity: {stock['debt_equity']}\n"
                    f"• Gross Margin: {stock['gross_margin']}\n\n"
                    "**🏢 Company Info:**\n"
                    f"• Sector: {stock['sector']}\n"
                    f"• Industry: {stock['industry']}\n"
                    f"• Market Cap: ${stock['market_cap']}M\n\n"
                    f"• Country: {stock['country']} 🌍\n\n"
                    "🎯 *Strong earnings performer with notable growth metrics*"
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

            if response.status_code != 204:
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
