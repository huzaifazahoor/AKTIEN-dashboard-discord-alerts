import os
from datetime import datetime

import requests
from common.utils import fetch_csv_as_dataframe


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
            "f": "fa_epsrev_eo10,ta_gap_u3",
            "ft": "4",
            "c": "0,1,2,3,4,5,6,63,67,65,66",
            "auth": f"{self.FINVIZ_EMAIL}",
        }

        return fetch_csv_as_dataframe(url, params)

    def process_data(self, df):
        df["Volume Ratio"] = df["Volume"] / df["Average Volume"]
        df["Change"] = df["Change"].str.rstrip("%").astype(float)
        df = df[df["Volume Ratio"] > 1.5]

        categorized_stocks = {
            cap_type: [] for cap_type in self.MARKET_CAP_RANGES.keys()
        }

        for _, stock in df.iterrows():
            for cap_type, (min_cap, max_cap) in self.MARKET_CAP_RANGES.items():
                if min_cap <= stock["Market Cap"] < max_cap:
                    stock_data = {
                        "ticker": stock["Ticker"],
                        "company": stock["Company"],
                        "price": stock["Price"],
                        "change": stock["Change"],
                        "volume_ratio": round(stock["Volume Ratio"], 2),
                        "market_cap": f"${stock['Market Cap']}M",
                    }
                    categorized_stocks[cap_type].append(stock_data)
                    break

        return categorized_stocks

    def create_discord_alert(self, categorized_stocks):
        headers = {"Content-Type": "application/json"}

        for cap_type, stocks in categorized_stocks.items():
            if not stocks:
                continue

            embed = {
                "title": f"🎯 Earnings Alert - {cap_type}",
                "description": f"High Volume Earnings Movers\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "color": int("2ecc71", 16),  # Green
                "fields": [],
            }

            for stock in stocks:
                embed["color"] = (
                    int("2ecc71", 16) if stock["change"] >= 0 else int("e74c3c", 16)
                )

                field = {
                    "name": f"{stock['ticker']} - {stock['company']}",
                    "value": (
                        f"💰 Price: ${stock['price']}\n"
                        f"📊 Change: {stock['change']:+.2f}%\n"
                        f"📈 Volume Ratio: {stock['volume_ratio']}x\n"
                        f"💎 Market Cap: {stock['market_cap']}"
                    ),
                    "inline": False,
                }
                embed["fields"].append(field)

            payload = {"embeds": [embed]}

            response = requests.post(
                self.DISCORD_WEBHOOK,
                json=payload,
                headers=headers,
            )
            if response.status_code != 204:
                print(
                    f"Error sending webhook: {response.status_code} - {response.text}"
                )


def main(request):
    alert_system = EarningsAlertSystem()
    df = alert_system.download_finviz_data()
    categorized_stocks = alert_system.process_data(df)
    alert_system.create_discord_alert(categorized_stocks)
    return "Alert sent successfully"


if __name__ == "__main__":
    main("")
