import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict
from supabase import create_client
import json

# Configuración Supabase
SUPABASE_URL = 'https://cxtresumeeybaksjtaqs.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN4dHJlc3VtZWV5YmFrc2p0YXFzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTMwMzE5ODgsImV4cCI6MjA2ODYwNzk4OH0.oo1l7GeAJQOGzM9nMgzFYrxwKNIU9x0B0RJlx7ShSOM'
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class OBPlusCompleteAnalyzer:
    def __init__(self):
        # Pares disponibles según datos verificados
        self.pairs = {
            '1min': ["USDCHF", "AUDJPY", "USDCAD", "EURJPY", "CHFJPY", "CADJPY", "NZDUSD"],
            'other': ["AUDJPY", "AUDUSD", "CADJPY", "CHFJPY", "EURJPY", "EURUSD", "GBPJPY", "GBPUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
        }
        
        # Timeframes y sus requisitos mínimos de datos
        self.timeframes = {
            '1min': {'min_records': 1000, 'min_occurrences': 50},
            '5min': {'min_records': 500, 'min_occurrences': 40},
            '15min': {'min_records': 300, 'min_occurrences': 30},
            '30min': {'min_records': 200, 'min_occurrences': 25},
            '1h': {'min_records': 150, 'min_occurrences': 20}
        }
        
        self.effectiveness_threshold = 0.60  # 60% mínimo
    
    def load_timeframe_data(self, pair, timeframe, days_back=30):
        """Cargar datos para cualquier timeframe"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            result = supabase.table("forex_candles") \
                .select("*") \
                .eq("pair", pair) \
                .eq("timeframe", timeframe) \
                .gte("datetime", start_date.isoformat()) \
                .order("datetime") \
                .execute()
            
            if result.data:
                df = pd.DataFrame(result.data)
                df['datetime'] = pd.to_datetime(df['datetime'])
                df['color'] = df.apply(lambda row: 'green' if row['close'] >= row['open'] else 'red', axis=1)
                return df
            return None
                
        except Exception as e:
            print(f"Error cargando {pair} {timeframe}: {e}")
            return None
    
    def strategy_tres_mosqueteros(self, df):
        """Tres Mosqueteros: Vela central → siguiente vela"""
        results = []
        for i in range(0, len(df) - 5):
            fragment = df.iloc[i:i+5]
            central_candle = fragment.iloc[2]  # Posición central (0-indexed)
            
            if i + 5 < len(df):
                next_candle = df.iloc[i + 5]
                results.append({
                    'reference': central_candle['color'],
                    'actual': next_candle['color'],
                    'correct': central_candle['color'] == next_candle['color']
                })
        
        return self.evaluate_strategy(results, 'TresMosqueteros', 'Central vela → siguiente')
    
    def strategy_mejor_de_3(self, df):
        """Mejor de 3: Mayoría en 3 centrales → vela central siguiente fragmento"""
        results = []
        for i in range(0, len(df) - 10, 5):  # Saltar de fragmento en fragmento
            current_fragment = df.iloc[i:i+5]
            central_3 = current_fragment.iloc[1:4]  # Velas 2,3,4
            
            green_count = sum(1 for _, candle in central_3.iterrows() if candle['color'] == 'green')
            if green_count > 1:  # Mayoría verde
                majority_color = 'green'
            elif green_count < 2:  # Mayoría roja
                majority_color = 'red'
            else:
                continue  # Empate
            
            # Siguiente fragmento
            if i + 7 < len(df):  # Vela central del siguiente fragmento
                target_candle = df.iloc[i + 7]
                results.append({
                    'reference': majority_color,
                    'actual': target_candle['color'],
                    'correct': majority_color == target_candle['color']
                })
        
        return self.evaluate_strategy(results, 'MejorDe3', 'Mayoría 3 centrales → central siguiente')
    
    def strategy_mhi_3(self, df):
        """MHI 3: Color minoritario prevalece"""
        results = []
        for i in range(0, len(df) - 5):
            fragment = df.iloc[i:i+5]
            green_count = sum(1 for _, candle in fragment.iterrows() if candle['color'] == 'green')
            
            if green_count < 2:  # Verde es minoría
                minority_color = 'green'
            elif green_count > 3:  # Rojo es minoría
                minority_color = 'red'
            else:
                continue  # No hay clara minoría
            
            if i + 5 < len(df):
                next_candle = df.iloc[i + 5]
                results.append({
                    'reference': minority_color,
                    'actual': next_candle['color'],
                    'correct': minority_color == next_candle['color']
                })
        
        return self.evaluate_strategy(results, 'MHI3', 'Color minoritario prevalece')
    
    def strategy_milhao_maioria(self, df):
        """Milhão Maioria: Mayoría en 3 centrales → primera vela siguiente fragmento"""
        results = []
        for i in range(0, len(df) - 10, 5):
            current_fragment = df.iloc[i:i+5]
            central_3 = current_fragment.iloc[1:4]
            
            green_count = sum(1 for _, candle in central_3.iterrows() if candle['color'] == 'green')
            if green_count > 1:
                majority_color = 'green'
            elif green_count < 2:
                majority_color = 'red'
            else:
                continue
            
            if i + 5 < len(df):  # Primera vela siguiente fragmento
                target_candle = df.iloc[i + 5]
                results.append({
                    'reference': majority_color,
                    'actual': target_candle['color'],
                    'correct': majority_color == target_candle['color']
                })
        
        return self.evaluate_strategy(results, 'MilhaoMaioria', 'Mayoría 3 centrales → primera siguiente')
    
    def strategy_padrao_23(self, df):
        """PADRÃO 23: Primera vela → segunda vela mismo color"""
        results = []
        for i in range(0, len(df) - 1):
            first_candle = df.iloc[i]
            second_candle = df.iloc[i + 1]
            
            results.append({
                'reference': first_candle['color'],
                'actual': second_candle['color'],
                'correct': first_candle['color'] == second_candle['color']
            })
        
        return self.evaluate_strategy(results, 'Padrao23', 'Primera vela → segunda mismo color')
    
    def strategy_padrao_impar(self, df):
        """PADRÃO ÍMPAR: Vela central → primera siguiente fragmento"""
        results = []
        for i in range(0, len(df) - 10, 5):
            current_fragment = df.iloc[i:i+5]
            central_candle = current_fragment.iloc[2]
            
            if i + 5 < len(df):
                target_candle = df.iloc[i + 5]  # Primera del siguiente fragmento
                results.append({
                    'reference': central_candle['color'],
                    'actual': target_candle['color'],
                    'correct': central_candle['color'] == target_candle['color']
                })
        
        return self.evaluate_strategy(results, 'PadraoImpar', 'Central → primera siguiente fragmento')
    
    def strategy_torres_gemeas(self, df):
        """Torres Gêmeas: Primera vela → última del mismo fragmento"""
        results = []
        for i in range(0, len(df) - 5, 5):
            fragment = df.iloc[i:i+5]
            first_candle = fragment.iloc[0]
            last_candle = fragment.iloc[4]
            
            results.append({
                'reference': first_candle['color'],
                'actual': last_candle['color'],
                'correct': first_candle['color'] == last_candle['color']
            })
        
        return self.evaluate_strategy(results, 'TorresGemeas', 'Primera → última mismo fragmento')
    
    def strategy_extremos_opuestos(self, df):
        """Estrategia adicional: Extremos opuestos - primera y última tienden a ser opuestas"""
        results = []
        for i in range(0, len(df) - 5, 5):
            fragment = df.iloc[i:i+5]
            first_candle = fragment.iloc[0]
            last_candle = fragment.iloc[4]
            
            opposite_color = 'green' if first_candle['color'] == 'red' else 'red'
            results.append({
                'reference': opposite_color,
                'actual': last_candle['color'],
                'correct': opposite_color == last_candle['color']
            })
        
        return self.evaluate_strategy(results, 'ExtremosOpuestos', 'Primera → última color opuesto')
    
    def strategy_simetria_central(self, df):
        """Estrategia adicional: Simetría - velas 2 y 4 tienden a ser iguales"""
        results = []
        for i in range(0, len(df) - 5, 5):
            fragment = df.iloc[i:i+5]
            second_candle = fragment.iloc[1]
            fourth_candle = fragment.iloc[3]
            
            results.append({
                'reference': second_candle['color'],
                'actual': fourth_candle['color'],
                'correct': second_candle['color'] == fourth_candle['color']
            })
        
        return self.evaluate_strategy(results, 'SimetriaCentral', 'Vela 2 → Vela 4 mismo color')
    
    def strategy_momentum_continuacion(self, df):
        """Estrategia adicional: Momentum - si 3 primeras son iguales, las 2 últimas siguen"""
        results = []
        for i in range(0, len(df) - 5, 5):
            fragment = df.iloc[i:i+5]
            first_three = fragment.iloc[0:3]
            
            # Verificar si las 3 primeras son del mismo color
            colors = [candle['color'] for _, candle in first_three.iterrows()]
            if len(set(colors)) == 1:  # Todas iguales
                momentum_color = colors[0]
                fourth_candle = fragment.iloc[3]
                fifth_candle = fragment.iloc[4]
                
                results.append({
                    'reference': momentum_color,
                    'actual': fourth_candle['color'],
                    'correct': momentum_color == fourth_candle['color'],
                    'position': 4
                })
                
                results.append({
                    'reference': momentum_color,
                    'actual': fifth_candle['color'],
                    'correct': momentum_color == fifth_candle['color'],
                    'position': 5
                })
        
        return self.evaluate_strategy(results, 'MomentumContinuacion', '3 primeras iguales → momentum continúa')
    
    def evaluate_strategy(self, results, strategy_name, description):
        """Evaluar efectividad de una estrategia"""
        if len(results) < self.timeframes.get('1min', {}).get('min_occurrences', 20):
            return None
        
        correct_predictions = sum(1 for r in results if r['correct'])
        effectiveness = correct_predictions / len(results)
        
        if effectiveness >= self.effectiveness_threshold:
            return {
                'name': strategy_name,
                'effectiveness': effectiveness,
                'occurrences': len(results),
                'wins': correct_predictions,
                'losses': len(results) - correct_predictions,
                'description': description
            }
        
        return None
    
    def save_obplus_strategy(self, strategy, pair, timeframe):
        """Guardar estrategia en base de datos"""
        try:
            # Determinar dirección basada en la estrategia
            if 'Opuestos' in strategy['name']:
                direction = 'REVERSE'
            else:
                direction = 'CALL'  # Mayoría de estrategias OBPlus son direccionales
            
            strategy_record = {
                'pair': pair,
                'timeframe': timeframe,
                'pattern': strategy['name'][:10],  # Truncar para DB
                'direction': direction,
                'effectiveness': strategy['effectiveness'],
                'occurrences': strategy['occurrences'],
                'wins': strategy['wins'],
                'losses': strategy['losses'],
                'avg_profit': 55.0,
                'score': strategy['effectiveness'] * 100,
                'trigger_condition': strategy['description'],
                'analysis_date': datetime.now().isoformat(),
                'strategy_type': 'obplus_complete',
                'source': 'obplus_complete_analyzer',
                'validation_method': 'fragment_analysis_5_candles',
                'data_quality': 'high',
                'is_active': True,
                'added_to_master': datetime.now().isoformat()
            }
            
            result = supabase.table("forex_strategies_master") \
                .insert(strategy_record) \
                .execute()
                
            return True
            
        except Exception as e:
            print(f"Error guardando {strategy['name']}: {e}")
            return False
    
    def analyze_pair_timeframe(self, pair, timeframe):
        """Analizar un par en un timeframe específico"""
        print(f"  Analizando {pair} {timeframe}")
        
        # Cargar datos
        df = self.load_timeframe_data(pair, timeframe)
        if df is None or len(df) < self.timeframes[timeframe]['min_records']:
            print(f"    Datos insuficientes")
            return 0
        
        print(f"    Dataset: {len(df)} velas")
        
        # Aplicar todas las estrategias
        strategies = [
            self.strategy_tres_mosqueteros(df),
            self.strategy_mejor_de_3(df),
            self.strategy_mhi_3(df),
            self.strategy_milhao_maioria(df),
            self.strategy_padrao_23(df),
            self.strategy_padrao_impar(df),
            self.strategy_torres_gemeas(df),
            self.strategy_extremos_opuestos(df),
            self.strategy_simetria_central(df),
            self.strategy_momentum_continuacion(df)
        ]
        
        # Filtrar estrategias válidas y guardar
        valid_strategies = [s for s in strategies if s is not None]
        saved_count = 0
        
        for strategy in valid_strategies:
            print(f"      {strategy['name']}: {strategy['effectiveness']:.1%} ({strategy['occurrences']} ops)")
            if self.save_obplus_strategy(strategy, pair, timeframe):
                saved_count += 1
        
        print(f"    Guardadas: {saved_count} estrategias")
        return saved_count
    
    def run_complete_analysis(self):
        """Ejecutar análisis completo en todos los timeframes"""
        print("ANALIZADOR OBPLUS COMPLETO - MULTI-TIMEFRAME")
        print("=" * 60)
        print("Estrategias: 7 OBPlus + 3 adicionales")
        print("Timeframes: 1min, 5min, 15min, 30min, 1h")
        print("Metodología: Fragmentos de 5 velas")
        
        total_strategies = 0
        analysis_summary = {}
        
        for timeframe in self.timeframes.keys():
            print(f"\nTIMEFRAME: {timeframe}")
            print("-" * 30)
            
            # Seleccionar pares según timeframe
            if timeframe == '1min':
                pairs_to_analyze = self.pairs['1min']
            else:
                pairs_to_analyze = self.pairs['other']
            
            timeframe_strategies = 0
            
            for pair in pairs_to_analyze:
                strategies_found = self.analyze_pair_timeframe(pair, timeframe)
                timeframe_strategies += strategies_found
            
            analysis_summary[timeframe] = timeframe_strategies
            total_strategies += timeframe_strategies
            print(f"  Total {timeframe}: {timeframe_strategies} estrategias")
        
        print(f"\n{'='*60}")
        print(f"ANÁLISIS OBPLUS COMPLETADO")
        print(f"{'='*60}")
        print(f"Total estrategias generadas: {total_strategies}")
        
        for tf, count in analysis_summary.items():
            print(f"  {tf}: {count} estrategias")
        
        print(f"\nCobertura: {len(self.pairs['other'])} pares × {len(self.timeframes)} timeframes")
        print(f"Metodologías: 10 estrategias por combinación viable")
        print(f"Fuente: obplus_complete_analyzer")
        
        return total_strategies

def main():
    analyzer = OBPlusCompleteAnalyzer()
    
    print("SISTEMA COMPLETO OBPLUS MULTI-TIMEFRAME")
    print("Implementa 7 estrategias OBPlus + 3 estrategias adicionales")
    print("Análisis en 5 timeframes diferentes")
    print("Fragmentos de 5 velas en cada timeframe")
    
    confirm = input("\n¿Proceder con análisis completo? (s/n): ")
    
    if confirm.lower() in ['s', 'si', 'y', 'yes']:
        total = analyzer.run_complete_analysis()
        
        if total > 0:
            print(f"\nSISTEMA OBPLUS IMPLEMENTADO")
            print(f"Se generaron {total} estrategias multi-timeframe")
            print(f"Metodologías probadas de OBPlus + variaciones")
            print(f"Revisa forex_strategies_master con source='obplus_complete_analyzer'")
        else:
            print(f"\nNo se encontraron estrategias que cumplan criterios")
    else:
        print("Análisis cancelado.")

if __name__ == "__main__":
    main()