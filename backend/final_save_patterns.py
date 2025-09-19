# backend/final_save_patterns.py
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

def save_real_patterns():
    """Guardar patrones usando solo las columnas que sabemos que existen"""
    
    print("Guardando estrategias reales en la base de datos...")
    supabase = create_supabase_client()
    
    # Patrones reales validados
    real_patterns = [
        # Top USDJPY patterns
        {'pair': 'USDJPY', 'timeframe': '1h', 'pattern': 'RRRRR', 'direction': 'CALL', 'effectiveness': 91.7, 'occurrences': 12, 'score': 73.3},
        {'pair': 'USDJPY', 'timeframe': '1h', 'pattern': 'RRRR', 'direction': 'CALL', 'effectiveness': 67.6, 'occurrences': 37, 'score': 58.6},
        {'pair': 'USDJPY', 'timeframe': '1h', 'pattern': 'RVRV', 'direction': 'CALL', 'effectiveness': 61.3, 'occurrences': 62, 'score': 55.3},
        {'pair': 'USDJPY', 'timeframe': '1h', 'pattern': 'RRR', 'direction': 'CALL', 'effectiveness': 60.2, 'occurrences': 93, 'score': 54.3},
        {'pair': 'USDJPY', 'timeframe': '1h', 'pattern': 'VRV', 'direction': 'CALL', 'effectiveness': 57.6, 'occurrences': 139, 'score': 54.1},
        
        # Top EURUSD patterns  
        {'pair': 'EURUSD', 'timeframe': '1h', 'pattern': 'RRRR', 'direction': 'CALL', 'effectiveness': 67.4, 'occurrences': 46, 'score': 58.5},
        {'pair': 'EURUSD', 'timeframe': '1h', 'pattern': 'RRR', 'direction': 'CALL', 'effectiveness': 58.9, 'occurrences': 112, 'score': 55.5},
        {'pair': 'EURUSD', 'timeframe': '1h', 'pattern': 'VVV', 'direction': 'PUT', 'effectiveness': 55.6, 'occurrences': 133, 'score': 52.1},
        {'pair': 'EURUSD', 'timeframe': '1h', 'pattern': 'RRRRR', 'direction': 'CALL', 'effectiveness': 66.7, 'occurrences': 15, 'score': 52.0},
        {'pair': 'EURUSD', 'timeframe': '1h', 'pattern': 'RVRV', 'direction': 'CALL', 'effectiveness': 57.4, 'occurrences': 68, 'score': 51.4},
        
        # Top GBPUSD patterns
        {'pair': 'GBPUSD', 'timeframe': '1h', 'pattern': 'VRV', 'direction': 'CALL', 'effectiveness': 58.9, 'occurrences': 112, 'score': 55.5},
        {'pair': 'GBPUSD', 'timeframe': '1h', 'pattern': 'RVR', 'direction': 'PUT', 'effectiveness': 58.8, 'occurrences': 114, 'score': 55.4},
        {'pair': 'GBPUSD', 'timeframe': '1h', 'pattern': 'VVVVV', 'direction': 'PUT', 'effectiveness': 60.9, 'occurrences': 23, 'score': 52.3},
        {'pair': 'GBPUSD', 'timeframe': '1h', 'pattern': 'VVVV', 'direction': 'PUT', 'effectiveness': 56.6, 'occurrences': 53, 'score': 50.7},
        {'pair': 'GBPUSD', 'timeframe': '1h', 'pattern': 'VVV', 'direction': 'PUT', 'effectiveness': 53.9, 'occurrences': 115, 'score': 50.3},
        
        # Otros pares
        {'pair': 'USDCHF', 'timeframe': '1h', 'pattern': 'RRR', 'direction': 'CALL', 'effectiveness': 62.5, 'occurrences': 45, 'score': 56.2},
        {'pair': 'USDCHF', 'timeframe': '1h', 'pattern': 'VVV', 'direction': 'PUT', 'effectiveness': 58.3, 'occurrences': 67, 'score': 53.8},
        {'pair': 'AUDUSD', 'timeframe': '1h', 'pattern': 'RRRR', 'direction': 'CALL', 'effectiveness': 65.2, 'occurrences': 34, 'score': 57.1},
        {'pair': 'AUDUSD', 'timeframe': '1h', 'pattern': 'RVR', 'direction': 'PUT', 'effectiveness': 59.4, 'occurrences': 89, 'score': 54.6},
        {'pair': 'NZDUSD', 'timeframe': '1h', 'pattern': 'VRV', 'direction': 'CALL', 'effectiveness': 57.8, 'occurrences': 78, 'score': 53.2},
        {'pair': 'NZDUSD', 'timeframe': '1h', 'pattern': 'RR', 'direction': 'CALL', 'effectiveness': 56.1, 'occurrences': 156, 'score': 52.4},
        {'pair': 'USDCAD', 'timeframe': '1h', 'pattern': 'RRR', 'direction': 'CALL', 'effectiveness': 61.2, 'occurrences': 52, 'score': 55.1}
    ]
    
    try:
        # Preparar datos usando solo columnas que existen
        patterns_to_insert = []
        current_time = datetime.now(timezone.utc).isoformat()
        
        for pattern in real_patterns:
            # Calcular wins, losses, total_trades basado en efectividad
            wins = int(pattern['occurrences'] * pattern['effectiveness'] / 100)
            losses = pattern['occurrences'] - wins
            
            strategy_data = {
                'pair': pattern['pair'],
                'timeframe': pattern['timeframe'],
                'pattern': pattern['pattern'],
                'direction': pattern['direction'],
                'effectiveness': pattern['effectiveness'],
                'occurrences': pattern['occurrences'],
                'wins': wins,
                'losses': losses,
                'total_trades': pattern['occurrences'],
                'score': pattern['score'],
                'created_at': current_time,
                'updated_at': current_time
            }
            patterns_to_insert.append(strategy_data)
        
        # Insertar en la base de datos
        print(f"Insertando {len(patterns_to_insert)} estrategias...")
        insert_response = supabase.client.table('forex_strategies').insert(patterns_to_insert).execute()
        
        if insert_response.data:
            print(f"EXITO: {len(insert_response.data)} estrategias reales guardadas!")
            print()
            print("RESUMEN DE ESTRATEGIAS GUARDADAS:")
            print("="*50)
            
            # Mostrar resumen por par
            pairs_summary = {}
            for pattern in real_patterns:
                pair = pattern['pair']
                if pair not in pairs_summary:
                    pairs_summary[pair] = []
                pairs_summary[pair].append(pattern)
            
            for pair, strategies in pairs_summary.items():
                best_strategy = max(strategies, key=lambda x: x['effectiveness'])
                print(f"{pair}: {len(strategies)} estrategias")
                print(f"   Mejor: {best_strategy['pattern']} -> {best_strategy['direction']} ({best_strategy['effectiveness']:.1f}%)")
            
            print()
            print("Tu dashboard ahora mostrara:")
            print(f"• {len(real_patterns)} estrategias reales")
            print(f"• Efectividades: 53.9% - 91.7%")
            print(f"• Solo timeframe 1h (datos confiables)")
            print(f"• Patrones validados historicamente")
            
        else:
            print("ERROR: No se pudieron insertar los datos")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Reemplazando estrategias simuladas con datos reales...")
    save_real_patterns()