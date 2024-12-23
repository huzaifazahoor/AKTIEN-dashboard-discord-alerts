import json
from datetime import datetime

from common.base_scanner import BaseScanner


class MomentumGapScanner(BaseScanner):
    def __init__(self):
        super().__init__(
            "https://discord.com/api/webhooks/1319301200780460133/2_m1P0R-V7vV__MUZWp9WfuQXgcXQKGeruKmgvte9aS0OY8wZU4X-PB85J4a8FytoZp5"
        )

    def get_filter_params(self):
        return "sh_price_u30,sh_relvol_o5,ta_perf_d15o,ta_rsi_ob70"

    def get_alert_type(self):
        return "Momentum Gap Alert"

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
                "gap": stock["Change"],
                "market_cap": stock["Market Cap"],
            }
        )

    def create_discord_alert(self, stocks):
        for stock in stocks:
            color = int("ff0000" if stock["Change"] * 100 >= 20 else "ffa500", 16)

            embed = {
                "title": f"🚀 Momentum Gap Alert | {stock['Ticker']}",
                "description": (
                    f"**{stock['Company']}** → ${stock['Price']:.2f}\n\n"
                    "**📊 Gap Metrics:**\n"
                    f"• Gap Up: +{stock['Change'] * 100:.2f}% 📈\n"
                    f"• Relative Volume: {stock['Relative Volume']:.2f}x 📊\n"
                    f"• Current Volume: {stock['Volume']:,} 📈\n\n"
                    "**💡 Trading Info:**\n"
                    f"• Market Cap: ${stock['Market Cap'] / 1e6:.2f}M\n"
                    f"• Sector: {stock['Sector']}\n"
                    f"• Industry: {stock['Industry']}\n\n"
                    f"• Country: {stock['Country']} 🌍\n\n"
                    "⚠️ *High volatility stock with significant gap up. Trade with caution!*"
                ),
                "color": color,
                "image": {
                    "url": f"https://elite.finviz.com/chart.ashx?t={stock['Ticker']}&ty=c&ta=1&p=d"
                },
                "footer": {
                    "text": f"Gap Scanner Alert • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                },
            }

            self.send_discord_message(embed)


def main(request):
    scanner = MomentumGapScanner()
    scanner.run_scanner()
    return "Momentum scanner completed successfully", 200


if __name__ == "__main__":
    main("")
