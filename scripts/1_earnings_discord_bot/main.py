import json
from datetime import datetime

from common.base_scanner import BaseScanner


class EarningsAlert(BaseScanner):
    def __init__(self):
        super().__init__(
            "https://discord.com/api/webhooks/1122843142140465192/Xc9tEeA2iGOx0McuvUeDiQkbcCP8tVpMuuN3oiYhrv43QxB6cVgoJv_BMW4mxipqXVEJ"
        )
        self.MARKET_CAP_RANGES = {
            "Small Cap": (0, 2000),
            "Mid Cap": (2000, 10000),
            "Large Cap": (10000, float("inf")),
        }

    def get_filter_params(self):
        return "earningsdate_prevdays5,fa_epsrev_bp"

    def get_alert_type(self):
        return "Earnings Alert"

    def process_data(self, df):
        df["Volume Ratio"] = df["Volume"] / df["Average Volume"]
        categorized_stocks = {
            cap_type: [] for cap_type in self.MARKET_CAP_RANGES.keys()
        }

        df = self.process_columns(df)

        for _, stock in df.iterrows():
            for cap_type, (min_cap, max_cap) in self.MARKET_CAP_RANGES.items():
                if min_cap <= stock["Market Cap"] < max_cap:
                    processed_stock = self.get_processed_stock(stock)
                    processed_stock["cap_type"] = cap_type
                    categorized_stocks[cap_type].append(processed_stock)
                    break

        return categorized_stocks

    def get_alert_data(self, stock, cap_type):
        return json.dumps(
            {
                "price": stock["Price"],
                "volume": stock["Volume"],
                "market_cap": stock["Market Cap"],
                "cap_type": cap_type,
                "eps": stock["EPS (ttm)"],
            }
        )

    def create_discord_alert(self, categorized_stocks):
        for cap_type, stocks in categorized_stocks.items():
            if not stocks:
                continue

            for stock in stocks:
                embed = {
                    "title": f"🎯 Earnings Alert | {stock['Ticker']} ({'Large Cap' if stock['Market Cap'] > 1e11 else 'Mid Cap'})",
                    "description": (
                        f"**{stock['Company']}** → ${stock['Price']:.2f} ({stock['Change'] * 100:.2f}%)\n\n"
                        "**📊 Key Metrics:**\n"
                        f"• EPS Growth (Next 5Y): {stock['EPS growth next 5 years'] * 100:.2f}% 📈\n"
                        f"• Sales Growth (Last 5Y): {stock['Sales growth past 5 years'] * 100:.2f}% 🚀\n"
                        f"• PEG Ratio: {stock['PEG']:.2f} ⚡\n"
                        f"• D/E Ratio: {stock['Total Debt/Equity']:.2f} 🛡\n"
                        f"• ROE: {stock['Return on Equity'] * 100:.2f}% 💡\n"
                        f"• P/FCF: {stock['P/Free Cash Flow']:.2f} 💰\n\n"
                        "**📈 Trading Data:**\n"
                        f"• Volume: {stock['Volume']:,} | RVOL: {stock['Relative Volume']:.2f}x\n"
                        f"• Market Cap: ${stock['Market Cap'] / 1e9:.2f}B | P/E: {stock['P/E']:.2f}\n"
                        f"• Sector: {stock['Sector']} | Industry: {stock['Industry']}\n\n"
                        f"• Country: {stock['Country']} 🌍\n\n"
                    ),
                    "color": (
                        int("2ecc71", 16) if stock["Change"] >= 0 else int("e74c3c", 16)
                    ),
                    "image": {
                        "url": f"https://elite.finviz.com/chart.ashx?t={stock['Ticker']}&ty=c&ta=0&p=d"
                    },
                    "footer": {
                        "text": f"Earnings Alert • {datetime.now().strftime(self.DATETIME_FORMAT)}"
                    },
                }
                self.send_discord_message(embed)


def main(request):
    scanner = EarningsAlert()
    scanner.run_scanner()
    return "Alert sent successfully", 200


if __name__ == "__main__":
    main("")
