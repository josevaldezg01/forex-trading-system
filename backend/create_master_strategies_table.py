# backend/create_master_strategies_table.py
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

def create_master_strategies_system():
    """Crear sistema de estrategias master y migrar datos existentes"""
    
    print("Creando sistema de estrategias master...")
    supabase = create_supabase_client()
    
    try:
        # Paso 1: Obtener estrategias actuales de forex_strategies
        print("1. Obteniendo estrategias actuales...")
        current_strategies = supabase.client.table('forex_strategies').select('*').execute()
        
        if current_strategies.data:
            print(f"   Encontradas {len(current_strategies.data)} estrategias activas")
        else:
            print("   No se encontraron estrategias activas")
            return
        
        # Paso 2: Preparar datos para forex_strategies_master
        print("2. Preparando datos para tabla master...")
        
        master_strategies = []
        current_time = datetime.now(timezone.utc).isoformat()
        
        for strategy in current_strategies.data:
            # Copiar todos los campos + campos adicionales para master
            master_strategy = {
                'pair': strategy['pair'],
                'timeframe': strategy['timeframe'],
                'pattern': strategy['pattern'],
                'direction': strategy['direction'],
                'effectiveness': strategy['effectiveness'],
                'occurrences': strategy['occurrences'],
                'wins': strategy['wins'],
                'losses': strategy['losses'],
                'avg_profit': strategy['avg_profit'],
                'score': strategy['score'],
                'trigger_condition': strategy['trigger_condition'],
                'analysis_date': strategy['analysis_date'],
                'created_at': strategy['created_at'],
                
                # Campos adicionales para master
                'strategy_type': 'validated_real',  # Tipo de estrategia
                'source': 'historical_data_1h',     # Origen de los datos
                'validation_method': 'pattern_detector', # Método de validación
                'data_quality': 'high',             # Calidad de datos
                'is_active': True,                  # Si está activa actualmente
                'added_to_master': current_time     # Cuándo se agregó al master
            }
            master_strategies.append(master_strategy)
        
        # Paso 3: Verificar si forex_strategies_master existe
        print("3. Verificando tabla forex_strategies_master...")
        
        # Intentar consultar la tabla para ver si existe
        try:
            test_query = supabase.client.table('forex_strategies_master').select('id').limit(1).execute()
            table_exists = True
            print("   Tabla forex_strategies_master ya existe")
            
            # Verificar cuántos registros tiene
            count_query = supabase.client.table('forex_strategies_master').select('id').execute()
            existing_count = len(count_query.data) if count_query.data else 0
            print(f"   Registros existentes: {existing_count}")
            
        except Exception:
            table_exists = False
            print("   Tabla forex_strategies_master no existe - necesita ser creada")
        
        # Paso 4: Insertar en forex_strategies_master
        if table_exists:
            print("4. Insertando estrategias en tabla master...")
            
            try:
                insert_response = supabase.client.table('forex_strategies_master').insert(master_strategies).execute()
                
                if insert_response.data:
                    print(f"   EXITO: {len(insert_response.data)} estrategias agregadas al master")
                    
                    # Verificar total después de inserción
                    final_count_query = supabase.client.table('forex_strategies_master').select('id').execute()
                    final_count = len(final_count_query.data) if final_count_query.data else 0
                    print(f"   Total en master: {final_count} estrategias")
                    
                else:
                    print("   ERROR: No se insertaron las estrategias")
                    
            except Exception as e:
                print(f"   ERROR insertando: {e}")
                
        else:
            print("4. Tabla master no existe - creando estructura...")
            print("   NOTA: Necesitas crear la tabla forex_strategies_master en Supabase")
            print("   Estructura sugerida:")
            print("""
   CREATE TABLE forex_strategies_master (
       id BIGSERIAL PRIMARY KEY,
       pair VARCHAR NOT NULL,
       timeframe VARCHAR NOT NULL,
       pattern VARCHAR NOT NULL,
       direction VARCHAR NOT NULL,
       effectiveness DECIMAL NOT NULL,
       occurrences INTEGER NOT NULL,
       wins INTEGER NOT NULL,
       losses INTEGER NOT NULL,
       avg_profit DECIMAL,
       score DECIMAL,
       trigger_condition TEXT,
       analysis_date DATE,
       created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
       
       -- Campos adicionales para master
       strategy_type VARCHAR DEFAULT 'generated',
       source VARCHAR DEFAULT 'unknown',
       validation_method VARCHAR,
       data_quality VARCHAR DEFAULT 'medium',
       is_active BOOLEAN DEFAULT false,
       added_to_master TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
       
       -- Índices para consultas rápidas
       CONSTRAINT unique_strategy UNIQUE (pair, timeframe, pattern, direction)
   );
            """)
        
        # Paso 5: Generar más estrategias para master
        print("5. Preparando para generar más estrategias...")
        print("   Sugerencias para poblar master:")
        print("   - Ejecutar generadores de patrones automáticos")
        print("   - Importar estrategias de otros timeframes")
        print("   - Generar combinaciones de patrones complejos")
        print("   - Agregar estrategias basadas en indicadores técnicos")
        
        # Resumen final
        print("\nRESUMEN DEL SISTEMA:")
        print("="*50)
        print(f"forex_strategies (activas): {len(current_strategies.data)} estrategias")
        print("forex_strategies_master: Repositorio maestro que crece continuamente")
        print("- Tipo: validated_real (las 22 actuales)")
        print("- Origen: historical_data_1h")
        print("- Calidad: high")
        print()
        print("SIGUIENTE PASO: Crear tabla master en Supabase si no existe")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

def generate_additional_strategies():
    """Generar estrategias adicionales para poblar el master"""
    
    print("Generando estrategias adicionales...")
    
    # Patrones adicionales que no están en las 22 actuales
    additional_patterns = []
    
    # Patrones simples
    simple_patterns = ['R', 'V', 'RR', 'VV']
    
    # Patrones mixtos complejos
    complex_patterns = ['RRV', 'VVR', 'RRVR', 'VVRV', 'RVRR', 'VRVV']
    
    # Pares adicionales
    additional_pairs = ['EURGBP', 'EURJPY', 'GBPJPY', 'CHFJPY', 'CADCHF']
    
    # Timeframes para cuando tengamos datos limpios
    future_timeframes = ['5m', '15m', '30m', '4h']
    
    current_time = datetime.now(timezone.utc).isoformat()
    analysis_date = datetime.now(timezone.utc).date().isoformat()
    
    for pair in additional_pairs:
        for timeframe in ['1h']:  # Solo 1h por ahora
            for pattern in simple_patterns + complex_patterns:
                for direction in ['CALL', 'PUT']:
                    
                    # Generar datos simulados realistas
                    effectiveness = 50 + (hash(f"{pair}{pattern}{direction}") % 25)  # 50-75%
                    occurrences = 20 + (hash(f"{pair}{pattern}") % 80)  # 20-100
                    wins = int(occurrences * effectiveness / 100)
                    losses = occurrences - wins
                    score = 40 + (effectiveness - 50) * 0.8  # 40-60
                    
                    strategy = {
                        'pair': pair,
                        'timeframe': timeframe,
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
                    
                    additional_patterns.append(strategy)
    
    print(f"Generadas {len(additional_patterns)} estrategias adicionales")
    return additional_patterns

if __name__ == "__main__":
    print("Implementando sistema de estrategias master...")
    create_master_strategies_system()
    
    # Preguntar si quiere generar estrategias adicionales
    generate_more = input("\n¿Generar estrategias adicionales para master? (s/n): ").lower().strip()
    if generate_more == 's':
        additional = generate_additional_strategies()
        print(f"Preparadas {len(additional)} estrategias adicionales")
        print("Estas se pueden agregar al master una vez que la tabla esté creada")