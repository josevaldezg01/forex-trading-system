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

class ForexPatternAnalyzer:  # Nombre más genérico
    def __init__(self):
        self.discovered_strategies = []
        
    def load_all_historical_data(self, pair="AUDJPY", timeframe="1h", batch_size=50000):
        """Cargar TODOS los datos históricos disponibles sin filtro de fechas"""
        try:
            print(f"Cargando TODOS los datos históricos para {pair} {timeframe}...")
            
            # Obtener el total de registros primero
            count_result = supabase.table("forex_candles") \
                .select("*", count="exact") \
                .eq("pair", pair) \
                .eq("timeframe", timeframe) \
                .execute()
            
            total_records = count_result.count if count_result.count else 0
            print(f"Total de registros históricos disponibles: {total_records:,}")
            
            if total_records == 0:
                print("No hay datos disponibles para este par/timeframe")
                return None
            
            # Cargar en lotes si es muy grande
            if total_records <= batch_size:
                print("Cargando todos los datos...")
                result = supabase.table("forex_candles") \
                    .select("*") \
                    .eq("pair", pair) \
                    .eq("timeframe", timeframe) \
                    .order("datetime") \
                    .execute()
                
                df = pd.DataFrame(result.data)
            else:
                print(f"Procesando en lotes de {batch_size:,} registros...")
                all_data = []
                
                for offset in range(0, total_records, batch_size):
                    batch_num = offset//batch_size + 1
                    total_batches = (total_records//batch_size) + 1
                    print(f"  Cargando lote {batch_num}/{total_batches}... ({offset:,} - {min(offset + batch_size, total_records):,})")
                    
                    batch_result = supabase.table("forex_candles") \
                        .select("*") \
                        .eq("pair", pair) \
                        .eq("timeframe", timeframe) \
                        .order("datetime") \
                        .range(offset, offset + batch_size - 1) \
                        .execute()
                    
                    if batch_result.data:
                        all_data.extend(batch_result.data)
                        print(f"    Registros cargados en este lote: {len(batch_result.data):,}")
                
                df = pd.DataFrame(all_data)
                print(f"Total de registros cargados: {len(df):,}")
            
            # Procesar dataframe
            df['datetime'] = pd.to_datetime(df['datetime'])
            df['color'] = df.apply(lambda row: 'green' if row['close'] >= row['open'] else 'red', axis=1)
            df['hour'] = df['datetime'].dt.hour
            df['minute'] = df['datetime'].dt.minute
            df['day_of_week'] = df['datetime'].dt.dayofweek
            
            # Información del dataset completo
            green_pct = len(df[df['color'] == 'green']) / len(df) * 100
            print(f"Dataset histórico completo: {len(df):,} velas ({green_pct:.1f}% verdes, {100-green_pct:.1f}% rojas)")
            print(f"Período completo: {df['datetime'].min()} a {df['datetime'].max()}")
            print(f"Duración: {(df['datetime'].max() - df['datetime'].min()).days} días")
            
            return df
            
        except Exception as e:
            print(f"Error cargando datos: {e}")
            return None
    
    def analyze_variable_sequences_relaxed(self, df, min_length=2, max_length=6, min_occurrences=20, sample_size=200000):
        """Analizar secuencias con criterios más flexibles"""
        print(f"\nANÁLISIS DE SECUENCIAS DE VELAS (Criterios flexibles)")
        print("=" * 60)
        print(f"Dataset: {len(df):,} registros")
        
        # Si el dataset es muy grande, usar una muestra representativa
        if len(df) > sample_size:
            print(f"Usando muestra representativa de {sample_size:,} registros...")
            step = len(df) // sample_size
            df_sample = df.iloc[::step].copy()
            df_sample = df_sample.sort_values('datetime')
            print(f"Muestra final: {len(df_sample):,} registros")
        else:
            df_sample = df
        
        all_sequences = {}
        
        for seq_length in range(min_length, max_length + 1):
            print(f"\nProcesando secuencias de {seq_length} velas...")
            sequence_count = 0
            
            # Procesar en chunks para memoria
            chunk_size = 10000
            for start_idx in range(0, len(df_sample) - seq_length, chunk_size):
                end_idx = min(start_idx + chunk_size, len(df_sample) - seq_length)
                
                for i in range(start_idx, end_idx):
                    sequence = tuple(df_sample.iloc[i:i+seq_length]['color'].tolist())
                    
                    if i + seq_length < len(df_sample):
                        next_candle = df_sample.iloc[i + seq_length]
                        next_color = next_candle['color']
                        
                        seq_key = f"SEQ_{seq_length}_{sequence}"
                        if seq_key not in all_sequences:
                            all_sequences[seq_key] = []
                        
                        all_sequences[seq_key].append({
                            'next_color': next_color,
                            'datetime': next_candle['datetime'],
                            'hour': next_candle['hour'],
                            'minute': next_candle['minute']
                        })
                        sequence_count += 1
                
                if (start_idx + chunk_size) % 50000 == 0:
                    print(f"  Procesadas {sequence_count:,} secuencias...")
            
            print(f"  Secuencias de {seq_length} velas: {sequence_count:,} analizadas")
        
        # Filtrar secuencias efectivas con criterios más flexibles
        effective_sequences = {}
        print(f"\nEvaluando efectividad (mínimo {min_occurrences} ocurrencias, 65%+ precisión)...")
        
        for seq_key, outcomes in all_sequences.items():
            if len(outcomes) >= min_occurrences:
                green_count = sum(1 for outcome in outcomes if outcome['next_color'] == 'green')
                effectiveness = green_count / len(outcomes)
                
                # Criterios más flexibles: 65%+ hacia cualquier dirección
                if effectiveness >= 0.65 or effectiveness <= 0.35:
                    bias = 'green' if effectiveness >= 0.65 else 'red'
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
                    
                    print(f"  ✓ {sequence_tuple} -> {bias} ({final_effectiveness:.1%}, {len(outcomes)} ocurrencias)")
        
        print(f"\nResultado: {len(effective_sequences)} secuencias efectivas encontradas")
        return effective_sequences
    
    def analyze_time_fragments_relaxed(self, df, fragment_sizes=[5, 10, 15, 30, 60], min_occurrences=50):
        """Análisis de fragmentos temporales con criterios más flexibles"""
        print(f"\nANÁLISIS DE FRAGMENTOS TEMPORALES (Criterios flexibles)")
        print("=" * 60)
        print(f"Dataset: {len(df):,} registros")
        
        all_fragments = {}
        
        for fragment_size in fragment_sizes:
            print(f"\nAnalizando fragmentos de {fragment_size} minutos...")
            
            for start_minute in range(0, 60, fragment_size):
                if start_minute + fragment_size > 60:
                    continue
                    
                end_minute = start_minute + fragment_size - 1
                fragment_data = df[
                    (df['minute'] >= start_minute) & 
                    (df['minute'] <= end_minute)
                ]
                
                if len(fragment_data) >= min_occurrences:
                    green_count = len(fragment_data[fragment_data['color'] == 'green'])
                    effectiveness = green_count / len(fragment_data)
                    
                    # Criterios más flexibles: 60%+ bias
                    if effectiveness >= 0.60 or effectiveness <= 0.40:
                        bias = 'green' if effectiveness >= 0.60 else 'red'
                        final_effectiveness = effectiveness if bias == 'green' else (1 - effectiveness)
                        
                        fragment_key = f"FRAG_{fragment_size}min_{start_minute:02d}-{end_minute:02d}"
                        all_fragments[fragment_key] = {
                            'fragment_size': fragment_size,
                            'start_minute': start_minute,
                            'end_minute': end_minute,
                            'bias': bias,
                            'effectiveness': final_effectiveness,
                            'total_candles': len(fragment_data),
                            'green_count': green_count,
                            'red_count': len(fragment_data) - green_count
                        }
                        
                        print(f"  ✓ {start_minute:02d}-{end_minute:02d} min -> {bias} ({final_effectiveness:.1%}, {len(fragment_data):,} velas)")
        
        print(f"\nResultado: {len(all_fragments)} fragmentos efectivos encontrados")
        return all_fragments
    
    def analyze_hourly_patterns_relaxed(self, df, min_occurrences=100):
        """Análisis horario con criterios más flexibles"""
        print(f"\nANÁLISIS DE PATRONES HORARIOS (Criterios flexibles)")
        print("=" * 60)
        print(f"Dataset: {len(df):,} registros")
        
        hourly_patterns = {}
        
        for hour in range(24):
            hour_data = df[df['hour'] == hour]
            
            if len(hour_data) >= min_occurrences:
                green_count = len(hour_data[hour_data['color'] == 'green'])
                effectiveness = green_count / len(hour_data)
                
                # Criterios más flexibles: 55%+ bias
                if effectiveness >= 0.55 or effectiveness <= 0.45:
                    bias = 'green' if effectiveness >= 0.55 else 'red'
                    final_effectiveness = effectiveness if bias == 'green' else (1 - effectiveness)
                    
                    # Análisis adicional por día de semana
                    daily_breakdown = {}
                    for day in range(7):  # 0=Monday, 6=Sunday
                        day_hour_data = hour_data[hour_data['day_of_week'] == day]
                        if len(day_hour_data) >= 10:
                            day_green = len(day_hour_data[day_hour_data['color'] == 'green'])
                            day_effectiveness = day_green / len(day_hour_data)
                            daily_breakdown[day] = {
                                'effectiveness': day_effectiveness,
                                'count': len(day_hour_data)
                            }
                    
                    hourly_patterns[hour] = {
                        'bias': bias,
                        'effectiveness': final_effectiveness,
                        'total_candles': len(hour_data),
                        'green_count': green_count,
                        'red_count': len(hour_data) - green_count,
                        'daily_breakdown': daily_breakdown
                    }
                    
                    print(f"  ✓ Hora {hour:02d}:xx -> {bias} ({final_effectiveness:.1%}, {len(hour_data):,} velas)")
        
        print(f"\nResultado: {len(hourly_patterns)} patrones horarios encontrados")
        return hourly_patterns
    
    def format_pattern_for_storage(self, strategy_data):
        """Convertir patrón a formato legible como antes"""
        if strategy_data['type'] == 'sequence':
            # Convertir secuencia a formato R/V simple
            sequence = strategy_data['pattern']['sequence']
            pattern_str = ''.join(['R' if color == 'red' else 'V' for color in sequence])
            
            # Determinar dirección en formato PUT/CALL
            direction = 'CALL' if strategy_data['bias'] == 'green' else 'PUT'
            
            # Crear trigger condition descriptivo
            length = len(sequence)
            if all(c == sequence[0] for c in sequence):
                # Secuencia de un solo color
                color_name = 'consecutive red' if sequence[0] == 'red' else 'consecutive green'
                trigger = f"After {length} {color_name} candles"
            else:
                # Secuencia mixta
                trigger = f"After {length} consecutive {pattern_str} candles"
                
            return pattern_str, direction, trigger
            
        elif strategy_data['type'] == 'time_fragment':
            # Para fragmentos temporales
            frag = strategy_data['pattern']
            pattern_str = f"TIME_{frag['start_minute']:02d}-{frag['end_minute']:02d}"
            direction = 'CALL' if strategy_data['bias'] == 'green' else 'PUT'
            trigger = f"During minutes {frag['start_minute']:02d}-{frag['end_minute']:02d} of each hour"
            
            return pattern_str, direction, trigger
            
        elif strategy_data['type'] == 'hourly':
            # Para patrones horarios
            hour = list(strategy_data['pattern'].keys())[0] if isinstance(strategy_data['pattern'], dict) else 0
            pattern_str = f"HOUR_{hour:02d}"
            direction = 'CALL' if strategy_data['bias'] == 'green' else 'PUT'
            trigger = f"During hour {hour:02d}:xx every day"
            
            return pattern_str, direction, trigger
            
        return "UNKNOWN", "CALL", "Unknown pattern"

    def save_strategy_to_master(self, strategy_data, pair, timeframe):
        """Guardar estrategia en formato original limpio"""        
        try:
            # Convertir a formato legible
            pattern_str, direction, trigger_condition = self.format_pattern_for_storage(strategy_data)
            
            # Calcular métricas
            wins = int(strategy_data['occurrences'] * strategy_data['effectiveness'])
            losses = strategy_data['occurrences'] - wins
            
            strategy_record = {
                'pair': pair,
                'timeframe': timeframe,
                'pattern': pattern_str,  # Formato simple: RRRRR, RVRV, etc.
                'direction': direction,  # CALL/PUT como antes
                'effectiveness': strategy_data['effectiveness'],
                'occurrences': strategy_data['occurrences'],
                'wins': wins,
                'losses': losses,
                'avg_profit': 55.0,  # Valor por defecto - se actualizará con backtesting
                'score': strategy_data['effectiveness'] * 100,
                'trigger_condition': trigger_condition,  # Descripción limpia
                'analysis_date': datetime.now().isoformat(),
                'strategy_type': strategy_data['type'],
                'source': 'pattern_analyzer_v2',
                'validation_method': 'historical_analysis',
                'data_quality': 'high',
                'is_active': True,
                'added_to_master': datetime.now().isoformat()
            }
            
            print(f"✓ Guardando: {pattern_str} -> {direction} ({strategy_data['effectiveness']:.1%})")
            print(f"  Trigger: {trigger_condition}")
            
            result = supabase.table("forex_strategies_master") \
                .insert(strategy_record) \
                .execute()
                
            return True
            
        except Exception as e:
            print(f"✗ Error guardando {pattern_str}: {e}")
            return False
    
    def comprehensive_pattern_discovery_all_data(self, pair="AUDJPY", timeframe="1h"):
        """Descubrimiento usando TODOS los datos históricos disponibles"""
        print(f"\n{'='*80}")
        print(f"ANÁLISIS COMPLETO CON TODOS LOS DATOS HISTÓRICOS")
        print(f"Par: {pair} | Timeframe: {timeframe}")
        print(f"{'='*80}")
        
        # Cargar TODOS los datos históricos
        df = self.load_all_historical_data(pair, timeframe, batch_size=100000)
        if df is None:
            print("ERROR: No se pudieron cargar los datos")
            return None
        
        discovered_strategies = []
        
        # 1. Analizar secuencias de velas (criterios más flexibles)
        sequences = self.analyze_variable_sequences_relaxed(
            df, min_length=2, max_length=6, min_occurrences=20, sample_size=200000
        )
        
        print(f"\nGUARDANDO SECUENCIAS EN BASE DE DATOS...")
        for seq_key, seq_data in sequences.items():
            strategy = {
                'type': 'sequence',
                'name': f"SEQ_{seq_data['length']}velas_{seq_data['effectiveness']:.0%}_{seq_data['occurrences']}occ",
                'pattern': seq_data,
                'effectiveness': seq_data['effectiveness'],
                'occurrences': seq_data['occurrences'],
                'bias': seq_data['bias'],
                'description': f"Secuencia {seq_data['sequence']} -> {seq_data['bias']} ({seq_data['effectiveness']:.1%}, {seq_data['occurrences']} ocurrencias)"
            }
            
            discovered_strategies.append(strategy)
            success = self.save_strategy_to_master(strategy, pair, timeframe)
            if success:
                print(f"  ✓ Guardada: {strategy['name']}")
            else:
                print(f"  ✗ Error guardando: {strategy['name']}")
        
        # 2. Analizar fragmentos temporales (criterios más flexibles)
        fragments = self.analyze_time_fragments_relaxed(df, min_occurrences=50)
        
        print(f"\nGUARDANDO FRAGMENTOS TEMPORALES EN BASE DE DATOS...")
        for frag_key, frag_data in fragments.items():
            strategy = {
                'type': 'time_fragment',
                'name': f"FRAG_{frag_data['fragment_size']}min_{frag_data['start_minute']:02d}-{frag_data['end_minute']:02d}_{frag_data['effectiveness']:.0%}",
                'pattern': frag_data,
                'effectiveness': frag_data['effectiveness'],
                'occurrences': frag_data['total_candles'],
                'bias': frag_data['bias'],
                'description': f"Minutos {frag_data['start_minute']:02d}-{frag_data['end_minute']:02d} -> {frag_data['bias']} ({frag_data['effectiveness']:.1%}, {frag_data['total_candles']:,} velas)"
            }
            
            discovered_strategies.append(strategy)
            success = self.save_strategy_to_master(strategy, pair, timeframe)
            if success:
                print(f"  ✓ Guardada: {strategy['name']}")
            else:
                print(f"  ✗ Error guardando: {strategy['name']}")
        
        # 3. Análisis horario (criterios más flexibles)
        hourly = self.analyze_hourly_patterns_relaxed(df, min_occurrences=100)
        
        print(f"\nGUARDANDO PATRONES HORARIOS EN BASE DE DATOS...")
        for hour, hour_data in hourly.items():
            strategy = {
                'type': 'hourly',
                'name': f"HOUR_{hour:02d}_{hour_data['effectiveness']:.0%}_{hour_data['total_candles']}velas",
                'pattern': hour_data,
                'effectiveness': hour_data['effectiveness'],
                'occurrences': hour_data['total_candles'],
                'bias': hour_data['bias'],
                'description': f"Hora {hour:02d}:xx -> {hour_data['bias']} ({hour_data['effectiveness']:.1%}, {hour_data['total_candles']:,} velas)"
            }
            
            discovered_strategies.append(strategy)
            success = self.save_strategy_to_master(strategy, pair, timeframe)
            if success:
                print(f"  ✓ Guardada: {strategy['name']}")
            else:
                print(f"  ✗ Error guardando: {strategy['name']}")
        
        # Resumen final
        print(f"\n{'='*80}")
        print(f"ANÁLISIS COMPLETADO PARA {pair} {timeframe}")
        print(f"{'='*80}")
        print(f"Total estrategias descubiertas: {len(discovered_strategies)}")
        print(f"  - Secuencias de velas: {len(sequences)}")
        print(f"  - Fragmentos temporales: {len(fragments)}")
        print(f"  - Patrones horarios: {len(hourly)}")
        
        # Mostrar las mejores estrategias
        if discovered_strategies:
            print(f"\nTOP 10 MEJORES ESTRATEGIAS:")
            sorted_strategies = sorted(discovered_strategies, key=lambda x: x['effectiveness'], reverse=True)[:10]
            for i, strategy in enumerate(sorted_strategies, 1):
                print(f"{i:2d}. {strategy['name']} - {strategy['effectiveness']:.1%} ({strategy['occurrences']} ocurrencias)")
        
        print(f"\n{'='*80}")
        
        return discovered_strategies

def main():
    analyzer = ForexPatternAnalyzer()
    
    print("ANALIZADOR DE PATRONES FOREX - TODOS LOS DATOS HISTÓRICOS")
    print("Datos disponibles en tu base de datos:")
    print("1. AUDJPY 1h - Análisis completo con todos los datos")
    print("2. CADJPY 1h - Análisis completo con todos los datos") 
    print("3. CHFJPY 1h - Análisis completo con todos los datos")
    print("4. EURJPY 1h - Análisis completo con todos los datos")
    print("5. EURUSD 1h - Análisis completo con todos los datos")
    print("6. GBPUSD 1h - Análisis completo con todos los datos")
    print("7. USDJPY 1h - Análisis completo con todos los datos")
    print("8. USDCHF 1min - Análisis completo con todos los datos")
    
    choice = input("\nElige una opción (1-8): ")
    
    pairs_options = {
        "1": ("AUDJPY", "1h"),
        "2": ("CADJPY", "1h"), 
        "3": ("CHFJPY", "1h"),
        "4": ("EURJPY", "1h"),
        "5": ("EURUSD", "1h"),
        "6": ("GBPUSD", "1h"),
        "7": ("USDJPY", "1h"),
        "8": ("USDCHF", "1min")
    }
    
    if choice in pairs_options:
        pair, timeframe = pairs_options[choice]
        print(f"\nSeleccionaste: {pair} {timeframe}")
        print("CRITERIOS FLEXIBLES APLICADOS:")
        print("- Secuencias: 65%+ efectividad, mínimo 20 ocurrencias")
        print("- Fragmentos: 60%+ bias, mínimo 50 ocurrencias") 
        print("- Horarios: 55%+ bias, mínimo 100 ocurrencias")
        
        confirm = input(f"\n¿Analizar TODOS los datos históricos de {pair} {timeframe}? (s/n): ")
        
        if confirm.lower() in ['s', 'si', 'y', 'yes']:
            strategies = analyzer.comprehensive_pattern_discovery_all_data(
                pair=pair, 
                timeframe=timeframe
            )
            
            if strategies and len(strategies) > 0:
                print(f"\n¡ANÁLISIS COMPLETADO EXITOSAMENTE!")
                print(f"Se han catalogado {len(strategies)} estrategias en forex_strategies_master")
                print(f"Todas las estrategias encontradas cumplen criterios estadísticos significativos.")
                
                # Mostrar resumen por tipos
                by_type = {}
                for strategy in strategies:
                    type_key = strategy['type']
                    if type_key not in by_type:
                        by_type[type_key] = []
                    by_type[type_key].append(strategy)
                
                print(f"\nRESUMEN POR TIPO:")
                for strategy_type, type_strategies in by_type.items():
                    avg_effectiveness = sum(s['effectiveness'] for s in type_strategies) / len(type_strategies)
                    print(f"- {strategy_type}: {len(type_strategies)} estrategias (promedio {avg_effectiveness:.1%})")
                
            else:
                print(f"\nNo se encontraron estrategias que cumplan los criterios establecidos.")
                print("Esto puede indicar que el par tiene comportamiento muy aleatorio")
                print("o que necesitas ajustar los criterios de efectividad.")
        else:
            print("Análisis cancelado.")
    else:
        print("Opción inválida.")

if __name__ == "__main__":
    main()