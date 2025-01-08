import json
from datetime import datetime

from common.base_scanner import BaseScanner


class StrongEarningsScanner(BaseScanner):
    def __init__(self):
        super().__init__(
            "1326541453555662939/DWXgkpT_70fBT5lOYtBVpizzchRvVN2iY7nJDcfyTvZ-JypjU1FFTH9pHWBZG6vh_a1n"
        )
        self.MARKET_CAP_RANGES = {
            "Small Cap": (0, 2000),
            "Mid Cap": (2000, 10000),
            "Large Cap": (10000, float("inf")),
        }

    def get_filter_params(self):
        return "earningsdate_prevdays5,sh_avgvol_o500,sh_curvol_o500,sh_price_u50,sh_relvol_o1,ta_perf_1wup"

    def get_alert_type(self):
        return "Strong Post-Earnings Alert"

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
                "avg_volume": stock["Average Volume"],
                "rel_volume": stock["Relative Volume"],
                "market_cap": stock["Market Cap"],
                "cap_type": cap_type,
                "eps_ttm": stock["EPS (ttm)"],
                "week_performance": stock["Performance (Week)"],
            }
        )

    def create_discord_alert(self, categorized_stocks):
        for cap_type, stocks in categorized_stocks.items():
            if not stocks:
                continue

            for stock in stocks:
                embed = {
                    "title": f"💪 Strong Post-Earnings Alert | {stock['Ticker']} ({cap_type})",
                    "description": (
                        f"**{stock['Company']}** → ${stock['Price']:.2f} ({stock['Change'] * 100:.2f}%)\n\n"
                        "**📊 Key Metrics:**\n"
                        f"• EPS Growth (5Y): {stock['EPS growth next 5 years'] * 100:.2f}% 📈\n"
                        f"• Sales Growth (5Y): {stock['Sales growth past 5 years'] * 100:.2f}% 🚀\n"
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
                        "url": f"https://elite.finviz.com/chart.ashx?t={stock['Ticker']}&ty=c&ta=1&p=d"
                    },
                    "footer": {
                        "text": f"Strong Post-Earnings Alert • {datetime.now().strftime(self.DATETIME_FORMAT)}"
                    },
                }

                self.send_discord_message(embed)


def main(request):
    scanner = StrongEarningsScanner()
    scanner.run_scanner()
    return "Scanner completed successfully", 200


if __name__ == "__main__":
    main("")
