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


class EarningsAlertSystem:
    def __init__(self):
        self.DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1122843142140465192/Xc9tEeA2iGOx0McuvUeDiQkbcCP8tVpMuuN3oiYhrv43QxB6cVgoJv_BMW4mxipqXVEJ"
        self.FINVIZ_EMAIL = os.getenv("FINVIZ_EMAIL")
        self.MARKET_CAP_RANGES = {
            "Small Cap": (0, 2000),
            "Mid Cap": (2000, 10000),
            "Large Cap": (10000, float("inf")),
        }

    def download_finviz_data(self):
        url = "https://elite.finviz.com/export.ashx"
        params = {
            "v": "152",
            "f": "earningsdate_prevdays5,fa_epsrev_bp",
            "ft": "4",
            "c": "0,1,2,3,4,5,6,63,67,65,66,129,7,16,20,21,9,38,33,13,39,64",
            "auth": f"{self.FINVIZ_EMAIL}",
        }
        return fetch_csv_as_dataframe(url, params)

    def process_data(self, df):
        df["Volume Ratio"] = df["Volume"] / df["Average Volume"]
        df["Change"] = df["Change"].str.rstrip("%").astype(float)

        categorized_stocks = {
            cap_type: [] for cap_type in self.MARKET_CAP_RANGES.keys()
        }

        # Prepare lists for bulk operations
        stocks_to_upsert = []
        stocks_info_to_upsert = []
        alerts_to_upsert = []

        for _, stock in df.iterrows():
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

            for cap_type, (min_cap, max_cap) in self.MARKET_CAP_RANGES.items():
                if min_cap <= stock["Market Cap"] < max_cap:
                    stock_data = {
                        "ticker": stock["Ticker"],
                        "company": stock["Company"],
                        "price": stock["Price"],
                        "change": stock["Change"],
                        "volume": stock["Volume"],
                        "volume_ratio": round(stock["Volume Ratio"], 2),
                        "market_cap": f"${stock['Market Cap']}M",
                        "sector": stock["Sector"],
                        "industry": stock["Industry"],
                        "eps_growth": stock["EPS growth next 5 years"],
                        "sales_growth": stock["Sales growth past 5 years"],
                        "peg": stock["PEG"],
                        "debt_equity": stock["Total Debt/Equity"],
                        "roe": stock["Return on Equity"],
                        "pfcf": stock["P/Free Cash Flow"],
                        "pe": stock["P/E"],
                        "rel_volume": stock["Relative Volume"],
                        "eps": stock["EPS (ttm)"],
                    }
                    # Prepare stock data for Discord alert
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
                    alerts_to_upsert.append(
                        (
                            stock["Ticker"],
                            "Earnings Alert",
                            "NOW()",
                            json.dumps(
                                {
                                    "price": stock["Price"],
                                    "volume": stock["Volume"],
                                    "market_cap": stock["Market Cap"],
                                    "cap_type": cap_type,
                                    "eps": stock["EPS (ttm)"],
                                }
                            ),
                            "NOW()",
                            "NOW()",
                        )
                    )
                    categorized_stocks[cap_type].append(stock_data)
                    break

        # Perform bulk operations
        with DBConnection() as connection:
            with connection.cursor() as cursor:
                # Bulk upsert operations
                bulk_upsert_stocks(connection, cursor, stocks_to_upsert)
                bulk_upsert_stock_info(connection, cursor, stocks_info_to_upsert)
                bulk_upsert_alerts(connection, cursor, alerts_to_upsert)

        return categorized_stocks

    def create_discord_alert(self, categorized_stocks):
        headers = {"Content-Type": "application/json"}

        for cap_type, stocks in categorized_stocks.items():
            if not stocks:
                continue

            for stock in stocks:
                price = stock["price"]
                change = stock["change"]
                company = stock["company"]

                embed = {
                    "title": f"🎯 Earnings Alert | {stock['ticker']} ({cap_type})",
                    "description": (
                        f"**{company}** → ${price} ({change}%)\n\n"
                        "**📊 Key Metrics:**\n"
                        f"• EPS Growth (Next 5Y): {stock['eps_growth']} 📈\n"
                        f"• Sales Growth (Last 5Y): {stock['sales_growth']} 🚀\n"
                        f"• PEG Ratio: {stock['peg']:.2f} ⚡\n"
                        f"• D/E Ratio: {stock['debt_equity']:.2f} 🛡\n"
                        f"• ROE: {stock['roe']} 💡\n"
                        f"• P/FCF: {stock['pfcf']:.1f} 💰\n\n"
                        "**📈 Trading Data:**\n"
                        f"• Volume: {stock['volume']:,.0f} | RVOL: {stock['volume_ratio']:.1f}x\n"
                        f"• Market Cap: {stock['market_cap']} | P/E: {stock['pe']:.1f}\n"
                        f"• Sector: {stock['sector']} | Industry: {stock['industry']}\n\n"
                    ),
                    "color": (
                        int("2ecc71", 16) if stock["change"] >= 0 else int("e74c3c", 16)
                    ),
                    "image": {
                        "url": f"https://elite.finviz.com/chart.ashx?t={stock['ticker']}&ty=c&ta=0&p=d"
                    },
                    "footer": {
                        "text": f"Alert Generated • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    },
                }

                payload = {"embeds": [embed]}
                response = requests.post(
                    self.DISCORD_WEBHOOK, json=payload, headers=headers
                )

                time.sleep(uniform(0.5, 1.0))


def main(request):
    alert_system = EarningsAlertSystem()
    df = alert_system.download_finviz_data()
    print(df.columns)
    categorized_stocks = alert_system.process_data(df)
    alert_system.create_discord_alert(categorized_stocks)
    return "Alert sent successfully", 200


if __name__ == "__main__":
    main("")
