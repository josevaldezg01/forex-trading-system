import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from collections import Counter, defaultdict
from supabase import create_client
import json

# Configuración Supabase
SUPABASE_URL = 'https://cxtresumeeybaksjtaqs.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN4dHJlc3VtZWV5YmFrc2p0YXFzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTMwMzE5ODgsImV4cCI6MjA2ODYwNzk4OH0.oo1l7GeAJQOGzM9nMgzFYrxwKNIU9x0B0RJlx7ShSOM'
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class AdvancedPatternAnalyzer:
    def __init__(self):
        self.discovered_strategies = []
        
        # Combinaciones conocidas
        self.known_combinations = [
            ("AUDJPY", "1min"), ("AUDJPY", "5min"), ("AUDJPY", "15min"), ("AUDJPY", "30min"), ("AUDJPY", "1h"), ("AUDJPY", "4h"), ("AUDJPY", "1d"), ("AUDJPY", "1w"), ("AUDJPY", "1M"),
            ("AUDUSD", "1min"), ("AUDUSD", "5min"), ("AUDUSD", "15min"), ("AUDUSD", "30min"), ("AUDUSD", "1h"), ("AUDUSD", "4h"), ("AUDUSD", "1d"), ("AUDUSD", "1w"), ("AUDUSD", "1M"),
            ("CADJPY", "1min"), ("CADJPY", "5min"), ("CADJPY", "15min"), ("CADJPY", "30min"), ("CADJPY", "1h"), ("CADJPY", "4h"), ("CADJPY", "1d"), ("CADJPY", "1w"), ("CADJPY", "1M"),
            ("CHFJPY", "1min"), ("CHFJPY", "5min"), ("CHFJPY", "15min"), ("CHFJPY", "30min"), ("CHFJPY", "1h"), ("CHFJPY", "4h"), ("CHFJPY", "1d"), ("CHFJPY", "1w"), ("CHFJPY", "1M"),
            ("EURJPY", "1min"), ("EURJPY", "5min"), ("EURJPY", "15min"), ("EURJPY", "30min"), ("EURJPY", "1h"), ("EURJPY", "4h"), ("EURJPY", "1d"), ("EURJPY", "1w"), ("EURJPY", "1M"),
            ("EURUSD", "1min"), ("EURUSD", "5min"), ("EURUSD", "15min"), ("EURUSD", "30min"), ("EURUSD", "1h"), ("EURUSD", "4h"), ("EURUSD", "1d"), ("EURUSD", "1w"), ("EURUSD", "1M"),
            ("GBPJPY", "1min"), ("GBPJPY", "5min"), ("GBPJPY", "15min"), ("GBPJPY", "30min"), ("GBPJPY", "1h"), ("GBPJPY", "4h"), ("GBPJPY", "1d"), ("GBPJPY", "1w"), ("GBPJPY", "1M"),
            ("GBPUSD", "1min"), ("GBPUSD", "5min"), ("GBPUSD", "15min"), ("GBPUSD", "30min"), ("GBPUSD", "1h"), ("GBPUSD", "4h"), ("GBPUSD", "1d"), ("GBPUSD", "1w"), ("GBPUSD", "1M"),
            ("NZDUSD", "1min"), ("NZDUSD", "5min"), ("NZDUSD", "15min"), ("NZDUSD", "30min"), ("NZDUSD", "1h"), ("NZDUSD", "4h"), ("NZDUSD", "1d"), ("NZDUSD", "1w"), ("NZDUSD", "1M"),
            ("USDCAD", "1min"), ("USDCAD", "5min"), ("USDCAD", "15min"), ("USDCAD", "30min"), ("USDCAD", "1h"), ("USDCAD", "4h"), ("USDCAD", "1d"), ("USDCAD", "1w"), ("USDCAD", "1M"),
            ("USDCHF", "1min"), ("USDCHF", "5min"), ("USDCHF", "15min"), ("USDCHF", "30min"), ("USDCHF", "1h"), ("USDCHF", "4h"), ("USDCHF", "1d"), ("USDCHF", "1w"), ("USDCHF", "1M"),
            ("USDJPY", "1min"), ("USDJPY", "5min"), ("USDJPY", "15min"), ("USDJPY", "30min"), ("USDJPY", "1h"), ("USDJPY", "4h"), ("USDJPY", "1d"), ("USDJPY", "1w"), ("USDJPY", "1M")
        ]
        
        # Configuración flexible por timeframe
        self.timeframe_config = {
            "1min": {"min_occurrences": 30, "effectiveness_threshold": 0.60, "min_records": 500},
            "5min": {"min_occurrences": 25, "effectiveness_threshold": 0.60, "min_records": 300},
            "15min": {"min_occurrences": 20, "effectiveness_threshold": 0.62, "min_records": 500},
            "30min": {"min_occurrences": 15, "effectiveness_threshold": 0.63, "min_records": 400},
            "1h": {"min_occurrences": 12, "effectiveness_threshold": 0.65, "min_records": 300},
            "4h": {"min_occurrences": 10, "effectiveness_threshold": 0.67, "min_records": 100},
            "1d": {"min_occurrences": 8, "effectiveness_threshold": 0.70, "min_records": 50},
            "1w": {"min_occurrences": 5, "effectiveness_threshold": 0.72, "min_records": 25},
            "1M": {"min_occurrences": 3, "effectiveness_threshold": 0.75, "min_records": 10}
        }
    
    def load_timeframe_data(self, pair, timeframe, max_records=20000):
        """Cargar datos optimizado"""
        try:
            result = supabase.table("forex_candles") \
                .select("*") \
                .eq("pair", pair) \
                .eq("timeframe", timeframe) \
                .order("datetime", desc=True) \
                .limit(max_records) \
                .execute()
            
            if not result.data:
                return None
            
            df = pd.DataFrame(result.data)
            df['datetime'] = pd.to_datetime(df['datetime'])
            df['color'] = df.apply(lambda row: 'green' if row['close'] >= row['open'] else 'red', axis=1)
            df['hour'] = df['datetime'].dt.hour
            df['minute'] = df['datetime'].dt.minute
            df['day_of_week'] = df['datetime'].dt.dayofweek
            
            # Ordenar cronológicamente y agregar índices posicionales
            df = df.sort_values('datetime').reset_index(drop=True)
            df['position'] = df.index + 1
            
            return df
            
        except Exception as e:
            return None
    
    def analyze_cyclic_patterns(self, df, timeframe):
        """Análisis de patrones cíclicos (estilo OBPlus)"""
        config = self.timeframe_config[timeframe]
        patterns = {}
        
        # Definir ciclos según timeframe
        if timeframe == "1min":
            cycles = [3, 5, 7, 10, 15]  # ciclos en minutos
        elif timeframe == "5min":
            cycles = [3, 4, 6, 12]  # ciclos en períodos de 5min
        elif timeframe in ["15min", "30min"]:
            cycles = [2, 3, 4, 6, 8]
        else:
            cycles = [2, 3, 4, 5, 6]
        
        for cycle_length in cycles:
            if len(df) < cycle_length * 3:  # Necesitamos al menos 3 ciclos completos
                continue
                
            # Crear grupos cíclicos
            df['cycle_group'] = df.index // cycle_length
            df['cycle_position'] = df.index % cycle_length
            
            # Analizar cada posición dentro del ciclo
            for position in range(cycle_length):
                position_data = df[df['cycle_position'] == position]
                
                if len(position_data) >= config["min_occurrences"]:
                    green_count = len(position_data[position_data['color'] == 'green'])
                    effectiveness = green_count / len(position_data)
                    
                    if effectiveness >= config["effectiveness_threshold"] or effectiveness <= (1 - config["effectiveness_threshold"]):
                        bias = 'green' if effectiveness >= 0.5 else 'red'
                        final_effectiveness = effectiveness if bias == 'green' else (1 - effectiveness)
                        
                        pattern_key = f"CYCLE_{cycle_length}_POS_{position+1}"
                        patterns[pattern_key] = {
                            'type': 'cyclic',
                            'cycle_length': cycle_length,
                            'position': position + 1,
                            'bias': bias,
                            'effectiveness': final_effectiveness,
                            'occurrences': len(position_data),
                            'description': f"Cada {cycle_length} velas, posición {position+1} -> {bias}"
                        }
        
        return patterns
    
    def analyze_positional_patterns(self, df, timeframe):
        """Análisis de patrones posicionales específicos"""
        config = self.timeframe_config[timeframe]
        patterns = {}
        
        # Patrones específicos según posición de vela
        positions_to_check = [1, 3, 5, 7, 10, 12, 15, 20]
        
        for target_pos in positions_to_check:
            if len(df) < target_pos * 5:  # Necesitamos suficientes datos
                continue
            
            # Obtener velas en posiciones específicas
            target_candles = df[df.index % target_pos == (target_pos - 1)]
            
            if len(target_candles) >= config["min_occurrences"]:
                green_count = len(target_candles[target_candles['color'] == 'green'])
                effectiveness = green_count / len(target_candles)
                
                if effectiveness >= config["effectiveness_threshold"] or effectiveness <= (1 - config["effectiveness_threshold"]):
                    bias = 'green' if effectiveness >= 0.5 else 'red'
                    final_effectiveness = effectiveness if bias == 'green' else (1 - effectiveness)
                    
                    pattern_key = f"POSITION_{target_pos}"
                    patterns[pattern_key] = {
                        'type': 'positional',
                        'position': target_pos,
                        'bias': bias,
                        'effectiveness': final_effectiveness,
                        'occurrences': len(target_candles),
                        'description': f"Vela en posición {target_pos} -> {bias}"
                    }
        
        return patterns
    
    def analyze_reversal_patterns(self, df, timeframe):
        """Análisis de patrones de reversión"""
        config = self.timeframe_config[timeframe]
        patterns = {}
        
        # Buscar secuencias de reversión
        reversal_lengths = [2, 3, 4, 5]
        
        for seq_length in reversal_lengths:
            if len(df) < seq_length + 50:
                continue
            
            for i in range(len(df) - seq_length - 1):
                # Obtener secuencia
                sequence = df.iloc[i:i+seq_length]['color'].tolist()
                
                # Verificar si es una secuencia de un solo color
                if len(set(sequence)) == 1:  # Todas del mismo color
                    if i + seq_length < len(df):
                        next_candle = df.iloc[i + seq_length]['color']
                        
                        # Reversión: secuencia de un color seguida por color opuesto
                        if sequence[0] != next_candle:
                            reversal_key = f"REVERSAL_{seq_length}_{sequence[0]}_to_{next_candle}"
                            
                            if reversal_key not in patterns:
                                patterns[reversal_key] = {'outcomes': [], 'sequence_color': sequence[0]}
                            
                            patterns[reversal_key]['outcomes'].append(next_candle)
        
        # Evaluar efectividad de reversiones
        effective_reversals = {}
        for pattern_key, data in patterns.items():
            if len(data['outcomes']) >= config["min_occurrences"]:
                # Para reversiones, medimos qué tan consistente es el cambio
                expected_color = 'green' if data['sequence_color'] == 'red' else 'red'
                reversal_count = sum(1 for outcome in data['outcomes'] if outcome == expected_color)
                effectiveness = reversal_count / len(data['outcomes'])
                
                if effectiveness >= config["effectiveness_threshold"]:
                    seq_length = int(pattern_key.split('_')[1])
                    
                    effective_reversals[pattern_key] = {
                        'type': 'reversal',
                        'sequence_length': seq_length,
                        'sequence_color': data['sequence_color'],
                        'bias': expected_color,
                        'effectiveness': effectiveness,
                        'occurrences': len(data['outcomes']),
                        'description': f"Después de {seq_length} {data['sequence_color']} consecutivas -> {expected_color}"
                    }
        
        return effective_reversals
    
    def analyze_minority_prevalence(self, df, timeframe):
        """Análisis de prevalencia de minoría (estilo MHI de OBPlus)"""
        config = self.timeframe_config[timeframe]
        patterns = {}
        
        # Analizar grupos de velas para detectar minoría
        group_sizes = [3, 4, 5, 6, 7]
        
        for group_size in group_sizes:
            if len(df) < group_size * 10:
                continue
            
            minority_outcomes = []
            
            for i in range(len(df) - group_size - 1):
                group = df.iloc[i:i+group_size]['color'].tolist()
                
                # Contar colores en el grupo
                green_count = group.count('green')
                red_count = group.count('red')
                
                # Determinar color minoritario
                if green_count < red_count:
                    minority_color = 'green'
                elif red_count < green_count:
                    minority_color = 'red'
                else:
                    continue  # Empate, saltar
                
                # Verificar la siguiente vela
                if i + group_size < len(df):
                    next_candle = df.iloc[i + group_size]['color']
                    minority_outcomes.append((minority_color, next_candle))
            
            if len(minority_outcomes) >= config["min_occurrences"]:
                # Evaluar si la minoría tiende a prevalecer en la siguiente vela
                minority_wins = sum(1 for minority, next_color in minority_outcomes if minority == next_color)
                effectiveness = minority_wins / len(minority_outcomes)
                
                if effectiveness >= config["effectiveness_threshold"]:
                    pattern_key = f"MINORITY_{group_size}"
                    patterns[pattern_key] = {
                        'type': 'minority_prevalence',
                        'group_size': group_size,
                        'bias': 'minority',
                        'effectiveness': effectiveness,
                        'occurrences': len(minority_outcomes),
                        'description': f"En grupos de {group_size}, la minoría prevalece en siguiente vela"
                    }
        
        return patterns
    
    def format_advanced_pattern_for_storage(self, strategy_data):
        """Convertir patrón avanzado a formato de almacenamiento"""
        pattern_type = strategy_data['type']
        
        if pattern_type == 'cyclic':
            pattern_str = f"C{strategy_data['cycle_length']}P{strategy_data['position']}"
            direction = 'CALL' if strategy_data['bias'] == 'green' else 'PUT'
            trigger = f"Cycle {strategy_data['cycle_length']}, position {strategy_data['position']}"
            
        elif pattern_type == 'positional':
            pattern_str = f"POS{strategy_data['position']}"
            direction = 'CALL' if strategy_data['bias'] == 'green' else 'PUT'
            trigger = f"Position {strategy_data['position']} candle"
            
        elif pattern_type == 'reversal':
            seq_color = 'R' if strategy_data['sequence_color'] == 'red' else 'V'
            pattern_str = f"REV{strategy_data['sequence_length']}{seq_color}"
            direction = 'CALL' if strategy_data['bias'] == 'green' else 'PUT'
            trigger = f"After {strategy_data['sequence_length']} consecutive {strategy_data['sequence_color']}"
            
        elif pattern_type == 'minority_prevalence':
            pattern_str = f"MIN{strategy_data['group_size']}"
            direction = 'CALL'  # Para minoría, siempre apostar al color minoritario
            trigger = f"Minority in group of {strategy_data['group_size']}"
            
        else:
            pattern_str = "UNKNOWN"
            direction = "CALL"
            trigger = "Unknown pattern"
        
        return pattern_str, direction, trigger
    
    def save_advanced_strategy(self, strategy_data, pair, timeframe):
        """Guardar estrategia avanzada"""
        try:
            pattern_str, direction, trigger_condition = self.format_advanced_pattern_for_storage(strategy_data)
            
            wins = int(strategy_data['occurrences'] * strategy_data['effectiveness'])
            losses = strategy_data['occurrences'] - wins
            
            strategy_record = {
                'pair': pair,
                'timeframe': timeframe,
                'pattern': pattern_str,
                'direction': direction,
                'effectiveness': strategy_data['effectiveness'],
                'occurrences': strategy_data['occurrences'],
                'wins': wins,
                'losses': losses,
                'avg_profit': 55.0,
                'score': strategy_data['effectiveness'] * 100,
                'trigger_condition': trigger_condition,
                'analysis_date': datetime.now().isoformat(),
                'strategy_type': strategy_data['type'],
                'source': 'advanced_pattern_analyzer',
                'validation_method': 'advanced_analysis',
                'data_quality': 'high',
                'is_active': True,
                'added_to_master': datetime.now().isoformat()
            }
            
            result = supabase.table("forex_strategies_master") \
                .insert(strategy_record) \
                .execute()
                
            return True
            
        except Exception as e:
            print(f"        Error guardando {pattern_str}: {e}")
            return False
    
    def analyze_pair_timeframe(self, pair, timeframe):
        """Análisis completo para un par/timeframe"""
        print(f"  Analizando {pair} {timeframe}...")
        
        # Cargar datos
        df = self.load_timeframe_data(pair, timeframe)
        if df is None or len(df) < self.timeframe_config[timeframe]["min_records"]:
            print(f"    Datos insuficientes")
            return 0
        
        print(f"    Dataset: {len(df)} registros")
        
        all_patterns = {}
        
        # 1. Análisis cíclico
        cyclic = self.analyze_cyclic_patterns(df, timeframe)
        all_patterns.update(cyclic)
        print(f"    Patrones cíclicos: {len(cyclic)}")
        
        # 2. Análisis posicional
        positional = self.analyze_positional_patterns(df, timeframe)
        all_patterns.update(positional)
        print(f"    Patrones posicionales: {len(positional)}")
        
        # 3. Análisis de reversión
        reversal = self.analyze_reversal_patterns(df, timeframe)
        all_patterns.update(reversal)
        print(f"    Patrones de reversión: {len(reversal)}")
        
        # 4. Análisis de minoría
        minority = self.analyze_minority_prevalence(df, timeframe)
        all_patterns.update(minority)
        print(f"    Patrones de minoría: {len(minority)}")
        
        # Guardar estrategias
        saved_count = 0
        for pattern_key, pattern_data in all_patterns.items():
            if self.save_advanced_strategy(pattern_data, pair, timeframe):
                saved_count += 1
        
        print(f"    Guardadas: {saved_count} estrategias")
        return saved_count
    
    def run_advanced_analysis(self):
        """Ejecutar análisis avanzado completo"""
        print("ANALIZADOR DE PATRONES AVANZADO (Estilo OBPlus)")
        print("=" * 60)
        
        # Verificar qué combinaciones tienen datos suficientes
        viable_combinations = []
        for pair, timeframe in self.known_combinations:
            try:
                count_result = supabase.table("forex_candles") \
                    .select("*", count="exact") \
                    .eq("pair", pair) \
                    .eq("timeframe", timeframe) \
                    .execute()
                
                count = count_result.count or 0
                min_required = self.timeframe_config[timeframe]["min_records"]
                
                if count >= min_required:
                    viable_combinations.append((pair, timeframe, count))
                    
            except:
                continue
        
        print(f"Combinaciones viables: {len(viable_combinations)}")
        
        total_strategies = 0
        
        for i, (pair, timeframe, count) in enumerate(viable_combinations, 1):
            print(f"\n[{i}/{len(viable_combinations)}] {pair} {timeframe} ({count:,} registros)")
            strategies_found = self.analyze_pair_timeframe(pair, timeframe)
            total_strategies += strategies_found
        
        print(f"\n{'='*60}")
        print(f"ANÁLISIS AVANZADO COMPLETADO")
        print(f"Total estrategias descubiertas: {total_strategies}")
        print(f"Combinaciones analizadas: {len(viable_combinations)}")
        print(f"{'='*60}")
        
        return total_strategies

def main():
    analyzer = AdvancedPatternAnalyzer()
    
    print("ANALIZADOR DE PATRONES AVANZADO")
    print("Incluye análisis cíclico, posicional, reversión y minoría")
    print("Criterios más flexibles para detectar más estrategias")
    
    confirm = input("\n¿Proceder con el análisis avanzado? (s/n): ")
    
    if confirm.lower() in ['s', 'si', 'y', 'yes']:
        total = analyzer.run_advanced_analysis()
        
        if total > 0:
            print(f"\n¡ANÁLISIS COMPLETADO!")
            print(f"Se descubrieron {total} estrategias avanzadas")
            print(f"Revisa forex_strategies_master para ver todas las estrategias")
        else:
            print(f"\nNo se encontraron estrategias con los criterios establecidos")
    else:
        print("Análisis cancelado.")

if __name__ == "__main__":
    main()