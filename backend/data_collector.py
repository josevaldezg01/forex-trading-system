# backend/data_collector.py
import os
import time
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import json

try:
    from dotenv import load_dotenv

    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass

from config import API_CONFIG, SYMBOL_MAPPING, CURRENCY_PAIRS, get_api_symbol

# Configurar logging
logger = logging.getLogger(__name__)


class ForexDataCollector:
    """Recolector de datos Forex desde múltiples APIs"""

    def __init__(self):
        self.apis = API_CONFIG
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ForexTradingSystem/1.0'
        })

        # Cache simple para evitar llamadas repetidas
        self.cache = {}
        self.cache_ttl = 300  # 5 minutos

    def _make_request(self, url: str, params: Dict[str, Any], api_name: str) -> Optional[Dict[str, Any]]:
        """Hacer petición HTTP con manejo de errores y reintentos"""
        api_config = self.apis.get(api_name, {})
        max_retries = api_config.get('retry_attempts', 3)
        retry_delay = api_config.get('retry_delay', 2)
        timeout = api_config.get('timeout', 30)

        for attempt in range(max_retries):
            try:
                logger.debug(f"🔄 Petición a {api_name}: {url}")

                response = self.session.get(url, params=params, timeout=timeout)
                response.raise_for_status()

                data = response.json()
                logger.debug(f"✅ Respuesta exitosa de {api_name}")
                return data

            except requests.exceptions.RequestException as e:
                logger.warning(f"⚠️ Intento {attempt + 1}/{max_retries} fallido para {api_name}: {e}")

                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    logger.error(f"❌ Todos los intentos fallaron para {api_name}")

            except json.JSONDecodeError as e:
                logger.error(f"❌ Error decodificando JSON de {api_name}: {e}")
                break

        return None

    def _get_cache_key(self, pair: str, timeframe: str, limit: int) -> str:
        """Generar clave de cache"""
        return f"{pair}_{timeframe}_{limit}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Verificar si el cache es válido"""
        if cache_key not in self.cache:
            return False

        cached_time = self.cache[cache_key].get('timestamp', 0)
        return time.time() - cached_time < self.cache_ttl

    def get_forex_data_alpha_vantage(self, pair: str, timeframe: str, limit: int = 1000) -> Optional[pd.DataFrame]:
        """Obtener datos de Alpha Vantage"""
        try:
            api_config = self.apis['alpha_vantage']
            api_key = api_config['key']

            if not api_key:
                logger.warning("⚠️ Alpha Vantage API key no configurada")
                return None

            # Mapear símbolo
            symbol = get_api_symbol(pair, 'alpha_vantage')

            # Mapear timeframe a función de Alpha Vantage
            function_map = {
                '1m': 'FX_INTRADAY',
                '5m': 'FX_INTRADAY',
                '15m': 'FX_INTRADAY',
                '30m': 'FX_INTRADAY',
                '1h': 'FX_INTRADAY',
                '4h': 'FX_INTRADAY',
                '1d': 'FX_DAILY',
                '1w': 'FX_WEEKLY',
                '1M': 'FX_MONTHLY'
            }

            interval_map = {
                '1m': '1min',
                '5m': '5min',
                '15m': '15min',
                '30m': '30min',
                '1h': '60min',
                '4h': '60min'  # Alpha Vantage no tiene 4h, usamos 1h
            }

            function = function_map.get(timeframe, 'FX_DAILY')

            params = {
                'function': function,
                'from_symbol': symbol.split('/')[0],
                'to_symbol': symbol.split('/')[1],
                'apikey': api_key,
                'outputsize': 'full' if limit > 100 else 'compact'
            }

            # Agregar intervalo para datos intraday
            if function == 'FX_INTRADAY':
                params['interval'] = interval_map.get(timeframe, '60min')

            url = api_config['base_url']
            data = self._make_request(url, params, 'alpha_vantage')

            if not data:
                return None

            # Procesar respuesta de Alpha Vantage
            time_series_key = None
            for key in data.keys():
                if 'Time Series' in key:
                    time_series_key = key
                    break

            if not time_series_key or time_series_key not in data:
                logger.error(f"❌ No se encontraron datos de series temporales en Alpha Vantage para {pair}")
                logger.debug(f"Respuesta: {list(data.keys())}")
                return None

            time_series = data[time_series_key]

            # Convertir a DataFrame
            df_data = []
            for timestamp, values in time_series.items():
                row = {
                    'timestamp': pd.to_datetime(timestamp),
                    'open': float(values.get('1. open', 0)),
                    'high': float(values.get('2. high', 0)),
                    'low': float(values.get('3. low', 0)),
                    'close': float(values.get('4. close', 0)),
                    'volume': float(values.get('5. volume', 0)) if '5. volume' in values else 0
                }
                df_data.append(row)

            if not df_data:
                logger.error(f"❌ No hay datos procesables para {pair}")
                return None

            df = pd.DataFrame(df_data)
            df = df.sort_values('timestamp').reset_index(drop=True)
            df = df.tail(limit)  # Limitar número de registros

            logger.info(f"✅ Alpha Vantage: {len(df)} registros para {pair} {timeframe}")
            return df

        except Exception as e:
            logger.error(f"❌ Error obteniendo datos de Alpha Vantage para {pair}: {e}")
            return None

    def get_forex_data_yahoo(self, pair: str, timeframe: str, limit: int = 1000) -> Optional[pd.DataFrame]:
        """Obtener datos de Yahoo Finance (backup)"""
        try:
            # Mapear símbolo para Yahoo Finance
            symbol = get_api_symbol(pair, 'yahoo_finance')

            # Mapear timeframe a intervalos de Yahoo
            interval_map = {
                '1m': '1m',
                '5m': '5m',
                '15m': '15m',
                '30m': '30m',
                '1h': '1h',
                '4h': '1h',  # Yahoo no tiene 4h, usar 1h
                '1d': '1d',
                '1w': '1wk',
                '1M': '1mo'
            }

            interval = interval_map.get(timeframe, '1d')

            # Calcular período basado en limit y timeframe
            if timeframe in ['1m', '5m', '15m', '30m']:
                period = min(limit * 5, 7)  # Días
            elif timeframe in ['1h', '4h']:
                period = min(limit // 4, 30)  # Días
            elif timeframe == '1d':
                period = min(limit, 365)  # Días
            else:
                period = limit

            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=period)

            params = {
                'interval': interval,
                'period1': int(start_time.timestamp()),
                'period2': int(end_time.timestamp()),
                'events': 'history',
                'includeAdjustedClose': 'false'
            }

            url = f"{self.apis['yahoo_finance']['base_url']}/{symbol}"

            # Configurar headers específicos para Yahoo
            headers = {
                'User-Agent': self.apis['yahoo_finance']['user_agent']
            }

            response = self.session.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()

            if 'chart' not in data or 'result' not in data['chart'] or not data['chart']['result']:
                logger.error(f"❌ No hay datos en Yahoo Finance para {pair}")
                return None

            result = data['chart']['result'][0]

            if 'timestamp' not in result or not result['timestamp']:
                logger.error(f"❌ No hay timestamps en Yahoo Finance para {pair}")
                return None

            # Extraer datos OHLCV
            timestamps = result['timestamp']
            indicators = result['indicators']['quote'][0]

            df_data = []
            for i, ts in enumerate(timestamps):
                try:
                    row = {
                        'timestamp': pd.to_datetime(ts, unit='s', utc=True),
                        'open': float(indicators['open'][i]) if indicators['open'][i] is not None else 0,
                        'high': float(indicators['high'][i]) if indicators['high'][i] is not None else 0,
                        'low': float(indicators['low'][i]) if indicators['low'][i] is not None else 0,
                        'close': float(indicators['close'][i]) if indicators['close'][i] is not None else 0,
                        'volume': float(indicators['volume'][i]) if indicators['volume'][i] is not None else 0
                    }

                    # Validar que no todos los valores sean 0
                    if row['open'] > 0 or row['high'] > 0 or row['low'] > 0 or row['close'] > 0:
                        df_data.append(row)

                except (ValueError, TypeError, IndexError):
                    continue

            if not df_data:
                logger.error(f"❌ No hay datos válidos en Yahoo Finance para {pair}")
                return None

            df = pd.DataFrame(df_data)
            df = df.sort_values('timestamp').reset_index(drop=True)
            df = df.tail(limit)

            logger.info(f"✅ Yahoo Finance: {len(df)} registros para {pair} {timeframe}")
            return df

        except Exception as e:
            logger.error(f"❌ Error obteniendo datos de Yahoo Finance para {pair}: {e}")
            return None

    def get_forex_data(self, pair: str, timeframe: str, limit: int = 1000) -> Optional[pd.DataFrame]:
        """Obtener datos Forex con fallback entre APIs"""

        # Verificar cache primero
        cache_key = self._get_cache_key(pair, timeframe, limit)
        if self._is_cache_valid(cache_key):
            logger.debug(f"📋 Usando datos en cache para {pair} {timeframe}")
            return self.cache[cache_key]['data']

        logger.info(f"🔍 Obteniendo datos para {pair} {timeframe} (límite: {limit})")

        # Lista de APIs para probar en orden
        apis_to_try = []

        # Alpha Vantage tiene prioridad si hay API key
        if self.apis['alpha_vantage']['key']:
            apis_to_try.append(('alpha_vantage', self.get_forex_data_alpha_vantage))

        # Yahoo Finance como fallback
        apis_to_try.append(('yahoo_finance', self.get_forex_data_yahoo))

        for api_name, api_function in apis_to_try:
            try:
                logger.debug(f"🔄 Intentando {api_name} para {pair}")

                # Respetar rate limits
                if api_name == 'alpha_vantage':
                    time.sleep(1)  # Alpha Vantage: max 5 calls per minute

                df = api_function(pair, timeframe, limit)

                if df is not None and len(df) > 0:
                    # Validar datos
                    if self._validate_forex_data(df, pair, timeframe):
                        # Guardar en cache
                        self.cache[cache_key] = {
                            'data': df,
                            'timestamp': time.time(),
                            'source': api_name
                        }

                        logger.info(f"✅ Datos obtenidos de {api_name}: {len(df)} registros para {pair} {timeframe}")
                        return df
                    else:
                        logger.warning(f"⚠️ Datos inválidos de {api_name} para {pair}")

            except Exception as e:
                logger.warning(f"⚠️ Error con {api_name} para {pair}: {e}")
                continue

        logger.error(f"❌ No se pudieron obtener datos para {pair} {timeframe}")
        return None

    def _validate_forex_data(self, df: pd.DataFrame, pair: str, timeframe: str) -> bool:
        """Validar calidad de datos Forex"""
        try:
            # Verificar columnas requeridas
            required_columns = ['timestamp', 'open', 'high', 'low', 'close']
            if not all(col in df.columns for col in required_columns):
                logger.error(f"❌ Columnas faltantes en datos de {pair}")
                return False

            # Verificar que hay datos
            if len(df) == 0:
                logger.error(f"❌ DataFrame vacío para {pair}")
                return False

            # Verificar valores válidos
            numeric_cols = ['open', 'high', 'low', 'close']
            for col in numeric_cols:
                if df[col].isna().all() or (df[col] <= 0).all():
                    logger.error(f"❌ Valores inválidos en columna {col} para {pair}")
                    return False

            # Verificar lógica OHLC
            invalid_ohlc = (
                    (df['high'] < df['low']) |
                    (df['high'] < df['open']) |
                    (df['high'] < df['close']) |
                    (df['low'] > df['open']) |
                    (df['low'] > df['close'])
            ).any()

            if invalid_ohlc:
                logger.warning(f"⚠️ Algunos registros OHLC inválidos para {pair}")
                # No rechazar completamente, solo advertir

            # Verificar timestamps
            if df['timestamp'].isna().any():
                logger.error(f"❌ Timestamps faltantes para {pair}")
                return False

            logger.debug(f"✅ Validación exitosa para {pair}: {len(df)} registros")
            return True

        except Exception as e:
            logger.error(f"❌ Error validando datos para {pair}: {e}")
            return False

    def get_multiple_pairs_data(self, pairs: List[str], timeframe: str, limit: int = 1000) -> Dict[str, pd.DataFrame]:
        """Obtener datos para múltiples pares"""
        results = {}

        logger.info(f"🔍 Obteniendo datos para {len(pairs)} pares en timeframe {timeframe}")

        for i, pair in enumerate(pairs):
            logger.info(f"📊 Procesando {pair} ({i + 1}/{len(pairs)})")

            try:
                df = self.get_forex_data(pair, timeframe, limit)
                if df is not None:
                    results[pair] = df
                else:
                    logger.warning(f"⚠️ No se pudieron obtener datos para {pair}")

                # Pequeña pausa entre requests para evitar rate limits
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"❌ Error procesando {pair}: {e}")
                continue

        logger.info(f"✅ Datos obtenidos para {len(results)}/{len(pairs)} pares")
        return results

    def clear_cache(self) -> None:
        """Limpiar cache"""
        self.cache.clear()
        logger.info("🗑️ Cache limpiado")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del cache"""
        return {
            'entries': len(self.cache),
            'keys': list(self.cache.keys()),
            'oldest_entry': min((entry['timestamp'] for entry in self.cache.values()), default=0),
            'newest_entry': max((entry['timestamp'] for entry in self.cache.values()), default=0)
        }


# Función de utilidad
def create_data_collector() -> ForexDataCollector:
    """Crear instancia del recolector de datos"""
    return ForexDataCollector()


# Test del recolector
if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)

    try:
        print("🔄 Probando recolector de datos...")
        collector = create_data_collector()

        # Test con un par específico
        test_pair = 'EURUSD'
        test_timeframe = '1d'

        print(f"📊 Obteniendo datos para {test_pair} {test_timeframe}...")
        df = collector.get_forex_data(test_pair, test_timeframe, limit=10)

        if df is not None:
            print(f"✅ Datos obtenidos: {len(df)} registros")
            print(f"📅 Rango: {df['timestamp'].min()} a {df['timestamp'].max()}")
            print(f"💹 Último precio: {df['close'].iloc[-1]:.5f}")
            print("\n📋 Primeros registros:")
            print(df.head())
        else:
            print("❌ No se pudieron obtener datos")

        # Estadísticas de cache
        cache_stats = collector.get_cache_stats()
        print(f"\n📋 Cache: {cache_stats}")

    except Exception as e:
        print(f"❌ Error: {e}")