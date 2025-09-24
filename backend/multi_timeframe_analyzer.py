import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from collections import Counter
from supabase import create_client
import os
import json

# Configuración Supabase
SUPABASE_URL = 'https://cxtresumeeybaksjtaqs.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN4dHJlc3VtZWV5YmFrc2p0YXFzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTMwMzE5ODgsImV4cCI6MjA2ODYwNzk4OH0.oo1l7GeAJQOGzM9nMgzFYrxwKNIU9x0B0RJlx7ShSOM'
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class DirectMultiTimeframeAnalyzer:
    def __init__(self):
        self.discovered_strategies = []
        
        # Combinaciones conocidas basadas en tu consulta SQL
        self.known_combinations = [
            # Pares con todos los timeframes (basado en tu consulta SQL)
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
        
        # Configuración por timeframe
        self.timeframe_config = {
            "1min": {"min_occurrences": 100, "effectiveness_threshold": 0.70, "min_records": 1000},
            "5min": {"min_occurrences": 50, "effectiveness_threshold": 0.68, "min_records": 500},
            "15min": {"min_occurrences": 50, "effectiveness_threshold": 0.65, "min_records": 1000},
            "30min": {"min_occurrences": 40, "effectiveness_threshold": 0.65, "min_records": 1000},
            "1h": {"min_occurrences": 30, "effectiveness_threshold": 0.65, "min_records": 1000},
            "4h": {"min_occurrences": 20, "effectiveness_threshold": 0.67, "min_records": 500},
            "1d": {"min_occurrences": 15, "effectiveness_threshold": 0.70, "min_records": 100},
            "1w": {"min_occurrences": 8, "effectiveness_threshold": 0.75, "min_records": 50},
            "1M": {"min_occurrences": 5, "effectiveness_threshold": 0.80, "min_records": 20}
        }
    
    def verify_data_availability(self):
        """Verificar qué combinaciones tienen datos suficientes"""
        print("Verificando disponibilidad de datos para combinaciones conocidas...")
        
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
                    print(f"  ✅ {pair} {timeframe}: {count:,} registros")
                else:
                    print(f"  ⚠️ {pair} {timeframe}: {count:,} registros (necesita {min_required})")
                    
            except Exception as e:
                print(f"  ❌ Error verificando {pair} {timeframe}: {e}")
        
        return viable_combinations
    
    def load_timeframe_data(self, pair, timeframe, max_records=15000):
        """Cargar datos optimizado por timeframe"""
        try:
            print(f"    Cargando {pair} {timeframe}...")
            
            # Ajustar cantidad de datos a cargar según timeframe
            if timeframe in ["1min", "5min"]:
                load_limit = min(max_records, 10000)  # Máximo 10k para timeframes cortos
            elif timeframe in ["15min", "30min"]:
                load_limit = min(max_records, 15000)  # Hasta 15k para timeframes medianos
            else:
                load_limit = min(max_records, 20000)  # Hasta 20k para timeframes largos
            
            result = supabase.table("forex_candles") \
                .select("*") \
                .eq("pair", pair) \
                .eq("timeframe", timeframe) \
                .order("datetime", desc=True) \
                .limit(load_limit) \
                .execute()
            
            if not result.data:
                return None
            
            df = pd.DataFrame(result.data)
            df['datetime'] = pd.to_datetime(df['datetime'])
            df['color'] = df.apply(lambda row: 'green' if row['close'] >= row['open'] else 'red', axis=1)
            
            # Ordenar cronológicamente para análisis
            df = df.sort_values('datetime').reset_index(drop=True)
            
            green_pct = len(df[df['color'] == 'green'])/len(df)*100
            date_range = (df['datetime'].max() - df['datetime'].min()).days
            print(f"      {len(df):,} registros, {green_pct:.1f}% verdes, {date_range} días")
            
            return df
            
        except Exception as e:
            print(f"      Error: {e}")
            return None
    
    def analyze_sequences(self, df, timeframe, min_length=2, max_length=5):
        """Analizar secuencias de velas"""
        config = self.timeframe_config[timeframe]
        min_occurrences = config["min_occurrences"]
        effectiveness_threshold = config["effectiveness_threshold"]
        
        # Ajustar longitud de secuencias según timeframe
        if timeframe in ["1d", "1w", "1M"]:
            max_length = 3
        elif timeframe in ["4h"]:
            max_length = 4
        
        all_sequences = {}
        
        for seq_length in range(min_length, max_length + 1):
            for i in range(len(df) - seq_length):
                sequence = tuple(df.iloc[i:i+seq_length]['color'].tolist())
                
                if i + seq_length < len(df):
                    next_color = df.iloc[i + seq_length]['color']
                    
                    seq_key = f"SEQ_{seq_length}_{sequence}"
                    if seq_key not in all_sequences:
                        all_sequences[seq_key] = []
                    
                    all_sequences[seq_key].append(next_color)
        
        # Filtrar secuencias efectivas
        effective_sequences = {}
        for seq_key, outcomes in all_sequences.items():
            if len(outcomes) >= min_occurrences:
                green_count = sum(1 for outcome in outcomes if outcome == 'green')
                effectiveness = green_count / len(outcomes)
                
                if effectiveness >= effectiveness_threshold or effectiveness <= (1 - effectiveness_threshold):
                    bias = 'green' if effectiveness >= 0.5 else 'red'
                    final_effectiveness = effectiveness if bias == 'green' else (1 - effectiveness)
                    
                    sequence_tuple = eval(seq_key.split('_', 2)[2])
                    seq_length = int(seq_key.split('_')[1])
                    
                    effective_sequences[seq_key] = {
                        'sequence': sequence_tuple,
                        'length': seq_length,
                        'bias': bias,
                        'effectiveness': final_effectiveness,
                        'occurrences': len(outcomes),
                        'green_count': green_count,
                        'red_count': len(outcomes) - green_count
                    }
        
        return effective_sequences
    
    def format_pattern_for_storage(self, strategy_data):
        """Convertir patrón a formato R/V"""
        if strategy_data['type'] == 'sequence':
            sequence = strategy_data['pattern']['sequence']
            pattern_str = ''.join(['R' if color == 'red' else 'V' for color in sequence])
            direction = 'CALL' if strategy_data['bias'] == 'green' else 'PUT'
            
            length = len(sequence)
            if all(c == sequence[0] for c in sequence):
                color_name = 'red' if sequence[0] == 'red' else 'green'
                trigger = f"After {length} consecutive {color_name} candles"
            else:
                trigger = f"After {length} consecutive {pattern_str} candles"
                
            return pattern_str, direction, trigger
        
        return "UNKNOWN", "CALL", "Unknown pattern"
    
    def save_strategy_to_master(self, strategy_data, pair, timeframe):
        """Guardar estrategia en formato limpio"""
        try:
            pattern_str, direction, trigger_condition = self.format_pattern_for_storage(strategy_data)
            
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
                'source': 'direct_multi_analyzer',
                'validation_method': 'historical_analysis',
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
    
    def analyze_all_available_data(self):
        """Analizar todas las combinaciones viables"""
        print("ANALIZADOR MULTI-TIMEFRAME DIRECTO")
        print("=" * 60)
        
        # Verificar datos disponibles
        viable_combinations = self.verify_data_availability()
        
        if not viable_combinations:
            print("No hay combinaciones viables para análisis")
            return 0
        
        print(f"\nCombinaciones viables encontradas: {len(viable_combinations)}")
        print(f"Iniciando análisis...")
        
        total_strategies = 0
        
        for i, (pair, timeframe, record_count) in enumerate(viable_combinations, 1):
            print(f"\n[{i}/{len(viable_combinations)}] Analizando {pair} {timeframe} ({record_count:,} registros)")
            
            # Cargar datos
            df = self.load_timeframe_data(pair, timeframe)
            if df is None:
                print(f"    ❌ Error cargando datos")
                continue
            
            # Analizar secuencias
            sequences = self.analyze_sequences(df, timeframe)
            
            if not sequences:
                print(f"    ⚠️ No se encontraron patrones efectivos")
                continue
            
            print(f"    📊 {len(sequences)} patrones encontrados")
            
            # Guardar estrategias
            saved_count = 0
            for seq_key, seq_data in sequences.items():
                strategy = {
                    'type': 'sequence',
                    'name': f"SEQ_{seq_data['length']}velas_{seq_data['effectiveness']:.0%}_{seq_data['occurrences']}occ",
                    'pattern': seq_data,
                    'effectiveness': seq_data['effectiveness'],
                    'occurrences': seq_data['occurrences'],
                    'bias': seq_data['bias']
                }
                
                if self.save_strategy_to_master(strategy, pair, timeframe):
                    saved_count += 1
            
            print(f"    💾 {saved_count} estrategias guardadas")
            total_strategies += saved_count
        
        print(f"\n{'='*60}")
        print(f"ANÁLISIS COMPLETADO")
        print(f"Total estrategias descubiertas: {total_strategies}")
        print(f"Combinaciones analizadas: {len(viable_combinations)}")
        print(f"{'='*60}")
        
        return total_strategies

def main():
    analyzer = DirectMultiTimeframeAnalyzer()
    
    print("ANALIZADOR MULTI-TIMEFRAME DIRECTO")
    print("Este script analiza directamente las combinaciones conocidas")
    print("sin depender de consultas complejas a Supabase")
    
    confirm = input("\n¿Proceder con el análisis completo? (s/n): ")
    
    if confirm.lower() in ['s', 'si', 'y', 'yes']:
        total = analyzer.analyze_all_available_data()
        
        if total > 0:
            print(f"\n🎉 ¡ANÁLISIS COMPLETADO EXITOSAMENTE!")
            print(f"Se descubrieron {total} estrategias")
            print(f"Tu sistema web ahora tiene estrategias para múltiples timeframes!")
        else:
            print(f"\n⚠️ No se encontraron estrategias efectivas")
    else:
        print("Análisis cancelado.")

if __name__ == "__main__":
    main()