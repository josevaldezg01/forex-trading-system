import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time

def check_yahoo_forex_data():
    """Verificar disponibilidad de datos forex en Yahoo Finance"""
    
    # Mapeo de pares forex para Yahoo Finance
    yahoo_symbols = {
        "EURUSD": "EURUSD=X",
        "GBPUSD": "GBPUSD=X", 
        "USDJPY": "USDJPY=X",
        "AUDUSD": "AUDUSD=X",
        "USDCAD": "USDCAD=X",
        "USDCHF": "USDCHF=X",
        "NZDUSD": "NZDUSD=X",
        "EURJPY": "EURJPY=X",
        "GBPJPY": "GBPJPY=X",
        "AUDJPY": "AUDJPY=X",
        "CADJPY": "CADJPY=X",
        "CHFJPY": "CHFJPY=X"
    }
    
    # Intervalos a verificar
    intervals_to_check = {
        "1min": "1m",
        "2min": "2m", 
        "5min": "5m",
        "15min": "15m",
        "30min": "30m",
        "1h": "1h"
    }
    
    print("VERIFICANDO DISPONIBILIDAD DE DATOS EN YAHOO FINANCE")
    print("=" * 80)
    print(f"Fecha de consulta: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Nota: Yahoo Finance usa nomenclatura =X para forex")
    print()
    
    results = {}
    
    for display_name, yahoo_symbol in yahoo_symbols.items():
        print(f"\n🔍 VERIFICANDO {display_name} ({yahoo_symbol})")
        print("-" * 60)
        
        results[display_name] = {'yahoo_symbol': yahoo_symbol}
        
        for interval_name, yahoo_interval in intervals_to_check.items():
            print(f"\n  📊 Timeframe {interval_name} ({yahoo_interval}):")
            
            try:
                # Crear ticker
                ticker = yf.Ticker(yahoo_symbol)
                
                # Definir período basado en el intervalo
                if yahoo_interval in ["1m", "2m", "5m"]:
                    period = "7d"  # Yahoo limita datos intraday a 7 días
                    max_days = 7
                elif yahoo_interval in ["15m", "30m"]:
                    period = "60d"  # 60 días para intervalos medianos
                    max_days = 60
                else:
                    period = "2y"  # 2 años para intervalos largos
                    max_days = 730
                
                print(f"    🔄 Descargando período {period}...")
                
                # Intentar descargar datos
                data = ticker.history(period=period, interval=yahoo_interval)
                
                if data.empty:
                    print(f"    ❌ Sin datos disponibles")
                    results[display_name][interval_name] = {
                        'status': 'no_data',
                        'message': 'Sin datos'
                    }
                else:
                    total_bars = len(data)
                    oldest_date = data.index.min()
                    newest_date = data.index.max()
                    days_span = (newest_date - oldest_date).days
                    
                    print(f"    ✅ {total_bars:,} barras obtenidas")
                    print(f"    📅 Desde: {oldest_date}")
                    print(f"    📅 Hasta: {newest_date}")
                    print(f"    📏 Período: {days_span} días")
                    
                    # Mostrar muestra de datos
                    sample = data.head(2)
                    print(f"    🔍 Muestra:")
                    for i, (timestamp, row) in enumerate(sample.iterrows()):
                        print(f"      {i+1}. {timestamp} | O:{row['Open']:.5f} H:{row['High']:.5f} L:{row['Low']:.5f} C:{row['Close']:.5f}")
                    
                    results[display_name][interval_name] = {
                        'status': 'available',
                        'total_bars': total_bars,
                        'oldest_date': oldest_date,
                        'newest_date': newest_date,
                        'days_span': days_span,
                        'max_days_allowed': max_days
                    }
                
                # Pausa para evitar rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                print(f"    ❌ Error: {e}")
                results[display_name][interval_name] = {
                    'status': 'error',
                    'message': str(e)
                }
    
    # Resumen final
    print(f"\n{'='*100}")
    print("RESUMEN DE DISPONIBILIDAD - YAHOO FINANCE")
    print("="*100)
    
    print(f"\n{'Par':<10} {'Símbolo':<12} {'1min':<20} {'5min':<20} {'15min':<20}")
    print("-" * 82)
    
    for display_name in yahoo_symbols.keys():
        if display_name in results:
            yahoo_symbol = results[display_name].get('yahoo_symbol', 'N/A')
            
            # Status para cada timeframe
            status_1min = format_status(results[display_name].get('1min', {}))
            status_5min = format_status(results[display_name].get('5min', {}))
            status_15min = format_status(results[display_name].get('15min', {}))
            
            print(f"{display_name:<10} {yahoo_symbol:<12} {status_1min:<20} {status_5min:<20} {status_15min:<20}")
    
    # Análisis comparativo
    print(f"\n{'='*100}")
    print("ANÁLISIS COMPARATIVO: YAHOO vs OANDA")
    print("="*100)
    
    available_1min_yahoo = []
    available_5min_yahoo = []
    
    for display_name in yahoo_symbols.keys():
        if display_name in results:
            if results[display_name].get('1min', {}).get('status') == 'available':
                bars = results[display_name]['1min']['total_bars']
                days = results[display_name]['1min']['days_span']
                available_1min_yahoo.append(f"{display_name} ({bars:,} barras, {days}d)")
            
            if results[display_name].get('5min', {}).get('status') == 'available':
                bars = results[display_name]['5min']['total_bars']
                days = results[display_name]['5min']['days_span']
                available_5min_yahoo.append(f"{display_name} ({bars:,} barras, {days}d)")
    
    print(f"\n📊 Resumen Yahoo Finance:")
    print(f"   - Pares con datos 1min: {len(available_1min_yahoo)}")
    print(f"   - Pares con datos 5min: {len(available_5min_yahoo)}")
    
    if available_1min_yahoo:
        print(f"\n✅ Yahoo Finance - Datos 1min disponibles:")
        for pair_info in available_1min_yahoo:
            print(f"   - {pair_info}")
    
    if available_5min_yahoo:
        print(f"\n✅ Yahoo Finance - Datos 5min disponibles:")
        for pair_info in available_5min_yahoo:
            print(f"   - {pair_info}")
    
    # Recomendaciones
    print(f"\n{'='*100}")
    print("RECOMENDACIONES")
    print("="*100)
    
    if available_1min_yahoo or available_5min_yahoo:
        print(f"\n✅ BUENAS NOTICIAS: Yahoo Finance SÍ tiene datos de timeframes cortos")
        print(f"\n💡 Opciones:")
        print(f"   1. Usar Yahoo Finance como fuente complementaria para 1min/5min")
        print(f"   2. Crear script híbrido: OANDA para 15min+ y Yahoo para 1min/5min")
        print(f"   3. Proceder solo con OANDA usando timeframes 15min+")
        
        print(f"\n⚠️  LIMITACIONES de Yahoo Finance:")
        print(f"   - Datos 1min/5min limitados a 7 días máximo")
        print(f"   - Rate limiting (necesita pausas entre requests)")
        print(f"   - Menos confiable para trading en tiempo real")
        
    else:
        print(f"\n⚠️  Yahoo Finance tampoco tiene datos suficientes para 1min/5min")
        print(f"\n✅ RECOMENDACIÓN FINAL:")
        print(f"   Proceder con análisis usando timeframes OANDA disponibles:")
        print(f"   - 15min: Excelente cobertura (~50k barras)")
        print(f"   - 30min, 1h, 4h, 1d: Datos históricos robustos")
    
    return results

def format_status(timeframe_data):
    """Formatear status de un timeframe"""
    if timeframe_data.get('status') == 'available':
        bars = timeframe_data.get('total_bars', 0)
        days = timeframe_data.get('days_span', 0)
        return f"✅ {bars:,} ({days}d)"
    else:
        return "❌ No disponible"

def main():
    print("🔍 VERIFICADOR DE DATOS YAHOO FINANCE")
    print("Este script consulta Yahoo Finance para verificar disponibilidad")
    print("de datos forex en timeframes cortos (1min, 5min)")
    print()
    
    # Verificar si yfinance está instalado
    try:
        import yfinance
        print("✅ yfinance está disponible")
    except ImportError:
        print("❌ yfinance no está instalado")
        print("Instalar con: pip install yfinance")
        return
    
    print("\n⚠️  NOTA: Yahoo Finance puede tener rate limiting")
    print("El script incluye pausas para evitar ser bloqueado")
    
    input("\nPresiona Enter para continuar...")
    
    try:
        results = check_yahoo_forex_data()
        print(f"\n✅ Verificación completada")
        
    except KeyboardInterrupt:
        print(f"\n\n⚠️ Verificación cancelada por el usuario")
    except Exception as e:
        print(f"\n❌ Error durante la verificación: {e}")

if __name__ == "__main__":
    main()