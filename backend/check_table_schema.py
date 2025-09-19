# backend/check_table_schema.py
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass

from supabase_client import create_supabase_client

def check_forex_strategies_schema():
    """Verificar exactamente qué columnas tiene la tabla forex_strategies"""
    
    print("Verificando esquema de tabla forex_strategies...")
    supabase = create_supabase_client()
    
    try:
        # Intentar obtener una fila para ver las columnas
        response = supabase.client.table('forex_strategies').select('*').limit(1).execute()
        
        if response.data and len(response.data) > 0:
            columns = list(response.data[0].keys())
            print(f"\nColumnas disponibles en forex_strategies:")
            for i, col in enumerate(columns, 1):
                print(f"   {i:2d}. {col}")
            
            print(f"\nEjemplo de datos:")
            example = response.data[0]
            for key, value in example.items():
                print(f"   {key}: {value}")
                
        else:
            print("La tabla está vacía, intentando insertar datos mínimos para ver estructura...")
            
            # Intentar con datos mínimos
            minimal_data = {
                'pair': 'TEST',
                'timeframe': '1h',
                'pattern': 'R',
                'direction': 'CALL',
                'effectiveness': 50.0,
                'occurrences': 10,
                'score': 50.0
            }
            
            test_response = supabase.client.table('forex_strategies').insert(minimal_data).execute()
            
            if test_response.data:
                print("Inserción de prueba exitosa")
                columns = list(test_response.data[0].keys())
                print(f"\nColumnas detectadas:")
                for i, col in enumerate(columns, 1):
                    print(f"   {i:2d}. {col}")
                
                # Limpiar el registro de prueba
                supabase.client.table('forex_strategies').delete().eq('pair', 'TEST').execute()
                print("Registro de prueba eliminado")
            else:
                print("No se pudo insertar datos de prueba")
        
    except Exception as e:
        print(f"Error verificando esquema: {e}")
        
        # Intentar método alternativo
        print("\nIntentando método alternativo...")
        try:
            # Usar información del cliente Supabase
            print("Columnas típicas que deberían existir:")
            typical_columns = [
                'id', 'pair', 'timeframe', 'pattern', 'direction', 
                'effectiveness', 'occurrences', 'score', 'avg_profit', 
                'created_at', 'updated_at', 'status', 'last_updated'
            ]
            
            for col in typical_columns:
                print(f"   - {col}")
                
        except Exception as e2:
            print(f"Error en método alternativo: {e2}")

if __name__ == "__main__":
    check_forex_strategies_schema()