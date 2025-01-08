import json
from datetime import datetime

from common.base_scanner import BaseScanner


class SteadyPerformanceScanner(BaseScanner):
    def __init__(self):
        super().__init__(
            "1326543155255840810/tMCyUfXq4rABkumgm9bJyBGYn5M6vo_UdGYDsFja8csaOeOTh4xF5mHPquI2115R-4Ui"
        )

    def get_filter_params(self):
        return (
            "cap_midover,fa_sales5years_pos,fa_curratio_o1,"
            "an_recom_holdbetter,sh_avgvol_o200,sh_curvol_o200,"
            "sh_opt_optionshort,sh_price_o1,ta_highlow52w_b5h,"
            "ta_perf_13wup,ta_perf2_52wup,ta_rsi_nos50,ta_sma20_pa,"
            "ta_sma200_pa,ta_sma50_sb20"
        )

    def get_alert_type(self):
        return "Steady Performance Alert"

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
                "market_cap": stock["Market Cap"],
                "current_ratio": stock["Current Ratio"],
                "analyst_recom": stock["Analyst Recom"],
                "sales_growth": stock["Sales growth past 5 years"],
                "rsi": stock["Relative Strength Index (14)"],
                "quarter_perf": stock["Performance (Quarter)"],
                "year_perf": stock["Performance (Year)"],
            }
        )

    def create_discord_alert(self, stocks):
        for stock in stocks:
            # Determine color
            # based on yearly performance
            color = int(
                "2ecc71" if stock["Performance (Year)"] * 100 > 20 else "3498db",
                16,
            )

            embed = {
                "title": f"💫 Steady Performance Alert | {stock['Ticker']}",
                "description": (
                    f"**{stock['Company']}** → ${stock['Price']:.2f}\n\n"
                    "**📊 Performance Metrics:**\n"
                    f"• Quarter Performance: {stock['Performance (Quarter)'] * 100:.2f}% 📈\n"
                    f"• Year Performance: {stock['Performance (Year)'] * 100:.2f}% 🚀\n"
                    f"• Sales Growth (5Y): {stock['Sales growth past 5 years'] * 100:.2f}% 📊\n"
                    f"• RSI(14): {stock['Relative Strength Index (14)']:.2f} ⚡\n\n"
                    "**💡 Fundamental Strength:**\n"
                    f"• Current Ratio: {stock['Current Ratio']:.2f} 💪\n"
                    f"• Analyst Recommendation: {stock['Analyst Recom']:.2f} 📋\n"
                    f"• Market Cap: ${stock['Market Cap'] / 1e6:.2f}M\n\n"
                    "**📈 Trading Info:**\n"
                    f"• Volume: {stock['Volume']:,}\n"
                    f"• Avg Volume: {stock['Average Volume']:,}\n"
                    f"• Sector: {stock['Sector']}\n"
                    f"• Industry: {stock['Industry']}\n\n"
                    f"• Country: {stock['Country']} 🌍\n\n"
                    "🎯 *Strong steady performer with solid fundamentals*"
                ),
                "color": color,
                "image": {
                    "url": f"https://elite.finviz.com/chart.ashx?t={stock['Ticker']}&ty=c&ta=1&p=d"
                },
                "footer": {
                    "text": f"Steady Performance Scanner • {datetime.now().strftime(self.DATETIME_FORMAT)}"
                },
            }

            self.send_discord_message(embed)


def main(request):
    scanner = SteadyPerformanceScanner()
    scanner.run_scanner()
    return "Steady performance scanner completed successfully", 200


if __name__ == "__main__":
    main("")
