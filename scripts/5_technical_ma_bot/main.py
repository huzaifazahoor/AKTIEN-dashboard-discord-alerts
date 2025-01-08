import json
from datetime import datetime

from common.base_scanner import BaseScanner


class TechnicalMAScanner(BaseScanner):
    def __init__(self):
        super().__init__(
            "1326542555566968832/9DE3ya_4uq5-ioREY69XAYJROLvMToPvCOwObAn1zZVZr_asctl5_4uVjASSowbbM8iF"
        )

    def get_filter_params(self):
        return (
            "cap_largeunder,fa_curratio_o1,sh_avgvol_o500,sh_price_10to50,"
            "sh_relvol_o1,ta_perf_13wup,ta_perf2_52wup,ta_sma20_pa,"
            "ta_sma200_pa,ta_sma50_sa200"
        )

    def get_alert_type(self):
        return "Technical MA Alert"

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
                "market_cap": stock["Market Cap"],
                "current_ratio": stock["Current Ratio"],
                "quarter_perf": stock["Performance (Quarter)"],
                "year_perf": stock["Performance (Year)"],
                "sma20": stock["20-Day Simple Moving Average"],
                "sma50": stock["50-Day Simple Moving Average"],
                "sma200": stock["200-Day Simple Moving Average"],
            }
        )

    def create_discord_alert(self, stocks):
        for stock in stocks:
            # Determine color
            # based on quarterly performance
            color = int(
                "2ecc71" if stock["Performance (Quarter)"] * 100 > 15 else "3498db",
                16,
            )

            embed = {
                "title": f"📈 Technical MA Alert | {stock['Ticker']}",
                "description": (
                    f"**{stock['Company']}** → ${stock['Price']:.2f}\n\n"
                    "**📊 Technical Metrics:**\n"
                    f"• Quarter Performance: {stock['Performance (Quarter)'] * 100:.2f}% 📈\n"
                    f"• Year Performance: {stock['Performance (Year)'] * 100:.2f}% 🚀\n"
                    f"• Current Ratio: {stock['Current Ratio']:.2f} 💪\n"
                    f"• Relative Volume: {stock['Relative Volume']:.2f}x 📊\n\n"
                    "**🎯 Moving Averages:**\n"
                    f"• Price > SMA20 ✅\n"
                    f"• Price > SMA200 ✅\n"
                    f"• SMA50 > SMA200 ✅\n\n"
                    "**💡 Trading Info:**\n"
                    f"• Market Cap: ${stock['Market Cap'] / 1e6:.2f}M\n"
                    f"• Volume: {stock['Volume']:,.0f}\n"
                    f"• Sector: {stock['Sector']}\n"
                    f"• Industry: {stock['Industry']}\n\n"
                    f"• Country: {stock['Country']} 🌍\n\n"
                    "🎯 *Strong technical setup with bullish moving averages*"
                ),
                "color": color,
                "image": {
                    "url": f"https://elite.finviz.com/chart.ashx?t={stock['Ticker']}&ty=c&ta=1&p=d"
                },
                "footer": {
                    "text": f"Technical Scanner • {datetime.now().strftime(self.DATETIME_FORMAT)}"
                },
            }

            self.send_discord_message(embed)


def main(request):
    scanner = TechnicalMAScanner()
    scanner.run_scanner()
    return "Technical MA scanner completed successfully", 200


if __name__ == "__main__":
    main("")
