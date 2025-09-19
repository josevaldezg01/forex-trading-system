# backend/test_real_patterns.py
import os
import sys
import pandas as pd
from datetime import datetime
from pathlib import Path

# Agregar directorio padre al path
sys.path.append(str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    print(f"📄 Cargando .env desde: {env_path}")
except ImportError:
    print("⚠️ python-dotenv no instalado")

from supabase_client import create_supabase_client
from pattern_detector import create_pattern_detector

def test_real_data_patterns():
    """Prueba el detector de patrones con datos reales de Supabase"""
    
    print("🔌 Conectando a Supabase...")
    supabase = create_supabase_client()
    
    if not supabase:
        print("❌ No se pudo conectar a Supabase")
        return
    
    print("🧩 Inicializando Pattern Detector...")
    detector = create_pattern_detector()
    
    # Obtener datos reales de diferentes pares
    test_pairs = ['EURUSD', 'GBPUSD', 'USDJPY']
    test_timeframes = ['1h', '1d']  # Solo los timeframes disponibles
    
    for pair in test_pairs:
        for timeframe in test_timeframes:
            print(f"\n🔍 Analizando {pair} {timeframe}...")
            
            try:
                # Verificar si tu supabase_client tiene método específico
                if hasattr(supabase, 'get_forex_data'):
                    # Usar método personalizado si existe
                    data = supabase.get_forex_data(pair, timeframe, limit=2000)
                    df = pd.DataFrame(data) if data else pd.DataFrame()
                
                elif hasattr(supabase, 'client') and supabase.client:
                    # Usar cliente de Supabase estándar
                    response = supabase.client.table('forex_candles').select('*').eq('pair', pair).eq('timeframe', timeframe).order('datetime', desc=False).limit(2000).execute()
                    df = pd.DataFrame(response.data) if response.data else pd.DataFrame()
                
                else:
                    # Intentar métodos alternativos
                    print(f"🔍 Explorando métodos disponibles en supabase:")
                    available_methods = [method for method in dir(supabase) if not method.startswith('_')]
                    print(f"   Métodos disponibles: {available_methods}")
                    
                    # Intentar método directo de consulta
                    if hasattr(supabase, 'query'):
                        query = f"SELECT * FROM forex_candles WHERE pair = '{pair}' AND timeframe = '{timeframe}' ORDER BY datetime ASC LIMIT 2000"
                        result = supabase.query(query)
                        df = pd.DataFrame(result) if result else pd.DataFrame()
                    else:
                        print(f"⚠️ No se encontró método para consultar datos")
                        continue
                
                if df.empty:
                    print(f"⚠️ No hay datos para {pair} {timeframe}")
                    continue
                
                print(f"📊 Datos obtenidos: {len(df)} velas")
                
                # Verificar estructura
                print(f"📋 Columnas: {df.columns.tolist()}")
                
                if len(df) > 0:
                    print(f"📅 Rango fechas: {df['datetime'].iloc[0]} → {df['datetime'].iloc[-1]}")
                
                # Verificar datos OHLC
                required_cols = ['open', 'high', 'low', 'close']
                missing_cols = [col for col in required_cols if col not in df.columns]
                
                if missing_cols:
                    print(f"❌ Faltan columnas: {missing_cols}")
                    continue
                
                # Mostrar muestra de datos
                print(f"📈 Muestra de datos:")
                print(df[['datetime', 'open', 'high', 'low', 'close']].head(3))
                
                # Detectar patrones
                print(f"🔍 Detectando patrones...")
                patterns = detector.detect_patterns(pair, timeframe, df)
                
                if patterns:
                    print(f"✅ Encontrados {len(patterns)} patrones válidos")
                    
                    # Mostrar mejores patrones
                    print(f"\n🏆 Top 5 patrones para {pair} {timeframe}:")
                    for i, pattern in enumerate(patterns[:5], 1):
                        print(f"{i}. {pattern['pattern']} → {pattern['predicted_candle']}: {pattern['effectiveness']:.1f}% ({pattern['occurrences']} veces, score: {pattern['score']:.1f})")
                    
                    # Estadísticas generales
                    stats = detector.get_pattern_statistics(patterns)
                    print(f"\n📊 Estadísticas {pair} {timeframe}:")
                    print(f"   Efectividad promedio: {stats.get('avg_effectiveness', 0):.1f}%")
                    print(f"   Score promedio: {stats.get('avg_score', 0):.1f}")
                    print(f"   Rango efectividad: {stats.get('min_effectiveness', 0):.1f}% - {stats.get('max_effectiveness', 0):.1f}%")
                    print(f"   Total ocurrencias: {stats.get('total_occurrences', 0)}")
                    
                    # Simulación rápida
                    simulation = detector.simulate_trading_performance(patterns[:3])  # Solo top 3
                    if 'error' not in simulation:
                        print(f"\n💰 Simulación Trading (Top 3 patrones):")
                        print(f"   Retorno estimado: {simulation['total_return']:.1f}%")
                        print(f"   Win rate: {simulation['win_rate']:.1f}%")
                        print(f"   Trades simulados: {simulation['total_trades']}")
                
                else:
                    print(f"ℹ️ No se encontraron patrones válidos para {pair} {timeframe}")
                
            except Exception as e:
                print(f"❌ Error analizando {pair} {timeframe}: {e}")
                import traceback
                traceback.print_exc()
    
    print(f"\n🎯 Análisis de datos reales completado")

def debug_supabase_client():
    """Debug para entender la estructura del cliente Supabase"""
    print("\n🔍 Analizando estructura del cliente Supabase...")
    
    try:
        supabase = create_supabase_client()
        
        print(f"📊 Tipo de objeto: {type(supabase)}")
        print(f"📋 Métodos disponibles:")
        
        methods = []
        for attr_name in dir(supabase):
            if not attr_name.startswith('_'):
                attr = getattr(supabase, attr_name)
                if callable(attr):
                    methods.append(f"   🔧 {attr_name}()")
                else:
                    methods.append(f"   📄 {attr_name} = {type(attr).__name__}")
        
        for method in methods[:20]:  # Mostrar primeros 20
            print(method)
        
        if len(methods) > 20:
            print(f"   ... y {len(methods) - 20} más")
        
        # Intentar test de conexión si existe
        if hasattr(supabase, 'test_connection'):
            print(f"\n🧪 Probando conexión...")
            result = supabase.test_connection()
            print(f"   Resultado: {result}")
        
    except Exception as e:
        print(f"❌ Error analizando cliente: {e}")

if __name__ == "__main__":
    print("🧪 Iniciando análisis de patrones con datos reales...")
    
    # Primero debuggear el cliente
    debug_supabase_client()
    
    # Luego probar el análisis
    test_real_data_patterns()