import json
from datetime import datetime

from common.base_scanner import BaseScanner


class ShortSqueezeScanner(BaseScanner):
    def __init__(self):
        super().__init__(
            "https://discord.com/api/webhooks/1319330056362790913/D88IoiowyiUiMxsWHKiOpUCZ-xydMlwKWoMOf9Rv6OtSd1_wFptoapGNF6pu6rRYBVHy"
        )

    def get_filter_params(self):
        return "sh_avgvol_o500,sh_relvol_o1,sh_short_o30,ta_highlow50d_b10h"

    def get_alert_type(self):
        return "Short Squeeze Alert"

    def process_data(self, df):
        df["Volume Ratio"] = df["Volume"] / df["Average Volume"]
        df = self.process_columns(df)

        processed_stocks = []
        for _, stock in df.iterrows():
            processed_stock = self.get_processed_stock(stock)
            processed_stocks.append(processed_stock)

        return processed_stocks

    def get_alert_data(self, stock):
        return json.dumps(
            {
                "price": stock["Price"],
                "change": stock["Change"],
                "volume": stock["Volume"],
                "rel_volume": stock["Relative Volume"],
                "short_float": stock["Short Float"],
                "market_cap": stock["Market Cap"],
                "fifty_day_high": stock["50-Day High"],
                "fifty_day_low": stock["50-Day Low"],
            }
        )

    def create_discord_alert(self, stocks):
        for stock in stocks:
            # Determine color dynamically based on Short Float percentage
            color = int("ff0000" if stock["Short Float"] * 100 >= 40 else "ffa500", 16)

            # Calculate distance from 50-day high dynamically
            high_distance = (
                (stock["Price"] - stock["50-Day High"]) / stock["50-Day High"] * 100
            )

            embed = {
                "title": f"🎯 Short Squeeze Alert | {stock['Ticker']}",
                "description": (
                    f"**{stock['Company']}** → ${stock['Price']:.2f}\n\n"
                    "**📊 Short Squeeze Metrics:**\n"
                    f"• Short Float: {stock['Short Float'] * 100:.2f}% 🎯\n"
                    f"• Distance from 50D High: {high_distance:.1f}% 📏\n"
                    f"• Relative Volume: {stock['Relative Volume']:.2f}x 📊\n"
                    f"• Current Volume: {stock['Volume']:,} 📈\n\n"
                    "**💡 Trading Info:**\n"
                    f"• Market Cap: ${stock['Market Cap'] / 1e6:.2f}M\n"
                    f"• Sector: {stock['Sector']}\n"
                    f"• Industry: {stock['Industry']}\n"
                    f"• Average Volume: {stock['Average Volume']:,}\n\n"
                    f"• Country: {stock['Country']} 🌍\n\n"
                    "⚠️ *High short interest stock with potential squeeze setup. Trade with caution!*"
                ),
                "color": color,
                "image": {
                    "url": f"https://elite.finviz.com/chart.ashx?t={stock['Ticker']}&ty=c&ta=1&p=d"
                },
                "footer": {
                    "text": f"Short Squeeze Scanner • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                },
            }

            self.send_discord_message(embed)


def main(request):
    scanner = ShortSqueezeScanner()
    scanner.run_scanner()
    return "Short squeeze scanner completed successfully", 200


if __name__ == "__main__":
    main("")
