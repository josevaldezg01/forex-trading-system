# test_real_data.py
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

def test_complete_system():
    """Probar sistema completo con datos reales"""
    try:
        print("🚀 Probando sistema completo con datos reales...")
        
        # Crear componentes
        collector = create_data_collector()
        detector = create_pattern_detector()
        
        # Pares para probar (empezar con pocos)
        test_pairs = ['EURUSD', 'GBPUSD', 'USDJPY']
        timeframe = '1d'
        
        print(f"📊 Obteniendo datos para {len(test_pairs)} pares...")
        
        all_patterns = []
        
        for pair in test_pairs:
            print(f"\n🔍 Procesando {pair}...")
            
            # Obtener datos reales
            df = collector.get_forex_data(pair, timeframe, limit=500)
            
            if df is not None and len(df) > 50:
                print(f"✅ {pair}: {len(df)} registros obtenidos")
                print(f"📅 Rango: {df['timestamp'].min().date()} a {df['timestamp'].max().date()}")
                print(f"💹 Último precio: {df['close'].iloc[-1]:.5f}")
                
                # Buscar patrones
                print(f"🔍 Buscando patrones en {pair}...")
                patterns = detector.find_patterns(df, pair, timeframe)
                
                if patterns:
                    print(f"✅ {pair}: {len(patterns)} patrones encontrados")
                    all_patterns.extend(patterns)
                    
                    # Mostrar mejores patrones
                    for i, pattern in enumerate(patterns[:3]):
                        print(f"   {i+1}. {pattern['pattern']}: {pattern['effectiveness']:.1f}% "
                              f"({pattern['occurrences']} ocurrencias, score: {pattern['score']:.1f})")
                else:
                    print(f"ℹ️ {pair}: No se encontraron patrones válidos")
                    
                    # Debug: intentar con filtros más permisivos
                    print(f"🔍 Debug para {pair}:")
                    sequence = detector._get_candle_sequence(df)
                    if sequence:
                        print(f"   Secuencia: {''.join(sequence[-20:])}...")  # Últimas 20 velas
                        
                        # Reducir temporalmente los filtros
                        original_min_occ = detector.min_occurrences
                        detector.min_occurrences = 5
                        
                        raw_patterns = detector._find_sequence_patterns(sequence, pair, timeframe)
                        print(f"   Patrones brutos: {len(raw_patterns)}")
                        
                        if raw_patterns:
                            for rp in raw_patterns[:2]:
                                print(f"   - {rp['pattern']}: {rp['effectiveness']:.1f}% ({rp['occurrences']} occ)")
                        
                        # Restaurar filtro original
                        detector.min_occurrences = original_min_occ
            else:
                print(f"❌ {pair}: No se pudieron obtener datos suficientes")
        
        # Resumen final
        print(f"\n🎉 RESUMEN FINAL:")
        print(f"✅ Patrones válidos encontrados: {len(all_patterns)}")
        
        if all_patterns:
            # Agrupar por tipo de patrón
            pattern_counts = {}
            for p in all_patterns:
                pattern_type = p['pattern']
                pattern_counts[pattern_type] = pattern_counts.get(pattern_type, 0) + 1
            
            print(f"📊 Por tipo de patrón:")
            for pattern_type, count in pattern_counts.items():
                print(f"   {pattern_type}: {count} estrategias")
            
            # Top 5 mejores estrategias
            top_patterns = sorted(all_patterns, key=lambda x: x['score'], reverse=True)[:5]
            print(f"\n🏆 TOP 5 MEJORES ESTRATEGIAS:")
            for i, pattern in enumerate(top_patterns):
                print(f"   {i+1}. {pattern['pair']} {pattern['pattern']}: "
                      f"{pattern['effectiveness']:.1f}% efectividad, "
                      f"{pattern['occurrences']} ocurrencias, "
                      f"score: {pattern['score']:.1f}")
            
            # Estadísticas generales
            stats = detector.get_pattern_statistics(all_patterns)
            print(f"\n📈 ESTADÍSTICAS:")
            print(f"   Efectividad promedio: {stats.get('avg_effectiveness', 0):.1f}%")
            print(f"   Score promedio: {stats.get('avg_score', 0):.1f}")
            print(f"   Total ocurrencias: {stats.get('total_occurrences', 0)}")
            
            # Distribución por dirección
            directions = stats.get('by_direction', {})
            print(f"   Direcciones: PUT: {directions.get('PUT', 0)}, CALL: {directions.get('CALL', 0)}")
            
        else:
            print("ℹ️ No se encontraron patrones que cumplan los criterios de calidad.")
            print("💡 Esto puede ser normal con datos limitados o filtros estrictos.")
        
        return all_patterns
        
    except Exception as e:
        logger.error(f"❌ Error en test completo: {e}")
        return []

if __name__ == "__main__":
    patterns = test_complete_system()