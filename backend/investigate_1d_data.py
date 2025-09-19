# backend/investigate_1d_data.py
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

# Agregar directorio padre al path
sys.path.append(str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    print(f"📄 Cargando .env desde: {env_path}")
except ImportError:
    print("⚠️ python-dotenv no instalado")

from supabase_client import create_supabase_client

def investigate_daily_data():
    """Investigar por qué los datos de 1d tienen efectividades anómalas"""
    
    print("🔍 Investigando datos diarios anómalos...")
    supabase = create_supabase_client()
    
    if not supabase:
        print("❌ No se pudo conectar a Supabase")
        return
    
    # Analizar cada par por separado
    test_pairs = ['EURUSD', 'GBPUSD', 'USDJPY']
    
    for pair in test_pairs:
        print(f"\n" + "="*60)
        print(f"🔍 ANALIZANDO {pair} TIMEFRAME 1D")
        print("="*60)
        
        try:
            # Obtener datos de 1d
            response = supabase.client.table('forex_candles').select('*').eq('pair', pair).eq('timeframe', '1d').order('datetime', desc=False).limit(100).execute()
            
            if not response.data:
                print(f"⚠️ No hay datos para {pair} 1d")
                continue
            
            df = pd.DataFrame(response.data)
            
            print(f"📊 Total velas: {len(df)}")
            print(f"📅 Rango: {df['datetime'].iloc[0]} → {df['datetime'].iloc[-1]}")
            
            # Análisis OHLC detallado
            print(f"\n📈 Análisis de precios OHLC:")
            print(f"   Open  - Min: {df['open'].min():.5f}, Max: {df['open'].max():.5f}")
            print(f"   High  - Min: {df['high'].min():.5f}, Max: {df['high'].max():.5f}")
            print(f"   Low   - Min: {df['low'].min():.5f}, Max: {df['low'].max():.5f}")
            print(f"   Close - Min: {df['close'].min():.5f}, Max: {df['close'].max():.5f}")
            
            # Calcular tipos de velas
            df['candle_type'] = df.apply(lambda row: 'V' if row['close'] >= row['open'] else 'R', axis=1)
            
            candle_counts = df['candle_type'].value_counts()
            print(f"\n🕯️ Distribución de velas:")
            for candle_type, count in candle_counts.items():
                percentage = (count / len(df)) * 100
                print(f"   {candle_type}: {count} velas ({percentage:.1f}%)")
            
            # Verificar si hay velas duplicadas o problemas
            print(f"\n🔍 Verificación de datos:")
            
            # Velas con Open = Close (dojis perfectos)
            dojis = df[df['open'] == df['close']]
            print(f"   Dojis perfectos (Open=Close): {len(dojis)}")
            
            # Velas con High = Low (sin rango)
            no_range = df[df['high'] == df['low']]
            print(f"   Velas sin rango (High=Low): {len(no_range)}")
            
            # Velas con datos idénticos consecutivos
            duplicates = 0
            for i in range(1, len(df)):
                if (df.iloc[i]['open'] == df.iloc[i-1]['open'] and 
                    df.iloc[i]['high'] == df.iloc[i-1]['high'] and
                    df.iloc[i]['low'] == df.iloc[i-1]['low'] and
                    df.iloc[i]['close'] == df.iloc[i-1]['close']):
                    duplicates += 1
            print(f"   Velas con OHLC idéntico consecutivo: {duplicates}")
            
            # Mostrar primeras 10 velas para inspección manual
            print(f"\n📋 Primeras 10 velas:")
            print(df[['datetime', 'open', 'high', 'low', 'close', 'candle_type']].head(10).to_string(index=False))
            
            # Mostrar últimas 10 velas
            print(f"\n📋 Últimas 10 velas:")
            print(df[['datetime', 'open', 'high', 'low', 'close', 'candle_type']].tail(10).to_string(index=False))
            
            # Análisis de secuencias
            print(f"\n🔗 Análisis de secuencias:")
            sequence = df['candle_type'].tolist()
            
            # Contar secuencias largas del mismo tipo
            max_v_sequence = 0
            max_r_sequence = 0
            current_v = 0
            current_r = 0
            
            for candle in sequence:
                if candle == 'V':
                    current_v += 1
                    current_r = 0
                    max_v_sequence = max(max_v_sequence, current_v)
                else:  # 'R'
                    current_r += 1
                    current_v = 0
                    max_r_sequence = max(max_r_sequence, current_r)
            
            print(f"   Máxima secuencia de V consecutivas: {max_v_sequence}")
            print(f"   Máxima secuencia de R consecutivas: {max_r_sequence}")
            
            # Mostrar la secuencia completa (primeros 50 para no saturar)
            sequence_str = ''.join(sequence[:50])
            print(f"   Secuencia (primeros 50): {sequence_str}")
            if len(sequence) > 50:
                sequence_str_end = ''.join(sequence[-20:])
                print(f"   Secuencia (últimos 20): {sequence_str_end}")
            
            # Análisis estadístico de cambios de precio
            print(f"\n📊 Análisis de cambios de precio:")
            df['price_change'] = df['close'] - df['open']
            df['price_change_pct'] = (df['price_change'] / df['open']) * 100
            
            print(f"   Cambio promedio: {df['price_change'].mean():.5f}")
            print(f"   Cambio máximo: {df['price_change'].max():.5f}")
            print(f"   Cambio mínimo: {df['price_change'].min():.5f}")
            print(f"   Desviación estándar: {df['price_change'].std():.5f}")
            
            # Verificar si hay un bias direccional extremo
            positive_changes = len(df[df['price_change'] > 0])
            negative_changes = len(df[df['price_change'] < 0])
            neutral_changes = len(df[df['price_change'] == 0])
            
            print(f"   Cambios positivos: {positive_changes} ({positive_changes/len(df)*100:.1f}%)")
            print(f"   Cambios negativos: {negative_changes} ({negative_changes/len(df)*100:.1f}%)")
            print(f"   Sin cambio: {neutral_changes} ({neutral_changes/len(df)*100:.1f}%)")
            
            # Buscar el problema específico del overfitting
            print(f"\n🚨 DIAGNÓSTICO DEL PROBLEMA:")
            
            # Si hay demasiadas velas del mismo tipo seguidas
            v_percentage = candle_counts.get('V', 0) / len(df) * 100
            r_percentage = candle_counts.get('R', 0) / len(df) * 100
            
            if v_percentage > 80 or r_percentage > 80:
                dominant_type = 'Verde' if v_percentage > r_percentage else 'Roja'
                print(f"   🔥 PROBLEMA ENCONTRADO: {dominant_type} domina con {max(v_percentage, r_percentage):.1f}%")
                print(f"   📈 Esto causa que el patrón 'V → V' o 'R → R' tenga ~99% efectividad")
                print(f"   💡 Los datos pueden estar sesgados o tener un trend extremo")
            
            # Si hay muchas secuencias largas
            if max_v_sequence > 10 or max_r_sequence > 10:
                print(f"   🔥 PROBLEMA: Secuencias muy largas detectadas")
                print(f"   📈 Secuencias largas causan overfitting en patrones simples")
            
            # Si hay demasiados cambios positivos/negativos
            if positive_changes / len(df) > 0.9 or negative_changes / len(df) > 0.9:
                bias_direction = "alcista" if positive_changes > negative_changes else "bajista"
                bias_percentage = max(positive_changes, negative_changes) / len(df) * 100
                print(f"   🔥 PROBLEMA: Bias {bias_direction} extremo ({bias_percentage:.1f}%)")
                print(f"   📈 Esto hace que casi todas las velas sean del mismo tipo")
                
        except Exception as e:
            print(f"❌ Error analizando {pair}: {e}")
            import traceback
            traceback.print_exc()

def compare_1h_vs_1d():
    """Comparar datos de 1h vs 1d para el mismo par"""
    
    print(f"\n" + "="*80)
    print("📊 COMPARACIÓN 1H vs 1D - EURUSD")
    print("="*80)
    
    supabase = create_supabase_client()
    
    try:
        # Datos de 1h
        response_1h = supabase.client.table('forex_candles').select('*').eq('pair', 'EURUSD').eq('timeframe', '1h').order('datetime', desc=False).limit(50).execute()
        df_1h = pd.DataFrame(response_1h.data)
        
        # Datos de 1d  
        response_1d = supabase.client.table('forex_candles').select('*').eq('pair', 'EURUSD').eq('timeframe', '1d').order('datetime', desc=False).limit(50).execute()
        df_1d = pd.DataFrame(response_1d.data)
        
        print(f"\n📈 DATOS 1H ({len(df_1h)} velas):")
        df_1h['candle_type'] = df_1h.apply(lambda row: 'V' if row['close'] >= row['open'] else 'R', axis=1)
        v_count_1h = len(df_1h[df_1h['candle_type'] == 'V'])
        r_count_1h = len(df_1h[df_1h['candle_type'] == 'R'])
        
        print(f"   Velas Verdes: {v_count_1h} ({v_count_1h/len(df_1h)*100:.1f}%)")
        print(f"   Velas Rojas: {r_count_1h} ({r_count_1h/len(df_1h)*100:.1f}%)")
        
        sequence_1h = ''.join(df_1h['candle_type'].tolist()[:30])
        print(f"   Secuencia: {sequence_1h}")
        
        print(f"\n📈 DATOS 1D ({len(df_1d)} velas):")
        df_1d['candle_type'] = df_1d.apply(lambda row: 'V' if row['close'] >= row['open'] else 'R', axis=1)
        v_count_1d = len(df_1d[df_1d['candle_type'] == 'V'])
        r_count_1d = len(df_1d[df_1d['candle_type'] == 'R'])
        
        print(f"   Velas Verdes: {v_count_1d} ({v_count_1d/len(df_1d)*100:.1f}%)")
        print(f"   Velas Rojas: {r_count_1d} ({r_count_1d/len(df_1d)*100:.1f}%)")
        
        sequence_1d = ''.join(df_1d['candle_type'].tolist()[:30])
        print(f"   Secuencia: {sequence_1d}")
        
        print(f"\n🔍 DIFERENCIAS CLAVE:")
        diff_v = abs(v_count_1h/len(df_1h) - v_count_1d/len(df_1d)) * 100
        print(f"   Diferencia en % de velas verdes: {diff_v:.1f} puntos porcentuales")
        
        if v_count_1d/len(df_1d) > 0.9:
            print(f"   🚨 PROBLEMA CONFIRMADO: 1d tiene {v_count_1d/len(df_1d)*100:.1f}% velas verdes")
            print(f"   💡 Esto explica por qué 'V → V' tiene ~99% efectividad")
        
    except Exception as e:
        print(f"❌ Error en comparación: {e}")

if __name__ == "__main__":
    print("🔍 Iniciando investigación de datos diarios anómalos...")
    
    # Investigación detallada
    investigate_daily_data()
    
    # Comparación 1h vs 1d
    compare_1h_vs_1d()
    
    print(f"\n🎯 Investigación completada")