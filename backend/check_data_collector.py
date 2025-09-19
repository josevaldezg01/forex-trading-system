# backend/check_data_collector.py
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

from data_collector import create_data_collector

def check_data_collector_methods():
    """Verificar qué métodos tiene disponibles el data collector"""
    
    print("Verificando métodos del data collector...")
    
    try:
        # Crear instancia del data collector
        data_collector = create_data_collector()
        
        print(f"Tipo de objeto: {type(data_collector)}")
        print(f"\nMétodos disponibles:")
        
        # Listar todos los métodos disponibles
        methods = []
        for attr_name in dir(data_collector):
            if not attr_name.startswith('_'):
                attr = getattr(data_collector, attr_name)
                if callable(attr):
                    methods.append(f"   🔧 {attr_name}()")
                else:
                    methods.append(f"   📄 {attr_name} = {type(attr).__name__}")
        
        for method in methods:
            print(method)
        
        # Probar métodos comunes que podría tener
        common_methods = [
            'get_data',
            'get_historical_data', 
            'fetch_data',
            'collect_data',
            'get_forex_data',
            'get_candles',
            'get_ohlc_data'
        ]
        
        print(f"\nProbando métodos comunes:")
        for method_name in common_methods:
            if hasattr(data_collector, method_name):
                print(f"   ✅ {method_name}() - DISPONIBLE")
            else:
                print(f"   ❌ {method_name}() - NO DISPONIBLE")
        
        # Intentar obtener datos de prueba con el método correcto
        print(f"\nIntentando obtener datos de prueba...")
        
        test_pair = 'EURUSD'
        test_timeframe = '1h'
        
        # Probar diferentes métodos
        if hasattr(data_collector, 'get_historical_data'):
            print(f"Probando get_historical_data...")
            data = data_collector.get_historical_data(test_pair, test_timeframe)
            print(f"Resultado: {type(data)} - {len(data) if hasattr(data, '__len__') else 'No length'}")
        
        elif hasattr(data_collector, 'fetch_data'):
            print(f"Probando fetch_data...")
            data = data_collector.fetch_data(test_pair, test_timeframe)
            print(f"Resultado: {type(data)} - {len(data) if hasattr(data, '__len__') else 'No length'}")
        
        elif hasattr(data_collector, 'collect_data'):
            print(f"Probando collect_data...")
            data = data_collector.collect_data(test_pair, test_timeframe)
            print(f"Resultado: {type(data)} - {len(data) if hasattr(data, '__len__') else 'No length'}")
        
        else:
            print("No se encontró un método obvio para obtener datos")
            
    except Exception as e:
        print(f"Error verificando data collector: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_data_collector_methods()