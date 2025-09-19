# backend/get_table_schema.py
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

def get_table_schema():
    """Obtener estructura exacta de la tabla forex_strategies usando SQL"""
    
    print("Consultando esquema de tabla forex_strategies...")
    supabase = create_supabase_client()
    
    try:
        # Query SQL para obtener información de columnas
        schema_query = """
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM information_schema.columns 
        WHERE table_name = 'forex_strategies'
        ORDER BY ordinal_position;
        """
        
        # Ejecutar query usando el cliente de Supabase
        response = supabase.client.rpc('exec_sql', {'sql': schema_query}).execute()
        
        if response.data:
            print("\nESTRUCTURA DE TABLA forex_strategies:")
            print("="*60)
            print(f"{'COLUMNA':<20} {'TIPO':<15} {'NULL':<8} {'DEFAULT':<15}")
            print("-" * 60)
            
            columns = []
            for row in response.data:
                column_name = row['column_name']
                data_type = row['data_type'] 
                nullable = row['is_nullable']
                default = row['column_default'] or ''
                
                columns.append(column_name)
                print(f"{column_name:<20} {data_type:<15} {nullable:<8} {default:<15}")
            
            print(f"\nCOLUMNAS DISPONIBLES ({len(columns)}):")
            for i, col in enumerate(columns, 1):
                print(f"  {i:2d}. {col}")
            
            # Crear datos de ejemplo usando solo columnas disponibles
            print(f"\nDATOS DE EJEMPLO PARA INSERCION:")
            example_data = {}
            for col in columns:
                if col == 'id':
                    continue  # Auto-generado
                elif col in ['pair']:
                    example_data[col] = 'EURUSD'
                elif col in ['timeframe']:
                    example_data[col] = '1h'
                elif col in ['pattern']:
                    example_data[col] = 'RRR'
                elif col in ['direction']:
                    example_data[col] = 'CALL'
                elif col in ['effectiveness']:
                    example_data[col] = 65.5
                elif col in ['occurrences', 'wins', 'losses', 'total_trades']:
                    example_data[col] = 50
                elif col in ['score']:
                    example_data[col] = 55.0
                elif col in ['created_at', 'updated_at']:
                    example_data[col] = '2025-01-01T12:00:00Z'
                else:
                    example_data[col] = None
            
            print("Estructura para insercion:")
            for key, value in example_data.items():
                print(f"  '{key}': {value}")
                
        else:
            print("No se pudo obtener información del esquema")
            
    except Exception as e:
        print(f"Error consultando esquema: {e}")
        
        # Método alternativo - usar PostgREST describe
        try:
            print("\nIntentando método alternativo...")
            
            # Inserción de prueba para ver que columnas acepta
            test_data = {
                'pair': 'TEST',
                'timeframe': '1h', 
                'pattern': 'R',
                'direction': 'CALL',
                'effectiveness': 50.0,
                'occurrences': 10,
                'wins': 5,
                'losses': 5,
                'score': 50.0,
                'created_at': '2025-01-01T12:00:00Z'
            }
            
            print("Probando insercion con datos basicos...")
            insert_response = supabase.client.table('forex_strategies').insert(test_data).execute()
            
            if insert_response.data:
                print("EXITO: Insercion de prueba funcionó")
                inserted = insert_response.data[0]
                print("Columnas confirmadas:")
                for key in inserted.keys():
                    print(f"  - {key}")
                
                # Limpiar registro de prueba
                supabase.client.table('forex_strategies').delete().eq('pair', 'TEST').execute()
                print("Registro de prueba eliminado")
            
        except Exception as e2:
            print(f"Error en método alternativo: {e2}")

if __name__ == "__main__":
    get_table_schema()