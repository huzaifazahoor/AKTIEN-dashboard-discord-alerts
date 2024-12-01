import json
import os
from datetime import datetime

import requests
from common.utils import DBConnection, execute_bulk_insert, fetch_csv_as_dataframe


class EarningsAlertSystem:
    def __init__(self):
        self.DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1122843142140465192/Xc9tEeA2iGOx0McuvUeDiQkbcCP8tVpMuuN3oiYhrv43QxB6cVgoJv_BMW4mxipqXVEJ"
        self.FINVIZ_EMAIL = os.getenv("FINVIZ_EMAIL")
        self.MARKET_CAP_RANGES = {
            "Small Cap": (0, 2000),
            "Mid Cap": (2000, 10000),
            "Large Cap": (10000, float("inf")),
        }

    def bulk_upsert_stocks(self, connection, cursor, stocks_data):
        """Bulk upsert stock records"""
        query = """
        INSERT INTO stocks_stock (
            ticker, name, exchange, sector, industry, created_at, updated_at
        ) VALUES %s
        ON CONFLICT (ticker)
        DO UPDATE SET
            name = EXCLUDED.name,
            exchange = EXCLUDED.exchange,
            sector = EXCLUDED.sector,
            industry = EXCLUDED.industry,
            updated_at = NOW()
        """
        execute_bulk_insert(connection, cursor, query, stocks_data)

    def bulk_upsert_stock_info(self, connection, cursor, stocks_data):
        """Bulk upsert stock info records"""
        query = """
        INSERT INTO stocks_stockinfo (
            stock_id, market_cap, avg_volume, current_price,
            current_volume, updated_at
        ) VALUES %s
        ON CONFLICT (stock_id)
        DO UPDATE SET
            market_cap = EXCLUDED.market_cap,
            avg_volume = EXCLUDED.avg_volume,
            current_price = EXCLUDED.current_price,
            current_volume = EXCLUDED.current_volume,
            updated_at = NOW()
        """
        execute_bulk_insert(connection, cursor, query, stocks_data)

    def bulk_upsert_alerts(self, connection, cursor, alerts_data):
        """Bulk upsert alert records"""
        query = """
        INSERT INTO alerts_alert (
            stock_id, alert_name, alert_datetime, data,
            created_at, updated_at
        ) VALUES %s
        ON CONFLICT (stock_id, alert_name, alert_datetime)
        DO UPDATE SET
            data = EXCLUDED.data,
            updated_at = NOW()
        """
        execute_bulk_insert(connection, cursor, query, alerts_data)

    def download_finviz_data(self, day):
        url = "https://elite.finviz.com/export.ashx"
        params = {
            "v": "152",
            "f": f"earningsdate_{day},fa_epsrev_eo5,sh_avgvol_o500,sh_relvol_o1.5,ta_gap_u3",
            # "f": "earningsdate_prevdays5,fa_epsrev_eo5,sh_relvol_o1.5",
            "ft": "4",
            "c": "0,1,2,3,4,5,6,63,67,65,66,129",
            "auth": f"{self.FINVIZ_EMAIL}",
        }
        return fetch_csv_as_dataframe(url, params)

    def process_data(self, df, day):
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
                        "volume_ratio": round(stock["Volume Ratio"], 2),
                        "market_cap": f"${stock['Market Cap']}M",
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
                            f"{day} Earnings",
                            "NOW()",
                            json.dumps(
                                {
                                    "price": float(stock["Price"]),
                                    "volume": int(stock["Volume"]),
                                    "market_cap": float(stock["Market Cap"]),
                                    "cap_type": cap_type,
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
                self.bulk_upsert_stocks(connection, cursor, stocks_to_upsert)
                self.bulk_upsert_stock_info(connection, cursor, stocks_info_to_upsert)
                self.bulk_upsert_alerts(connection, cursor, alerts_to_upsert)

        return categorized_stocks

    def create_discord_alert(self, categorized_stocks, day):
        headers = {"Content-Type": "application/json"}

        for cap_type, stocks in categorized_stocks.items():
            if not stocks:
                continue

            embed = {
                "title": f"🎯 {day} Earnings Alert - {cap_type}",
                "description": f"High Volume Earnings Movers\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "color": int("2ecc71", 16),
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
                self.DISCORD_WEBHOOK, json=payload, headers=headers
            )

            if response.status_code != 204:
                print(
                    f"Error sending webhook: {response.status_code} - {response.text}"
                )


def main(request):
    alert_system = EarningsAlertSystem()
    for day in ["today", "yesterday"]:
        df = alert_system.download_finviz_data(day)
        categorized_stocks = alert_system.process_data(df, day.title())
        alert_system.create_discord_alert(categorized_stocks, day.title())
    return "Alert sent successfully", 200


if __name__ == "__main__":
    main("")
