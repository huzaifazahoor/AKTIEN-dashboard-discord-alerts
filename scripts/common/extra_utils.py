from common.utils import execute_bulk_insert


def bulk_upsert_stocks(connection, cursor, stocks_data):
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


def bulk_upsert_stock_info(connection, cursor, stocks_data):
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


def bulk_upsert_alerts(connection, cursor, alerts_data):
    """Bulk upsert alert records"""
    query = """
    INSERT INTO alerts_alert (
        stock_id, alert_name, alert_datetime, data,
        created_at, updated_at
    ) VALUES %s
    ON CONFLICT (stock_id, alert_name)
    DO UPDATE SET
        alert_datetime = EXCLUDED.alert_datetime,
        data = EXCLUDED.data,
        updated_at = NOW()
    """
    execute_bulk_insert(connection, cursor, query, alerts_data)
