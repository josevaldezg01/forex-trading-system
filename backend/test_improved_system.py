# test_improved_system.py
import logging
from pathlib import Path

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass

from data_collector import create_data_collector
from pattern_detector import create_pattern_detector

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_improved_patterns():
    """Probar sistema mejorado con datos más extensos"""
    try:
        print("🚀 Probando sistema mejorado con datos históricos...")
        
        # Crear componentes
        collector = create_data_collector()
        detector = create_pattern_detector()
        
        # Probar con un solo par primero para verificar
        test_pair = 'EURUSD'
        timeframe = '1d'
        
        print(f"📊 Obteniendo datos históricos extensos para {test_pair}...")
        
        # Obtener más datos históricos (2 años si es posible)
        df = collector.get_forex_data(test_pair, timeframe, limit=800)
        
        if df is not None and len(df) > 200:
            print(f"✅ {test_pair}: {len(df)} registros obtenidos")
            print(f"📅 Rango: {df['timestamp'].min().date()} a {df['timestamp'].max().date()}")
            
            # Mostrar distribución de velas
            sequence = detector._get_candle_sequence(df)
            if sequence:
                red_count = sequence.count('R')
                green_count = sequence.count('V')
                total = len(sequence)
                
                print(f"🕯️ Distribución de velas:")
                print(f"   Rojas (R): {red_count} ({red_count/total*100:.1f}%)")
                print(f"   Verdes (V): {green_count} ({green_count/total*100:.1f}%)")
                print(f"   Secuencia reciente: {''.join(sequence[-30:])}")
            
            # Buscar patrones con sistema mejorado
            print(f"\n🔍 Buscando patrones mejorados...")
            patterns = detector.find_patterns(df, test_pair, timeframe)
            
            if patterns:
                print(f"✅ Patrones encontrados: {len(patterns)}")
                
                for i, pattern in enumerate(patterns):
                    print(f"\n📈 Patrón {i+1}: {pattern['pattern']} → {pattern['predicted_candle']}")
                    print(f"   Par: {pattern['pair']}")
                    print(f"   Dirección: {pattern['direction']}")
                    print(f"   Efectividad: {pattern['effectiveness']:.1f}%")
                    print(f"   Ocurrencias: {pattern['occurrences']}")
                    print(f"   Wins/Losses: {pattern['wins']}/{pattern['losses']}")
                    print(f"   Score: {pattern['score']:.1f}")
                    print(f"   Ganancia promedio: {pattern['avg_profit']:.4f}%")
                
                # Estadísticas
                stats = detector.get_pattern_statistics(patterns)
                print(f"\n📊 ESTADÍSTICAS MEJORADAS:")
                print(f"   Efectividad promedio: {stats.get('avg_effectiveness', 0):.1f}%")
                print(f"   Score promedio: {stats.get('avg_score', 0):.1f}")
                print(f"   Total ocurrencias: {stats.get('total_occurrences', 0)}")
                
                # Distribución por dirección
                directions = stats.get('by_direction', {})
                print(f"   Distribución: PUT: {directions.get('PUT', 0)}, CALL: {directions.get('CALL', 0)}")
                
                # Distribución por tipo de patrón
                pattern_types = stats.get('by_pattern_type', {})
                print(f"   Por patrón: {dict(pattern_types)}")
                
            else:
                print("ℹ️ No se encontraron patrones que cumplan los criterios mejorados")
                
                # Debug detallado
                print("\n🔍 ANÁLISIS DETALLADO:")
                sequence = detector._get_candle_sequence(df)
                
                if sequence:
                    # Analizar patrones individuales
                    test_patterns = ['R', 'RR', 'RRR', 'V', 'VV', 'VVV']
                    
                    for test_pattern in test_patterns:
                        pattern_result = detector._analyze_pattern(sequence, test_pattern, test_pair, timeframe)
                        
                        if pattern_result:
                            print(f"   {test_pattern}: {pattern_result['effectiveness']:.1f}% "
                                  f"({pattern_result['occurrences']} occ, score: {pattern_result['score']:.1f})")
                        else:
                            # Contar manualmente
                            pattern_count = 0
                            for i in range(len(sequence) - len(test_pattern) + 1):
                                if ''.join(sequence[i:i + len(test_pattern)]) == test_pattern:
                                    pattern_count += 1
                            
                            if pattern_count > 0:
                                print(f"   {test_pattern}: {pattern_count} ocurrencias (no válido)")
        
        else:
            print(f"❌ No se pudieron obtener datos suficientes para {test_pair}")
        
        return patterns if 'patterns' in locals() else []
        
    except Exception as e:
        logger.error(f"❌ Error en test mejorado: {e}")
        return []

def test_multiple_pairs_improved():
    """Probar múltiples pares con sistema mejorado"""
    try:
        print("\n🌍 Probando múltiples pares con sistema mejorado...")
        
        collector = create_data_collector()
        detector = create_pattern_detector()
        
        test_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF']
        timeframe = '1d'
        all_patterns = []
        
        for pair in test_pairs:
            print(f"\n📊 Analizando {pair}...")
            
            df = collector.get_forex_data(pair, timeframe, limit=600)
            
            if df is not None and len(df) > 100:
                print(f"✅ {pair}: {len(df)} registros")
                
                patterns = detector.find_patterns(df, pair, timeframe)
                
                if patterns:
                    print(f"   🎯 {len(patterns)} patrones encontrados")
                    all_patterns.extend(patterns)
                    
                    # Mostrar mejor patrón
                    best = max(patterns, key=lambda x: x['score'])
                    print(f"   🏆 Mejor: {best['pattern']} → {best['predicted_candle']} "
                          f"({best['effectiveness']:.1f}%, score: {best['score']:.1f})")
                else:
                    print(f"   ℹ️ Sin patrones válidos")
        
        print(f"\n🎉 RESUMEN MULTI-PAR:")
        print(f"   Total patrones: {len(all_patterns)}")
        
        if all_patterns:
            # Top 10 mejores
            top_patterns = sorted(all_patterns, key=lambda x: x['score'], reverse=True)[:10]
            
            print(f"\n🏆 TOP 10 PATRONES:")
            for i, p in enumerate(top_patterns):
                print(f"   {i+1:2d}. {p['pair']} {p['pattern']} → {p['predicted_candle']}: "
                      f"{p['effectiveness']:5.1f}% ({p['occurrences']:3d} occ, score: {p['score']:5.1f})")
        
        return all_patterns
        
    except Exception as e:
        logger.error(f"❌ Error en test multi-par: {e}")
        return []

if __name__ == "__main__":
    # Test individual mejorado
    patterns = test_improved_patterns()
    
    # Test múltiple si el individual funcionó
    if patterns:
        all_patterns = test_multiple_pairs_improved()
    else:
        print("\n⚠️ Saltando test múltiple debido a problemas en test individual")