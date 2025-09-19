# backend/minimal_working_patterns.py
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

def save_minimal_working_patterns():
    """Guardar usando solo las columnas básicas que definitivamente existen"""
    
    print("Guardando estrategias con columnas basicas...")
    supabase = create_supabase_client()
    
    # Solo las mejores estrategias
    top_patterns = [
        {'pair': 'USDJPY', 'timeframe': '1h', 'pattern': 'RRRRR', 'direction': 'CALL', 'effectiveness': 91.7, 'occurrences': 12, 'score': 73.3, 'wins': 11, 'losses': 1},
        {'pair': 'USDJPY', 'timeframe': '1h', 'pattern': 'RRRR', 'direction': 'CALL', 'effectiveness': 67.6, 'occurrences': 37, 'score': 58.6, 'wins': 25, 'losses': 12},
        {'pair': 'EURUSD', 'timeframe': '1h', 'pattern': 'RRRR', 'direction': 'CALL', 'effectiveness': 67.4, 'occurrences': 46, 'score': 58.5, 'wins': 31, 'losses': 15},
        {'pair': 'USDJPY', 'timeframe': '1h', 'pattern': 'RVRV', 'direction': 'CALL', 'effectiveness': 61.3, 'occurrences': 62, 'score': 55.3, 'wins': 38, 'losses': 24},
        {'pair': 'GBPUSD', 'timeframe': '1h', 'pattern': 'VRV', 'direction': 'CALL', 'effectiveness': 58.9, 'occurrences': 112, 'score': 55.5, 'wins': 66, 'losses': 46}
    ]
    
    try:
        current_time = datetime.now(timezone.utc).isoformat()
        
        # Preparar solo con columnas basicas
        for pattern in top_patterns:
            strategy_data = {
                'pair': pattern['pair'],
                'timeframe': pattern['timeframe'],
                'pattern': pattern['pattern'],
                'direction': pattern['direction'],
                'effectiveness': pattern['effectiveness'],
                'occurrences': pattern['occurrences'],
                'wins': pattern['wins'],
                'losses': pattern['losses'],
                'score': pattern['score'],
                'created_at': current_time,
                'updated_at': current_time
            }
            
            # Insertar uno por uno para identificar problemas
            try:
                insert_response = supabase.client.table('forex_strategies').insert(strategy_data).execute()
                if insert_response.data:
                    print(f"OK: {pattern['pair']} {pattern['pattern']} insertado")
                else:
                    print(f"FALLO: {pattern['pair']} {pattern['pattern']}")
            except Exception as e:
                print(f"ERROR en {pattern['pair']} {pattern['pattern']}: {e}")
        
        print("\nVerificando estrategias guardadas...")
        verify_response = supabase.client.table('forex_strategies').select('*').limit(10).execute()
        if verify_response.data:
            print(f"Total estrategias en DB: {len(verify_response.data)}")
            for strategy in verify_response.data[:3]:
                print(f"  {strategy['pair']} {strategy['pattern']} -> {strategy['direction']} ({strategy['effectiveness']}%)")
        
    except Exception as e:
        print(f"ERROR GENERAL: {e}")

if __name__ == "__main__":
    save_minimal_working_patterns()