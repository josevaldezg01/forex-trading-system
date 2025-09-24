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

class EURUSDPatternAnalyzer:
    def __init__(self):
        self.discovered_strategies = []
        
    def load_forex_data_batched(self, pair="EURUSD", timeframe="1min", days_back=90, batch_size=50000):
        """Cargar datos en lotes para manejar grandes volúmenes"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            print(f"Cargando datos para {pair} {timeframe} desde {start_date.strftime('%Y-%m-%d')} hasta {end_date.strftime('%Y-%m-%d')}")
            
            # Obtener el total de registros primero
            count_result = supabase.table("forex_candles") \
                .select("*", count="exact") \
                .eq("pair", pair) \
                .eq("timeframe", timeframe) \
                .gte("datetime", start_date.isoformat()) \
                .execute()
            
            total_records = count_result.count if count_result.count else 0
            print(f"Total de registros disponibles: {total_records:,}")
            
            if total_records == 0:
                print("No hay datos disponibles para el período especificado")
                return None
            
            # Cargar en lotes si es muy grande
            if total_records <= batch_size:
                print("Cargando datos completos...")
                result = supabase.table("forex_candles") \
                    .select("*") \
                    .eq("pair", pair) \
                    .eq("timeframe", timeframe) \
                    .gte("datetime", start_date.isoformat()) \
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
                        .gte("datetime", start_date.isoformat()) \
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
            
            # Información del dataset
            green_pct = len(df[df['color'] == 'green']) / len(df) * 100
            print(f"Dataset procesado: {len(df):,} velas ({green_pct:.1f}% verdes, {100-green_pct:.1f}% rojas)")
            print(f"Período: {df['datetime'].min()} a {df['datetime'].max()}")
            
            return df
            
        except Exception as e:
            print(f"Error cargando datos: {e}")
            return None
    
    def analyze_variable_sequences_optimized(self, df, min_length=2, max_length=6, min_occurrences=100, sample_size=200000):
        """Analizar secuencias optimizado para grandes datasets"""
        print(f"\nANÁLISIS DE SECUENCIAS DE VELAS")
        print("=" * 50)
        print(f"Dataset: {len(df):,} registros")
        
        # Si el dataset es muy grande, usar una muestra representativa
        if len(df) > sample_size:
            print(f"Usando muestra representativa de {sample_size:,} registros...")
            # Tomar muestra distribuida a lo largo del tiempo
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
        
        # Filtrar secuencias efectivas con criterios estrictos
        effective_sequences = {}
        print(f"\nEvaluando efectividad (mínimo {min_occurrences} ocurrencias)...")
        
        for seq_key, outcomes in all_sequences.items():
            if len(outcomes) >= min_occurrences:
                green_count = sum(1 for outcome in outcomes if outcome['next_color'] == 'green')
                effectiveness = green_count / len(outcomes)
                
                # Criterios estrictos: 75%+ hacia cualquier dirección
                if effectiveness >= 0.75 or effectiveness <= 0.25:
                    bias = 'green' if effectiveness >= 0.75 else 'red'
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
    
    def analyze_time_fragments_optimized(self, df, fragment_sizes=[5, 10, 15, 30, 60], min_occurrences=200):
        """Análisis de fragmentos temporales optimizado"""
        print(f"\nANÁLISIS DE FRAGMENTOS TEMPORALES")
        print("=" * 50)
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
                    
                    # Criterios estrictos para datasets grandes
                    if effectiveness >= 0.70 or effectiveness <= 0.30:
                        bias = 'green' if effectiveness >= 0.70 else 'red'
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
    
    def analyze_hourly_patterns_extended(self, df, min_occurrences=500):
        """Análisis horario extendido con más detalle"""
        print(f"\nANÁLISIS DE PATRONES HORARIOS")
        print("=" * 50)
        print(f"Dataset: {len(df):,} registros")
        
        hourly_patterns = {}
        
        for hour in range(24):
            hour_data = df[df['hour'] == hour]
            
            if len(hour_data) >= min_occurrences:
                green_count = len(hour_data[hour_data['color'] == 'green'])
                effectiveness = green_count / len(hour_data)
                
                if effectiveness >= 0.65 or effectiveness <= 0.35:
                    bias = 'green' if effectiveness >= 0.65 else 'red'
                    final_effectiveness = effectiveness if bias == 'green' else (1 - effectiveness)
                    
                    # Análisis adicional por día de semana
                    daily_breakdown = {}
                    for day in range(7):  # 0=Monday, 6=Sunday
                        day_hour_data = hour_data[hour_data['day_of_week'] == day]
                        if len(day_hour_data) >= 20:
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
    
    def save_strategy_to_master(self, strategy_data, pair, timeframe):
        """Guardar estrategia descubierta en forex_strategies_master"""
        try:
            strategy_record = {
                'pair': pair,
                'timeframe': timeframe,
                'strategy_type': strategy_data['type'],
                'strategy_name': strategy_data['name'],
                'pattern_data': json.dumps(strategy_data['pattern']),
                'effectiveness': strategy_data['effectiveness'],
                'occurrences': strategy_data['occurrences'],
                'bias': strategy_data['bias'],
                'discovered_at': datetime.now().isoformat(),
                'status': 'discovered',
                'description': strategy_data.get('description', '')
            }
            
            result = supabase.table("forex_strategies_master") \
                .upsert(strategy_record, on_conflict="pair,timeframe,strategy_name") \
                .execute()
                
            return True
            
        except Exception as e:
            print(f"Error guardando estrategia: {e}")
            return False
    
    def comprehensive_pattern_discovery_optimized(self, pair="EURUSD", timeframe="1min", days_back=90):
        """Descubrimiento optimizado para EURUSD"""
        print(f"\n{'='*80}")
        print(f"ANÁLISIS COMPLETO DE PATRONES EURUSD")
        print(f"Período: {days_back} días | Timeframe: {timeframe}")
        print(f"{'='*80}")
        
        # Cargar datos en lotes
        df = self.load_forex_data_batched(pair, timeframe, days_back, batch_size=100000)
        if df is None:
            print("ERROR: No se pudieron cargar los datos")
            return None
        
        discovered_strategies = []
        
        # 1. Analizar secuencias de velas
        sequences = self.analyze_variable_sequences_optimized(
            df, min_length=2, max_length=6, min_occurrences=100, sample_size=200000
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
        
        # 2. Analizar fragmentos temporales
        fragments = self.analyze_time_fragments_optimized(df, min_occurrences=200)
        
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
        
        # 3. Análisis horario
        hourly = self.analyze_hourly_patterns_extended(df, min_occurrences=500)
        
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
        print(f"ANÁLISIS COMPLETADO PARA EURUSD")
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
    analyzer = EURUSDPatternAnalyzer()
    
    print("ANALIZADOR DE PATRONES FOREX")
    print("Datos disponibles en tu base de datos:")
    print("1. AUDJPY 1h (30,000 registros) - MEJOR OPCIÓN")
    print("2. EURUSD 1h (15,000 registros)")
    print("3. USDCHF 1min (11,110 registros)")
    print("4. Ver todos los pares disponibles")
    
    choice = input("\nElige una opción (1/2/3/4): ")
    
    if choice == "1":
        confirm = input("\n¿Analizar AUDJPY en timeframe 1h? (s/n): ")
        if confirm.lower() in ['s', 'si', 'y', 'yes']:
            strategies = analyzer.comprehensive_pattern_discovery_optimized(
                pair="AUDJPY", 
                timeframe="1h", 
                days_back=90
            )
    
    elif choice == "2":
        confirm = input("\n¿Analizar EURUSD en timeframe 1h? (s/n): ")
        if confirm.lower() in ['s', 'si', 'y', 'yes']:
            strategies = analyzer.comprehensive_pattern_discovery_optimized(
                pair="EURUSD", 
                timeframe="1h", 
                days_back=90
            )
    
    elif choice == "3":
        confirm = input("\n¿Analizar USDCHF en timeframe 1min? (s/n): ")
        if confirm.lower() in ['s', 'si', 'y', 'yes']:
            strategies = analyzer.comprehensive_pattern_discovery_optimized(
                pair="USDCHF", 
                timeframe="1min", 
                days_back=30  # Reducido porque son menos registros
            )
    
    elif choice == "4":
        # Mostrar todos los pares con buenos datos
        good_options = [
            ("AUDJPY", "1h", "30,000"),
            ("CADJPY", "1h", "30,000"), 
            ("CHFJPY", "1h", "30,000"),
            ("EURJPY", "1h", "30,000"),
            ("EURUSD", "1h", "15,000"),
            ("GBPUSD", "1h", "15,000"),
            ("USDJPY", "1h", "15,000"),
            ("USDCHF", "1min", "11,110")
        ]
        
        print("\nOpciones recomendadas:")
        for i, (pair, tf, count) in enumerate(good_options, 1):
            print(f"{i}. {pair} {tf} ({count} registros)")
        
        selection = input(f"\nElige un número (1-{len(good_options)}): ")
        try:
            idx = int(selection) - 1
            if 0 <= idx < len(good_options):
                pair, tf, count = good_options[idx]
                confirm = input(f"\n¿Analizar {pair} en {tf}? (s/n): ")
                if confirm.lower() in ['s', 'si', 'y', 'yes']:
                    days = 90 if tf in ['1h', '4h'] else 30
                    strategies = analyzer.comprehensive_pattern_discovery_optimized(
                        pair=pair, 
                        timeframe=tf, 
                        days_back=days
                    )
        except:
            print("Selección inválida")
            return
    
    else:
        print("Opción inválida")
        return

if __name__ == "__main__":
    main()