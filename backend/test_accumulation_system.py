# backend/test_accumulation_system.py
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    print(f"Cargando .env desde: {env_path}")
except ImportError:
    pass

from forex_analyzer import ForexAnalyzer

def test_accumulation_logic():
    """Probar el sistema de acumulación histórica"""
    
    print("Probando sistema de acumulación histórica...")
    print("="*60)
    
    # Crear analizador
    analyzer = ForexAnalyzer()
    
    # Probar análisis de un par específico
    test_pair = 'EURUSD'
    test_timeframe = '1h'
    
    print(f"1. Probando análisis de {test_pair} {test_timeframe}...")
    
    # Obtener estado inicial del master
    initial_master = analyzer.db_client.client.table('forex_strategies_master').select('*').eq('pair', test_pair).eq('timeframe', test_timeframe).execute()
    
    initial_count = len(initial_master.data) if initial_master.data else 0
    print(f"   Estrategias iniciales en master para {test_pair}: {initial_count}")
    
    # Ejecutar análisis
    result = analyzer.analyze_pair_with_accumulation(test_pair, test_timeframe)
    
    if result['success']:
        print(f"   EXITO: {result['patterns_found']} patrones encontrados")
        print(f"   Estrategias actualizadas: {result['patterns_updated']}")
        
        # Verificar estado final del master
        final_master = analyzer.db_client.client.table('forex_strategies_master').select('*').eq('pair', test_pair).eq('timeframe', test_timeframe).execute()
        
        final_count = len(final_master.data) if final_master.data else 0
        print(f"   Estrategias finales en master para {test_pair}: {final_count}")
        print(f"   Diferencia: +{final_count - initial_count}")
        
        if final_master.data:
            print(f"   Ejemplo de estrategia en master:")
            example = final_master.data[0]
            print(f"   {example['pattern']} -> {example['direction']}: {example['effectiveness']:.1f}% ({example['occurrences']} ocurrencias)")
            print(f"   Tipo: {example['strategy_type']}, Calidad: {example['data_quality']}")
    
    else:
        print(f"   ERROR: {result.get('error', 'Unknown error')}")
    
    print()
    
    # Mostrar resumen general
    print("2. Resumen general del sistema...")
    
    # Contar estrategias activas
    active_strategies = analyzer.db_client.client.table('forex_strategies').select('id').execute()
    active_count = len(active_strategies.data) if active_strategies.data else 0
    
    # Contar estrategias en master
    master_strategies = analyzer.db_client.client.table('forex_strategies_master').select('id').execute()
    master_count = len(master_strategies.data) if master_strategies.data else 0
    
    print(f"   Estrategias activas (forex_strategies): {active_count}")
    print(f"   Estrategias master (forex_strategies_master): {master_count}")
    
    # Mostrar distribución por tipo en master
    types_query = analyzer.db_client.client.table('forex_strategies_master').select('strategy_type').execute()
    if types_query.data:
        type_counts = {}
        for record in types_query.data:
            strategy_type = record['strategy_type']
            type_counts[strategy_type] = type_counts.get(strategy_type, 0) + 1
        
        print(f"   Distribución por tipo en master:")
        for strategy_type, count in type_counts.items():
            print(f"     {strategy_type}: {count}")
    
    # Mostrar top 5 estrategias del master
    top_strategies = analyzer.db_client.client.table('forex_strategies_master').select('pair, pattern, direction, effectiveness, occurrences, strategy_type').order('effectiveness', desc=True).limit(5).execute()
    
    if top_strategies.data:
        print(f"   Top 5 estrategias por efectividad:")
        for i, strategy in enumerate(top_strategies.data, 1):
            print(f"     {i}. {strategy['pair']} {strategy['pattern']} -> {strategy['direction']}: {strategy['effectiveness']:.1f}% ({strategy['occurrences']} occ, {strategy['strategy_type']})")
    
    print("\n" + "="*60)
    print("Prueba del sistema de acumulación completada")

def simulate_multiple_updates():
    """Simular múltiples actualizaciones para probar acumulación"""
    
    print("\n3. Simulando múltiples actualizaciones...")
    
    analyzer = ForexAnalyzer()
    test_pair = 'GBPUSD'
    test_timeframe = '1h'
    
    for i in range(3):
        print(f"   Iteración {i+1}...")
        
        result = analyzer.analyze_pair_with_accumulation(test_pair, test_timeframe)
        
        if result['success']:
            print(f"     Patrones encontrados: {result['patterns_found']}")
            
            # Mostrar una estrategia específica para ver acumulación
            strategy_query = analyzer.db_client.client.table('forex_strategies_master').select('occurrences, effectiveness, wins, losses').eq('pair', test_pair).eq('timeframe', test_timeframe).limit(1).execute()
            
            if strategy_query.data:
                strategy = strategy_query.data[0]
                print(f"     Estado actual: {strategy['occurrences']} occ, {strategy['effectiveness']:.1f}% eff, {strategy['wins']} wins, {strategy['losses']} losses")
        
        else:
            print(f"     Error: {result.get('error', 'Unknown')}")

if __name__ == "__main__":
    print("Iniciando prueba del sistema de acumulación histórica...")
    
    # Probar lógica básica
    test_accumulation_logic()
    
    # Simular múltiples actualizaciones
    simulate_multiple_updates()
    
    print("\nPruebas completadas.")