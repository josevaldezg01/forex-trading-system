import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import logging

# Configuración MT5
MT5_LOGIN = 7030106
MT5_PASSWORD = "Taliana123*"
MT5_SERVER = "OANDA-Live-1"

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def connect_mt5():
    """Conectar a MetaTrader 5"""
    try:
        if not mt5.initialize():
            logger.error("Error inicializando MT5")
            return False
            
        account_info = mt5.account_info()
        if account_info is None:
            logger.error("Error obteniendo info de cuenta")
            return False
            
        if not mt5.login(MT5_LOGIN, MT5_PASSWORD, MT5_SERVER):
            logger.error(f"Error conectando: {mt5.last_error()}")
            return False
            
        logger.info(f"Conectado a MT5 - Cuenta: {account_info.login}, Servidor: {account_info.server}")
        return True
        
    except Exception as e:
        logger.error(f"Excepción conectando a MT5: {e}")
        return False

def check_symbol_availability(symbol):
    """Verificar si el símbolo está disponible en MT5"""
    try:
        print(f"      🔍 Verificando símbolo: {symbol}")
        
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"      ❌ symbol_info() retornó None para {symbol}")
            return False, "Símbolo no encontrado"
        
        print(f"      ✅ Símbolo encontrado: {symbol}")
        print(f"         - Visible: {symbol_info.visible}")
        print(f"         - Spread: {symbol_info.spread}")
        print(f"         - Point: {symbol_info.point}")
        
        if not symbol_info.visible:
            print(f"      🔄 Intentando hacer visible el símbolo...")
            if not mt5.symbol_select(symbol, True):
                error = mt5.last_error()
                print(f"      ❌ No se puede hacer visible. Error: {error}")
                return False, f"No se puede hacer visible. Error: {error}"
            print(f"      ✅ Símbolo ahora es visible")
        
        return True, "Disponible"
    except Exception as e:
        print(f"      ❌ Excepción verificando símbolo: {e}")
        return False, f"Error: {e}"

def get_data_range_for_timeframe(symbol, timeframe, max_bars=50000):
    """Obtener el rango de datos disponibles para un símbolo y timeframe"""
    try:
        print(f"    🔍 Intentando obtener datos para {symbol} timeframe {timeframe}...")
        
        # Método 1: Intentar con copy_rates_range (más específico)
        from_date = datetime.now() - timedelta(days=365*2)  # 2 años atrás
        to_date = datetime.now()
        
        rates = mt5.copy_rates_range(symbol, timeframe, from_date, to_date)
        
        if rates is None or len(rates) == 0:
            print(f"    ⚠️ copy_rates_range falló, intentando copy_rates...")
            
            # Método 2: Intentar con copy_rates (obtener las últimas barras)
            rates = mt5.copy_rates(symbol, timeframe, max_bars)
            
            if rates is None or len(rates) == 0:
                print(f"    ⚠️ copy_rates también falló, intentando copy_rates_from...")
                
                # Método 3: Intentar con copy_rates_from
                rates = mt5.copy_rates_from(symbol, timeframe, from_date, max_bars)
                
                if rates is None or len(rates) == 0:
                    error_code = mt5.last_error()
                    return None, f"Sin datos disponibles. Error MT5: {error_code}"
        
        print(f"    ✅ Obtenidos {len(rates)} registros")
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        return {
            'total_bars': len(df),
            'oldest_date': df['time'].min(),
            'newest_date': df['time'].max(),
            'days_span': (df['time'].max() - df['time'].min()).days,
            'sample_data': df.head(2).to_dict('records')
        }, "OK"
        
    except Exception as e:
        return None, f"Error obteniendo datos: {e}"

def check_mt5_data_availability():
    """Verificar disponibilidad de datos en MT5 para timeframes específicos"""
    
    if not connect_mt5():
        print("❌ No se pudo conectar a MT5")
        return
    
    # Pares con nomenclatura OANDA (.sml para algunos)
    pairs_mapping = {
        "AUDJPY": "AUDJPY.sml",
        "AUDUSD": "AUDUSD.sml", 
        "CADJPY": "CADJPY.sml",
        "CHFJPY": "CHFJPY.sml",
        "EURJPY": "EURJPY.sml",
        "EURUSD": "EURUSD.sml",
        "GBPJPY": "GBPJPY.sml",
        "GBPUSD": "GBPUSD.sml",
        "NZDUSD": "NZDUSD.sml",
        "USDCAD": "USDCAD.sml",
        "USDCHF": "USDCHF.sml",
        "USDJPY": "USDJPY.sml"
    }
    
    # Timeframes de interés (MT5 format) - agregamos 15min como control
    timeframes_to_check = {
        "1min": mt5.TIMEFRAME_M1,
        "5min": mt5.TIMEFRAME_M5,
        "15min": mt5.TIMEFRAME_M15  # Agregado como control
    }
    
    print("VERIFICANDO DISPONIBILIDAD DE DATOS EN MT5 (OANDA)")
    print("=" * 80)
    print(f"Servidor: {MT5_SERVER}")
    print(f"Fecha de consulta: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Nota: Usando nomenclatura OANDA (.sml)")
    print()
    
    results = {}
    
    for display_name, mt5_symbol in pairs_mapping.items():
        print(f"\n🔍 VERIFICANDO {display_name} ({mt5_symbol})")
        print("-" * 60)
        
        # Verificar disponibilidad del símbolo
        available, status = check_symbol_availability(mt5_symbol)
        if not available:
            print(f"  ❌ Símbolo no disponible: {status}")
            
            # Intentar también sin .sml
            alternative_symbol = display_name
            print(f"  🔄 Intentando {alternative_symbol}...")
            available_alt, status_alt = check_symbol_availability(alternative_symbol)
            
            if not available_alt:
                print(f"  ❌ Tampoco disponible sin .sml: {status_alt}")
                continue
            else:
                print(f"  ✅ Disponible como {alternative_symbol}")
                mt5_symbol = alternative_symbol
        else:
            print(f"  ✅ Símbolo disponible como {mt5_symbol}")
            
        results[display_name] = {'mt5_symbol': mt5_symbol}
        
        for tf_name, tf_mt5 in timeframes_to_check.items():
            print(f"\n  📊 Timeframe {tf_name}:")
            
            data_info, error = get_data_range_for_timeframe(mt5_symbol, tf_mt5)
            
            if data_info is None:
                print(f"    ❌ {error}")
                results[display_name][tf_name] = {'status': 'error', 'message': error}
            else:
                print(f"    ✅ {data_info['total_bars']:,} barras disponibles")
                print(f"    📅 Desde: {data_info['oldest_date']}")
                print(f"    📅 Hasta: {data_info['newest_date']}")
                print(f"    📏 Período: {data_info['days_span']} días")
                
                # Mostrar muestra de datos
                if data_info['sample_data']:
                    print(f"    🔍 Muestra de datos:")
                    for i, sample in enumerate(data_info['sample_data'][:2]):
                        print(f"      {i+1}. {sample['time']} | O:{sample['open']} H:{sample['high']} L:{sample['low']} C:{sample['close']}")
                
                results[display_name][tf_name] = {
                    'status': 'available',
                    'total_bars': data_info['total_bars'],
                    'oldest_date': data_info['oldest_date'],
                    'newest_date': data_info['newest_date'],
                    'days_span': data_info['days_span']
                }
    
    # Resumen final
    print(f"\n{'='*80}")
    print("RESUMEN DE DISPONIBILIDAD")
    print("="*80)
    
    print(f"\n{'Par':<10} {'Símbolo MT5':<15} {'1min':<25} {'5min':<25} {'15min':<25}")
    print("-" * 105)
    
    for display_name in pairs_mapping.keys():
        if display_name in results:
            mt5_symbol = results[display_name].get('mt5_symbol', 'N/A')
            
            # Status 1min
            if results[display_name].get('1min', {}).get('status') == 'available':
                bars_1min = results[display_name]['1min']['total_bars']
                days_1min = results[display_name]['1min']['days_span']
                status_1min = f"✅ {bars_1min:,} barras ({days_1min}d)"
            else:
                status_1min = "❌ No disponible"
            
            # Status 5min
            if results[display_name].get('5min', {}).get('status') == 'available':
                bars_5min = results[display_name]['5min']['total_bars']
                days_5min = results[display_name]['5min']['days_span']
                status_5min = f"✅ {bars_5min:,} barras ({days_5min}d)"
            else:
                status_5min = "❌ No disponible"
            
            # Status 15min (control)
            if results[display_name].get('15min', {}).get('status') == 'available':
                bars_15min = results[display_name]['15min']['total_bars']
                days_15min = results[display_name]['15min']['days_span']
                status_15min = f"✅ {bars_15min:,} barras ({days_15min}d)"
            else:
                status_15min = "❌ No disponible"
            
            print(f"{display_name:<10} {mt5_symbol:<15} {status_1min:<25} {status_5min:<25} {status_15min:<25}")
        else:
            print(f"{display_name:<10} {'N/A':<15} {'❌ Símbolo no encontrado':<25} {'❌ Símbolo no encontrado':<25} {'❌ Símbolo no encontrado':<25}")
    
    # Análisis y recomendaciones
    print(f"\n{'='*80}")
    print("ANÁLISIS Y RECOMENDACIONES")
    print("="*80)
    
    available_pairs = []
    good_1min = []
    good_5min = []
    good_15min = []  # Agregado para control
    
    for display_name in pairs_mapping.keys():
        if display_name in results:
            available_pairs.append(display_name)
            
            # Verificar si tiene buenos datos 1min
            if results[display_name].get('1min', {}).get('status') == 'available':
                bars = results[display_name]['1min']['total_bars']
                days = results[display_name]['1min']['days_span']
                if bars > 10000 and days > 30:
                    good_1min.append(f"{display_name} ({bars:,} barras, {days} días)")
            
            # Verificar si tiene buenos datos 5min
            if results[display_name].get('5min', {}).get('status') == 'available':
                bars = results[display_name]['5min']['total_bars']
                days = results[display_name]['5min']['days_span']
                if bars > 5000 and days > 30:
                    good_5min.append(f"{display_name} ({bars:,} barras, {days} días)")
            
            # Verificar si tiene buenos datos 15min (control)
            if results[display_name].get('15min', {}).get('status') == 'available':
                bars = results[display_name]['15min']['total_bars']
                days = results[display_name]['15min']['days_span']
                if bars > 3000 and days > 30:
                    good_15min.append(f"{display_name} ({bars:,} barras, {days} días)")
    
    print(f"\n📊 Resumen:")
    print(f"   - Pares conectados exitosamente: {len(available_pairs)}")
    print(f"   - Pares con buenos datos 1min: {len(good_1min)}")
    print(f"   - Pares con buenos datos 5min: {len(good_5min)}")
    print(f"   - Pares con buenos datos 15min: {len(good_15min)} (control)")
    
    if good_1min:
        print(f"\n✅ Pares recomendados para descarga 1min:")
        for pair_info in good_1min:
            print(f"   - {pair_info}")
    
    if good_5min:
        print(f"\n✅ Pares recomendados para descarga 5min:")
        for pair_info in good_5min:
            print(f"   - {pair_info}")
    
    if good_15min:
        print(f"\n✅ Control - Pares con buenos datos 15min (debería coincidir con tu BD):")
        for pair_info in good_15min:
            print(f"   - {pair_info}")
    
    if not good_1min and not good_5min:
        print(f"\n⚠️  CONCLUSIÓN: OANDA parece tener datos limitados para 1min y 5min")
        print(f"   Recomendación: Proceder con análisis usando timeframes disponibles:")
        print(f"   - 15min: Excelente cobertura (como confirma el control)")
        print(f"   - 30min: Excelente cobertura") 
        print(f"   - 1h: Excelente cobertura")
        print(f"   - 4h+: Datos históricos extensos")
    else:
        print(f"\n💡 Siguiente paso: Actualizar mt5_data_downloader.py con:")
        print(f"   - Usar nomenclatura .sml para los símbolos")
        print(f"   - Descargar más historia para los pares con datos disponibles")
        print(f"   - Ampliar el rango de fechas en la descarga")
    
    mt5.shutdown()
    return results

if __name__ == "__main__":
    print("🔍 VERIFICADOR DE DISPONIBILIDAD DE DATOS MT5")
    print("Este script consulta directamente MT5 para ver qué datos")
    print("están disponibles para timeframes 1min y 5min")
    print()
    
    input("Presiona Enter para continuar...")
    
    try:
        results = check_mt5_data_availability()
    except KeyboardInterrupt:
        print("\n\n⚠️ Verificación cancelada por el usuario")
    except Exception as e:
        print(f"\n❌ Error durante la verificación: {e}")
    finally:
        mt5.shutdown()