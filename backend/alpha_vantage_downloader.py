import requests
import time
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timedelta
import json
import os
from typing import List, Dict

# Configuración
ALPHA_VANTAGE_API_KEY = "43CK04U9WWUI2XZN"
SUPABASE_URL = "https://cxtresumeeybaksjtaqs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN4dHJlc3VtZWV5YmFrc2p0YXFzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTMwMzE5ODgsImV4cCI6MjA2ODYwNzk4OH0.oo1l7GeAJQOGzM9nMgzFYrxwKNIU9x0B0RJlx7ShSOM"

# Inicializar cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Pares de divisas principales
FOREX_PAIRS = [
    ("EUR", "USD"),
    ("GBP", "USD"),
    ("USD", "JPY"),
    ("USD", "CHF"),
    ("AUD", "USD"),
    ("CHF", "JPY")
]

# Timeframes disponibles en Alpha Vantage
TIMEFRAMES = {
    "1min": "1min",
    "5min": "5min",
    "15min": "15min",
    "30min": "30min",
    "60min": "60min"
}


def fetch_forex_intraday(from_symbol: str, to_symbol: str, interval: str) -> Dict:
    """
    Descargar datos intraday de Alpha Vantage
    """
    url = f"https://www.alphavantage.co/query"
    params = {
        "function": "FX_INTRADAY",
        "from_symbol": from_symbol,
        "to_symbol": to_symbol,
        "interval": interval,
        "apikey": ALPHA_VANTAGE_API_KEY,
        "outputsize": "full"  # Obtener hasta 30 días de datos
    }

    try:
        print(f"Descargando {from_symbol}/{to_symbol} - {interval}...")
        response = requests.get(url, params=params)
        response.raise_for_status()

        data = response.json()

        # Debug: mostrar estructura de respuesta
        print(f"Claves en respuesta: {list(data.keys())}")

        # Mostrar mensaje de Information si existe
        if "Information" in data:
            print(f"Mensaje de Alpha Vantage: {data['Information']}")

        # Verificar si hay errores en la respuesta
        if "Error Message" in data:
            print(f"Error: {data['Error Message']}")
            return None

        if "Note" in data:
            print(f"Límite de API alcanzado: {data['Note']}")
            return None

        return data

    except requests.exceptions.RequestException as e:
        print(f"Error al descargar datos: {e}")
        return None


def process_forex_data(data: Dict, pair: str, timeframe: str) -> List[Dict]:
    """
    Procesar datos de Alpha Vantage al formato de Supabase
    """
    if not data:
        return []

    # Buscar la clave de datos de series temporales (corregido)
    time_series_key = None
    possible_keys = [
        f"Time Series FX ({timeframe})",
        f"Time Series FX ({timeframe.upper()})",
        "Time Series FX (Daily)",
        "Time Series FX (Weekly)",
        "Time Series FX (Monthly)"
    ]

    # Para datos intraday, buscar patrón específico
    for key in data.keys():
        if "Time Series FX" in key:
            time_series_key = key
            break

    if not time_series_key:
        print(f"Claves disponibles: {list(data.keys())}")
        return []

    time_series = data[time_series_key]
    processed_data = []

    for timestamp, values in time_series.items():
        try:
            # Manejar diferentes formatos de fecha
            try:
                dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                dt = datetime.strptime(timestamp, "%Y-%m-%d")

            # Mapear timeframes largos a códigos cortos
            tf_mapping = {
                "daily": "1d",
                "weekly": "1w",
                "monthly": "1M"
            }

            final_timeframe = tf_mapping.get(timeframe, timeframe)

            candle_data = {
                "pair": pair,
                "timeframe": final_timeframe,
                "datetime": dt.isoformat(),
                "open": float(values["1. open"]),
                "high": float(values["2. high"]),
                "low": float(values["3. low"]),
                "close": float(values["4. close"]),
                "created_at": datetime.now().isoformat()
            }

            processed_data.append(candle_data)

        except (ValueError, KeyError) as e:
            print(f"Error procesando datos para {timestamp}: {e}")
            continue

    return processed_data


def save_to_supabase(data: List[Dict]) -> bool:
    """
    Guardar datos en Supabase con manejo de duplicados
    """
    if not data:
        return False

    try:
        # Insertar datos usando upsert para evitar duplicados
        result = supabase.table("forex_candles").upsert(
            data,
            on_conflict="pair,timeframe,datetime"  # Evitar duplicados
        ).execute()

        print(f"Guardados {len(data)} registros en Supabase")
        return True

    except Exception as e:
        print(f"Error guardando en Supabase: {e}")
        return False


def download_all_timeframes():
    """
    Descargar todos los timeframes para todos los pares
    """
    total_calls = 0
    max_calls_per_day = 500
    calls_per_minute = 0
    max_calls_per_minute = 5

    for from_symbol, to_symbol in FOREX_PAIRS:
        pair = f"{from_symbol}{to_symbol}"

        for tf_name, tf_alpha in TIMEFRAMES.items():
            # Verificar límites de API
            if total_calls >= max_calls_per_day:
                print("Límite diario de API alcanzado")
                return

            if calls_per_minute >= max_calls_per_minute:
                print("Esperando 1 minuto por límite de rate...")
                time.sleep(60)
                calls_per_minute = 0

            # Descargar datos
            data = fetch_forex_intraday(from_symbol, to_symbol, tf_alpha)
            total_calls += 1
            calls_per_minute += 1

            if data:
                # Procesar datos
                processed_data = process_forex_data(data, pair, tf_name)

                if processed_data:
                    # Guardar en Supabase
                    success = save_to_supabase(processed_data)
                    if success:
                        print(f"✓ {pair} {tf_name}: {len(processed_data)} velas guardadas")
                    else:
                        print(f"✗ Error guardando {pair} {tf_name}")
                else:
                    print(f"✗ No hay datos para {pair} {tf_name}")

            # Pausa entre llamadas (recomendado)
            time.sleep(12)  # 5 calls por minuto = 12 segundos entre calls

    print(f"\nDescarga completada. Total de llamadas API: {total_calls}")


def download_daily_weekly_data():
    """
    Descargar datos diarios y semanales (funciones separadas en Alpha Vantage)
    """
    daily_weekly_functions = {
        "daily": "FX_DAILY",
        "weekly": "FX_WEEKLY",
        "monthly": "FX_MONTHLY"
    }

    for from_symbol, to_symbol in FOREX_PAIRS:
        pair = f"{from_symbol}{to_symbol}"

        for tf_name, function in daily_weekly_functions.items():
            url = f"https://www.alphavantage.co/query"
            params = {
                "function": function,
                "from_symbol": from_symbol,
                "to_symbol": to_symbol,
                "apikey": ALPHA_VANTAGE_API_KEY
            }

            try:
                print(f"Descargando {pair} - {tf_name}...")
                response = requests.get(url, params=params)
                data = response.json()

                # Procesar según el tipo de función
                time_series_key = f"Time Series FX ({tf_name.title()})"
                if time_series_key in data:
                    processed_data = []

                    for date_str, values in data[time_series_key].items():
                        try:
                            # Para datos diarios/semanales/mensuales
                            if tf_name == "daily":
                                dt = datetime.strptime(date_str, "%Y-%m-%d")
                            else:
                                dt = datetime.strptime(date_str, "%Y-%m-%d")

                            candle_data = {
                                "pair": pair,
                                "timeframe": tf_name,
                                "datetime": dt.isoformat(),
                                "open": float(values["1. open"]),
                                "high": float(values["2. high"]),
                                "low": float(values["3. low"]),
                                "close": float(values["4. close"]),
                                "created_at": datetime.now().isoformat()
                            }

                            processed_data.append(candle_data)

                        except (ValueError, KeyError) as e:
                            continue

                    if processed_data:
                        save_to_supabase(processed_data)
                        print(f"✓ {pair} {tf_name}: {len(processed_data)} velas guardadas")

                time.sleep(12)  # Respetar límites de API

            except Exception as e:
                print(f"Error descargando {pair} {tf_name}: {e}")


def main():
    """
    Función principal
    """
    print("🚀 Iniciando descarga de datos de Alpha Vantage...")
    print(f"📊 Pares a descargar: {len(FOREX_PAIRS)}")
    print(f"⏰ Timeframes intraday: {list(TIMEFRAMES.keys())}")
    print("=" * 50)

    # Verificar conexión a Supabase
    try:
        test_query = supabase.table("forex_candles").select("id").limit(1).execute()
        print("✓ Conexión a Supabase exitosa")
    except Exception as e:
        print(f"✗ Error conectando a Supabase: {e}")
        return

    # Descargar datos intraday
    print("\n📈 Descargando datos intraday...")
    download_all_timeframes()

    # Esperar antes de descargar datos diarios/semanales
    print("\n⏳ Esperando 2 minutos antes de descargar datos diarios/semanales...")
    time.sleep(120)

    # Descargar datos diarios/semanales/mensuales
    print("\n📅 Descargando datos diarios/semanales/mensuales...")
    download_daily_weekly_data()

    print("\n🎉 Descarga completada!")


if __name__ == "__main__":
    main()