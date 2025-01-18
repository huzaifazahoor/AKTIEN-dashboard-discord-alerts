import json
from datetime import datetime

from common.base_scanner import BaseScanner


class CNBCGrowthScanner(BaseScanner):
    def __init__(self):
        super().__init__(
            "1326543415206215764/C-2LturhAi2tMe6A9XtI0K__6l9hcO0DZpfASevvUzW0kYWvLvB-AqEhEDm8nGZ73XNo"
        )

    def get_filter_params(self):
        return (
            "fa_epsyoy_o20,"
            "fa_curratio_o15,"
            "fa_netmargin_o15,"
            "fa_sales5years_o15,"
            "fa_salesqoq_o15"
        )

    def get_alert_type(self):
        return "CNBC Growth Alert"

    def process_data(self, df):
        df["Volume Ratio"] = df["Volume"] / df["Average Volume"]
        df = self.process_columns(df)

        processed_stocks = []
        for _, stock in df.iterrows():
            # Only process stocks meeting the
            # Sales growth quarter-over-quarter criteria
            if stock["Sales growth quarter over quarter"] > 15:
                processed_stock = self.get_processed_stock(stock)
                processed_stock["sales_qoq_growth"] = stock[
                    "Sales growth quarter over quarter"
                ]
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
                "sales_qoq_growth": stock["sales_qoq_growth"],
                "sales_growth": stock["Sales growth past 5 years"],
                "eps_growth": stock["EPS growth this year"],
                "net_margin": stock["Profit Margin"],
            }
        )

    def create_discord_alert(self, stocks):
        for stock in stocks:
            embed = {
                "title": f"🎯 Growth Scanner Alert | {stock['Ticker']}",
                "description": (
                    f"**{stock['Company']}** → ${stock['Price']:.2f}\n\n"
                    "**📊 Growth Metrics:**\n"
                    f"• EPS Growth (1Y): {stock['EPS growth this year'] * 100:.2f}% 📈\n"
                    f"• Sales Growth QoQ: {stock['Sales growth quarter over quarter'] * 100:.2f}% 💰\n"
                    f"• 5Y Revenue Growth: {stock['Sales growth past 5 years'] * 100:.2f}% 📊\n\n"
                    "**💪 Financial Strength:**\n"
                    f"• Current Ratio: {stock['Current Ratio']:.2f} 💪\n"
                    f"• Net Profit Margin: {stock['Profit Margin'] * 100:.2f}% 📈\n\n"
                    "**📈 Trading Info:**\n"
                    f"• Volume: {stock['Volume']:,.0f}\n"
                    f"• Avg Volume: {stock['Average Volume']:,.0f}\n"
                    f"• Market Cap: ${stock['Market Cap'] / 1e6:.2f}M\n"
                    f"• Sector: {stock['Sector']}\n"
                    f"• Industry: {stock['Industry']}\n"
                ),
                "color": int("2ecc71", 16),
                "image": {
                    "url": f"https://elite.finviz.com/chart.ashx?t={stock['Ticker']}&ty=c&ta=1&p=d"
                },
                "footer": {
                    "text": f"BulleXpert Scanner • {datetime.now().strftime(self.DATETIME_FORMAT)}"
                },
            }

            self.send_discord_message(embed)


def main(request):
    scanner = CNBCGrowthScanner()
    scanner.run_scanner()
    return "CNBC growth scanner completed successfully", 200


if __name__ == "__main__":
    main("")
