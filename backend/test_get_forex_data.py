# backend/test_get_forex_data.py
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

def test_get_forex_data():
    """Probar el método get_forex_data con diferentes parámetros"""
    
    print("Probando get_forex_data()...")
    
    try:
        data_collector = create_data_collector()
        
        test_pair = 'EURUSD'
        test_timeframe = '1h'
        
        print(f"Intentando obtener datos: {test_pair} {test_timeframe}")
        
        # Probar con los parámetros básicos
        try:
            data = data_collector.get_forex_data(test_pair, test_timeframe)
            print(f"Éxito con 2 parámetros: {type(data)}")
            
            if data is not None:
                print(f"Tipo de datos: {type(data)}")
                if hasattr(data, '__len__'):
                    print(f"Longitud: {len(data)}")
                if hasattr(data, 'columns'):
                    print(f"Columnas: {data.columns.tolist()}")
                if hasattr(data, 'head'):
                    print(f"Primeras filas:")
                    print(data.head())
            else:
                print("Datos son None")
                
        except Exception as e:
            print(f"Error con 2 parámetros: {e}")
            
            # Probar con parámetros adicionales
            try:
                print("Probando con parámetros adicionales...")
                # Muchos data collectors requieren límite de datos
                data = data_collector.get_forex_data(test_pair, timeframe=test_timeframe, limit=100)
                print(f"Éxito con limit: {type(data)}")
            except Exception as e2:
                print(f"Error con limit: {e2}")
                
                # Probar solo con pair
                try:
                    print("Probando solo con pair...")
                    data = data_collector.get_forex_data(test_pair)
                    print(f"Éxito solo con pair: {type(data)}")
                except Exception as e3:
                    print(f"Error solo con pair: {e3}")
        
    except Exception as e:
        print(f"Error general: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_get_forex_data()