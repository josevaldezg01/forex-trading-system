# backend/fix_strategy_updates.py
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass

from forex_analyzer import ForexAnalyzer

def fix_and_run_analysis():
    """Corregir y ejecutar análisis que SÍ actualice forex_strategies"""
    
    print("Ejecutando análisis que actualizará forex_strategies...")
    
    analyzer = ForexAnalyzer()
    
    # Obtener datos antes
    before_active = analyzer.db_client.client.table('forex_strategies').select('id').execute()
    before_master = analyzer.db_client.client.table('forex_strategies_master').select('id').execute()
    
    before_active_count = len(before_active.data) if before_active.data else 0
    before_master_count = len(before_master.data) if before_master.data else 0
    
    print(f"ANTES:")
    print(f"  forex_strategies (activas): {before_active_count}")
    print(f"  forex_strategies_master: {before_master_count}")
    
    # Ejecutar análisis manual para un par específico
    test_pair = 'EURUSD'
    test_timeframe = '1h'
    
    print(f"\nAnalizando {test_pair} {test_timeframe} manualmente...")
    
    # Obtener datos
    historical_data = analyzer.data_collector.get_forex_data(test_pair, test_timeframe)
    
    if historical_data is not None and not historical_data.empty:
        print(f"Datos obtenidos: {len(historical_data)} velas")
        
        # Detectar patrones
        patterns = analyzer.pattern_detector.detect_and_update_patterns(test_pair, test_timeframe, historical_data)
        
        print(f"Patrones detectados: {len(patterns)}")
        
        if patterns:
            # Forzar inserción en forex_strategies
            print("Insertando patrones en forex_strategies...")
            
            current_time = datetime.now(timezone.utc).isoformat()
            
            for pattern in patterns[:5]:  # Solo top 5 para prueba
                strategy_data = {
                    'pair': pattern['pair'],
                    'timeframe': pattern['timeframe'],
                    'pattern': pattern['pattern'],
                    'direction': pattern['direction'],
                    'effectiveness': pattern['effectiveness'],
                    'occurrences': pattern['occurrences'],
                    'wins': pattern.get('wins', 0),
                    'losses': pattern.get('losses', 0),
                    'avg_profit': pattern.get('avg_profit', 65),
                    'score': pattern['score'],
                    'trigger_condition': f"After {len(pattern['pattern'])} consecutive {pattern['pattern']} candles",
                    'analysis_date': datetime.now(timezone.utc).date().isoformat(),
                    'created_at': current_time
                }
                
                try:
                    # Verificar si ya existe
                    existing = analyzer.db_client.client.table('forex_strategies').select('id').eq('pair', pattern['pair']).eq('timeframe', pattern['timeframe']).eq('pattern', pattern['pattern']).eq('direction', pattern['direction']).execute()
                    
                    if existing.data:
                        # Actualizar existente
                        update_result = analyzer.db_client.client.table('forex_strategies').update(strategy_data).eq('id', existing.data[0]['id']).execute()
                        print(f"  Actualizada: {pattern['pair']} {pattern['pattern']} → {pattern['direction']}")
                    else:
                        # Insertar nueva
                        insert_result = analyzer.db_client.client.table('forex_strategies').insert(strategy_data).execute()
                        print(f"  Insertada: {pattern['pair']} {pattern['pattern']} → {pattern['direction']} ({pattern['effectiveness']:.1f}%)")
                        
                except Exception as e:
                    print(f"  Error: {pattern['pair']} {pattern['pattern']}: {e}")
    
    # Verificar después
    after_active = analyzer.db_client.client.table('forex_strategies').select('id').execute()
    after_master = analyzer.db_client.client.table('forex_strategies_master').select('id').execute()
    
    after_active_count = len(after_active.data) if after_active.data else 0
    after_master_count = len(after_master.data) if after_master.data else 0
    
    print(f"\nDESPUÉS:")
    print(f"  forex_strategies (activas): {after_active_count} (+{after_active_count - before_active_count})")
    print(f"  forex_strategies_master: {after_master_count} (+{after_master_count - before_master_count})")
    
    # Mostrar algunas estrategias activas para verificar
    current_active = analyzer.db_client.client.table('forex_strategies').select('pair, pattern, direction, effectiveness, score').order('effectiveness', desc=True).limit(5).execute()
    
    if current_active.data:
        print(f"\nTop 5 estrategias ACTIVAS (las que ve tu dashboard):")
        for i, strategy in enumerate(current_active.data, 1):
            print(f"  {i}. {strategy['pair']} {strategy['pattern']} → {strategy['direction']}: {strategy['effectiveness']:.1f}% (Score: {strategy['score']:.1f})")
    
    print(f"\nAhora tu dashboard debería mostrar estas estrategias actualizadas.")

if __name__ == "__main__":
    fix_and_run_analysis()