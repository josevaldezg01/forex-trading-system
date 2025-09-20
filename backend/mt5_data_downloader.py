# scripts/mt5_github_updater.py
import MetaTrader5 as mt5
import pandas as pd
import os
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client
import logging

# Configuración desde variables de entorno (GitHub Secrets)
MT5_LOGIN = int(os.getenv('MT5_LOGIN', '7030106'))
MT5_PASSWORD = os.getenv('MT5_PASSWORD', 'Taliana123*')
MT5_SERVER = os.getenv('MT5_SERVER', 'OANDA-Live-1')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Inicializar Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configurar logging para GitHub Actions
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Pares principales (los que ya tienes descargados los comentamos)
FOREX_PAIRS = [
    "EURUSD",  # Activo
    "GBPUSD",  # Activo
    "USDJPY",  # Activo
    "GBPJPY",  # Activo
    "AUDUSD",  # Activo
    "AUDJPY",  # Activo
    "CADJPY",  # Activo
    "CHFJPY",  # Activo
    "EURJPY",  # Activo
    "NZDUSD",  # Activo
    "USDCAD",  # Activo
    "USDCHF",  # Activo
]

# Timeframes para tiempo real (cada minuto)
REAL_TIME_TIMEFRAMES = {
    mt5.TIMEFRAME_M1: "1min",  # Prioridad 1 - Siempre
    mt5.TIMEFRAME_M5: "5min",  # Prioridad 2 - Siempre
}

# Timeframes adicionales (cada 5 minutos)
ADDITIONAL_TIMEFRAMES = {
    mt5.TIMEFRAME_M15: "15min",  # Cada 5 min
    mt5.TIMEFRAME_M30: "30min",  # Cada 5 min
    mt5.TIMEFRAME_H1: "1h",  # Cada 5 min
}


def connect_mt5():
    """Conectar a MetaTrader 5"""
    try:
        if not mt5.initialize():
            logger.error("Error inicializando MT5")
            return False

        # Verificar conexión
        if not mt5.login(MT5_LOGIN, MT5_PASSWORD, MT5_SERVER):
            error = mt5.last_error()
            logger.error(f"Error conectando a MT5: {error}")
            mt5.shutdown()
            return False

        account_info = mt5.account_info()
        if account_info is None:
            logger.error("No se pudo obtener info de la cuenta")
            return False

        logger.info(f"Conectado a MT5 - Cuenta: {account_info.login}, Servidor: {account_info.server}")
        return True

    except Exception as e:
        logger.error(f"Excepción conectando MT5: {e}")
        return False


def get_symbol_name(pair):
    """Detectar el nombre correcto del símbolo (con .sml si es necesario)"""
    try:
        # Intentar primero sin extensión
        symbol_info = mt5.symbol_info(pair)
        if symbol_info is not None:
            return pair

        # Intentar con .sml
        symbol_sml = f"{pair}.sml"
        symbol_info = mt5.symbol_info(symbol_sml)
        if symbol_info is not None:
            return symbol_sml

        # Intentar otras extensiones comunes
        extensions = [".raw", ".ecn", ".m"]
        for ext in extensions:
            symbol_ext = f"{pair}{ext}"
            symbol_info = mt5.symbol_info(symbol_ext)
            if symbol_info is not None:
                return symbol_ext

        logger.warning(f"No se encontró símbolo para {pair}")
        return None

    except Exception as e:
        logger.error(f"Error detectando símbolo {pair}: {e}")
        return None


def get_latest_candle_time(pair, timeframe):
    """Obtener timestamp de la última vela en la base de datos"""
    try:
        result = supabase.table("forex_candles") \
            .select("timestamp") \
            .eq("pair", pair) \
            .eq("timeframe", timeframe) \
            .order("timestamp", desc=True) \
            .limit(1) \
            .execute()

        if result.data:
            # Convertir timestamp a datetime
            timestamp_str = result.data[0]['timestamp']
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            # Si no hay datos, empezar desde hace 24 horas
            return datetime.now(timezone.utc) - timedelta(hours=24)

    except Exception as e:
        logger.error(f"Error obteniendo última vela para {pair} {timeframe}: {e}")
        return datetime.now(timezone.utc) - timedelta(hours=1)


def download_incremental_data(pair, mt5_timeframe, timeframe_name):
    """Descargar solo datos nuevos desde la última vela"""
    try:
        symbol = get_symbol_name(pair)
        if not symbol:
            return 0

        # Obtener última fecha en la BD
        last_time = get_latest_candle_time(pair, timeframe_name)
        logger.info(f"Última vela de {pair} {timeframe_name}: {last_time}")

        # Descargar desde la última fecha hasta ahora
        now = datetime.now(timezone.utc)

        # Si la última vela es muy reciente (menos de 1 hora), solo descargar últimas 100 velas
        if (now - last_time).total_seconds() < 3600:
            rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, 100)
        else:
            # Descargar desde la última fecha
            rates = mt5.copy_rates_from(symbol, mt5_timeframe, last_time, now)

        if rates is None or len(rates) == 0:
            logger.info(f"No hay datos nuevos para {pair} {timeframe_name}")
            return 0

        logger.info(f"Descargadas {len(rates)} velas para {pair} {timeframe_name}")

        # Convertir a DataFrame
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')

        # Filtrar solo velas posteriores a la última en BD
        df = df[df['time'] > last_time]

        if df.empty:
            logger.info(f"No hay velas nuevas para {pair} {timeframe_name}")
            return 0

        # Procesar y guardar
        new_candles = process_and_save_candles(df, pair, timeframe_name)
        return new_candles

    except Exception as e:
        logger.error(f"Error descargando datos incrementales para {pair}: {e}")
        return 0


def process_and_save_candles(df, pair, timeframe):
    """Procesar DataFrame y guardar en Supabase"""
    try:
        candles_data = []

        for _, row in df.iterrows():
            # Determinar color de la vela
            color = "green" if row['close'] >= row['open'] else "red"

            candle = {
                "pair": pair,
                "timeframe": timeframe,
                "timestamp": row['time'].isoformat(),
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close']),
                "volume": int(row['tick_volume']),
                "color": color
            }
            candles_data.append(candle)

        if not candles_data:
            return 0

        # Guardar en Supabase usando upsert para evitar duplicados
        try:
            result = supabase.table("forex_candles").upsert(
                candles_data,
                on_conflict="pair,timeframe,timestamp"
            ).execute()

            logger.info(f"Guardadas {len(candles_data)} velas para {pair} {timeframe}")
            return len(candles_data)

        except Exception as e:
            logger.error(f"Error guardando en Supabase: {e}")
            return 0

    except Exception as e:
        logger.error(f"Error procesando velas: {e}")
        return 0


def cleanup_old_data():
    """Eliminar datos más antiguos de 3 años"""
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=3 * 365)

        # Contar registros antes
        count_before = supabase.table("forex_candles") \
            .select("*", count="exact") \
            .lt("timestamp", cutoff_date.isoformat()) \
            .execute()

        if count_before.count and count_before.count > 0:
            # Eliminar datos antiguos
            result = supabase.table("forex_candles") \
                .delete() \
                .lt("timestamp", cutoff_date.isoformat()) \
                .execute()

            logger.info(f"Limpieza completada: eliminados {count_before.count} registros anteriores a {cutoff_date}")
        else:
            logger.info("No hay datos antiguos para limpiar")

    except Exception as e:
        logger.error(f"Error en limpieza: {e}")


def is_forex_market_open():
    """Verificar si el mercado forex está abierto"""
    now = datetime.now(timezone.utc)
    weekday = now.weekday()  # 0=lunes, 6=domingo

    # Forex cierra viernes 22:00 UTC, abre lunes 22:00 UTC
    if weekday == 5 and now.hour >= 22:  # Viernes después de 22:00
        return False
    elif weekday == 6:  # Todo el sábado
        return False
    elif weekday == 0 and now.hour < 22:  # Lunes antes de 22:00
        return False

    return True


def main():
    """Función principal optimizada para tiempo real"""
    logger.info("=== Actualización MT5 en Tiempo Real ===")

    # Verificar credenciales
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("❌ Faltan credenciales de Supabase")
        return

    # Conectar a MT5
    if not connect_mt5():
        logger.error("❌ No se pudo conectar a MT5")
        return

    try:
        now = datetime.now(timezone.utc)
        minute = now.minute

        # CADA MINUTO: Actualizar M1 y M5 (tiempo real)
        total_new_candles = 0

        logger.info("🔄 Actualizando timeframes de tiempo real...")
        for pair in FOREX_PAIRS:
            for mt5_tf, tf_name in REAL_TIME_TIMEFRAMES.items():
                try:
                    new_candles = download_incremental_data(pair, mt5_tf, tf_name)
                    total_new_candles += new_candles

                    if new_candles > 0:
                        logger.info(f"✅ {pair} {tf_name}: +{new_candles} velas")

                except Exception as e:
                    logger.error(f"❌ Error {pair} {tf_name}: {e}")
                    continue

        # CADA 5 MINUTOS: Actualizar timeframes adicionales
        if minute % 5 == 0:
            logger.info("🔄 Actualizando timeframes adicionales...")
            for pair in FOREX_PAIRS:
                for mt5_tf, tf_name in ADDITIONAL_TIMEFRAMES.items():
                    try:
                        new_candles = download_incremental_data(pair, mt5_tf, tf_name)
                        total_new_candles += new_candles

                        if new_candles > 0:
                            logger.info(f"✅ {pair} {tf_name}: +{new_candles} velas")

                    except Exception as e:
                        logger.error(f"❌ Error {pair} {tf_name}: {e}")
                        continue

        logger.info(f"=== ✅ Completado: {total_new_candles} velas nuevas ===")

        # Limpieza solo a medianoche
        if now.hour == 0 and now.minute < 2:
            logger.info("🧹 Ejecutando limpieza de datos antiguos...")
            cleanup_old_data()

    finally:
        mt5.shutdown()
        logger.info("🔌 Conexión MT5 cerrada")


if __name__ == "__main__":
    main()