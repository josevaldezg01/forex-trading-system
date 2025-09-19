# backend/insert_additional_strategies.py
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

from supabase_client import create_supabase_client

def insert_additional_strategies_to_master():
    """Insertar las 100 estrategias adicionales generadas al master"""
    
    print("Insertando estrategias adicionales al master...")
    supabase = create_supabase_client()
    
    # Generar estrategias adicionales
    additional_strategies = generate_additional_strategies()
    
    try:
        print(f"Insertando {len(additional_strategies)} estrategias adicionales...")
        
        # Insertar en lotes para evitar errores
        batch_size = 25
        inserted_total = 0
        
        for i in range(0, len(additional_strategies), batch_size):
            batch = additional_strategies[i:i + batch_size]
            
            try:
                insert_response = supabase.client.table('forex_strategies_master').insert(batch).execute()
                
                if insert_response.data:
                    inserted_total += len(insert_response.data)
                    print(f"   Lote {i//batch_size + 1}: {len(insert_response.data)} estrategias insertadas")
                else:
                    print(f"   Error en lote {i//batch_size + 1}")
                    
            except Exception as e:
                print(f"   Error insertando lote {i//batch_size + 1}: {e}")
                # Continuar con el siguiente lote
                continue
        
        # Verificar total final
        final_count = supabase.client.table('forex_strategies_master').select('id').execute()
        total_count = len(final_count.data) if final_count.data else 0
        
        print(f"\nRESUMEN:")
        print(f"Estrategias insertadas: {inserted_total}")
        print(f"Total en master: {total_count}")
        
        # Mostrar resumen por tipo
        types_query = supabase.client.table('forex_strategies_master').select('strategy_type').execute()
        if types_query.data:
            type_counts = {}
            for record in types_query.data:
                strategy_type = record['strategy_type']
                type_counts[strategy_type] = type_counts.get(strategy_type, 0) + 1
            
            print("\nEstrategias por tipo:")
            for strategy_type, count in type_counts.items():
                print(f"  {strategy_type}: {count}")
        
    except Exception as e:
        print(f"Error general: {e}")

def generate_additional_strategies():
    """Generar estrategias adicionales para el repositorio master"""
    
    additional_strategies = []
    
    # Patrones simples y complejos
    simple_patterns = ['R', 'V', 'RR', 'VV']
    complex_patterns = ['RRV', 'VVR', 'RRVR', 'VVRV', 'RVRR', 'VRVV', 'RRRVV', 'VVVRR']
    
    # Pares adicionales
    additional_pairs = ['EURGBP', 'EURJPY', 'GBPJPY', 'CHFJPY', 'CADCHF']
    
    current_time = datetime.now(timezone.utc).isoformat()
    analysis_date = datetime.now(timezone.utc).date().isoformat()
    
    for pair in additional_pairs:
        for pattern in simple_patterns + complex_patterns:
            for direction in ['CALL', 'PUT']:
                
                # Generar datos simulados realistas
                base_hash = hash(f"{pair}{pattern}{direction}")
                effectiveness = 50 + (base_hash % 25)  # 50-75%
                occurrences = 20 + (abs(base_hash) % 80)  # 20-100
                wins = int(occurrences * effectiveness / 100)
                losses = occurrences - wins
                score = 40 + (effectiveness - 50) * 0.8  # 40-60
                
                strategy = {
                    'pair': pair,
                    'timeframe': '1h',
                    'pattern': pattern,
                    'direction': direction,
                    'effectiveness': effectiveness,
                    'occurrences': occurrences,
                    'wins': wins,
                    'losses': losses,
                    'avg_profit': 55.0 + (effectiveness - 50) * 0.6,
                    'score': score,
                    'trigger_condition': f"After {len(pattern)} consecutive {pattern} candles",
                    'analysis_date': analysis_date,
                    'created_at': current_time,
                    
                    # Campos master
                    'strategy_type': 'generated_simulation',
                    'source': 'pattern_generator',
                    'validation_method': 'mathematical_simulation',
                    'data_quality': 'medium',
                    'is_active': False,
                    'added_to_master': current_time
                }
                
                additional_strategies.append(strategy)
    
    return additional_strategies

if __name__ == "__main__":
    insert_additional_strategies_to_master()