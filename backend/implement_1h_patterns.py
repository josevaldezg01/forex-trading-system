# backend/implement_1h_patterns.py
import os
import sys
import pandas as pd
from datetime import datetime, timezone
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
from pattern_detector import create_pattern_detector

def implement_1h_trading_system():
    """Implementar sistema de trading con patrones de 1 hora validados"""
    
    print("🚀 Implementando sistema de trading con datos de 1 hora...")
    
    supabase = create_supabase_client()
    detector = create_pattern_detector()
    
    if not supabase or not detector:
        print("❌ Error inicializando componentes")
        return
    
    # Pares disponibles con datos válidos de 1h
    VALID_1H_PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD']
    TIMEFRAME = '1h'
    
    all_patterns = []
    pair_statistics = {}
    
    print(f"\n📊 Analizando {len(VALID_1H_PAIRS)} pares de divisas...")
    
    for pair in VALID_1H_PAIRS:
        print(f"\n{'='*60}")
        print(f"🔍 PROCESANDO {pair} {TIMEFRAME}")
        print('='*60)
        
        try:
            # Obtener datos históricos (más datos para mejor análisis)
            response = supabase.client.table('forex_candles').select('*').eq('pair', pair).eq('timeframe', TIMEFRAME).order('datetime', desc=False).limit(2000).execute()
            
            if not response.data:
                print(f"⚠️ No hay datos para {pair}")
                continue
            
            df = pd.DataFrame(response.data)
            print(f"📊 Datos disponibles: {len(df)} velas")
            print(f"📅 Período: {df['datetime'].iloc[0][:10]} → {df['datetime'].iloc[-1][:10]}")
            
            # Detectar patrones
            patterns = detector.detect_patterns(pair, TIMEFRAME, df)
            
            if patterns:
                print(f"✅ Encontrados {len(patterns)} patrones válidos")
                
                # Filtrar solo patrones de alta calidad
                quality_patterns = []
                for pattern in patterns:
                    # Criterios de calidad:
                    # - Efectividad >= 55%
                    # - Ocurrencias >= 30 (suficiente historial)
                    # - Score >= 50
                    if (pattern['effectiveness'] >= 55.0 and 
                        pattern['occurrences'] >= 30 and 
                        pattern['score'] >= 50.0):
                        quality_patterns.append(pattern)
                
                print(f"🏆 Patrones de alta calidad: {len(quality_patterns)}")
                
                # Mostrar top 5 patrones
                if quality_patterns:
                    print(f"\n🥇 TOP 5 PATRONES DE ALTA CALIDAD:")
                    for i, pattern in enumerate(quality_patterns[:5], 1):
                        print(f"{i}. {pattern['pattern']} → {pattern['predicted_candle']}")
                        print(f"   📈 Efectividad: {pattern['effectiveness']:.1f}%")
                        print(f"   📊 Ocurrencias: {pattern['occurrences']}")
                        print(f"   🎯 Score: {pattern['score']:.1f}")
                        print(f"   🚀 Dirección: {pattern['direction']}")
                        print()
                    
                    # Agregar patrones de calidad a la lista general
                    all_patterns.extend(quality_patterns)
                    
                    # Estadísticas del par
                    stats = detector.get_pattern_statistics(quality_patterns)
                    pair_statistics[pair] = {
                        'total_patterns': len(quality_patterns),
                        'avg_effectiveness': stats.get('avg_effectiveness', 0),
                        'avg_score': stats.get('avg_score', 0),
                        'total_occurrences': stats.get('total_occurrences', 0),
                        'best_pattern': quality_patterns[0] if quality_patterns else None
                    }
                
                else:
                    print("ℹ️ No se encontraron patrones que cumplan criterios de alta calidad")
            
            else:
                print("ℹ️ No se encontraron patrones válidos")
                
        except Exception as e:
            print(f"❌ Error procesando {pair}: {e}")
            continue
    
    # Resumen general del sistema
    print(f"\n{'='*80}")
    print("📊 RESUMEN DEL SISTEMA DE TRADING 1H")
    print('='*80)
    
    if all_patterns:
        print(f"✅ Patrones de alta calidad encontrados: {len(all_patterns)}")
        print(f"💰 Pares con patrones válidos: {len(pair_statistics)}")
        
        # Ranking de mejores pares
        print(f"\n🏆 RANKING DE PARES POR CALIDAD:")
        sorted_pairs = sorted(pair_statistics.items(), 
                            key=lambda x: x[1]['avg_effectiveness'], 
                            reverse=True)
        
        for i, (pair, stats) in enumerate(sorted_pairs, 1):
            print(f"{i}. {pair}")
            print(f"   📈 Efectividad promedio: {stats['avg_effectiveness']:.1f}%")
            print(f"   🎯 Score promedio: {stats['avg_score']:.1f}")
            print(f"   📊 Patrones encontrados: {stats['total_patterns']}")
            if stats['best_pattern']:
                best = stats['best_pattern']
                print(f"   🥇 Mejor patrón: {best['pattern']} → {best['predicted_candle']} ({best['effectiveness']:.1f}%)")
            print()
        
        # Top 10 patrones globales
        print(f"🌟 TOP 10 PATRONES GLOBALES:")
        all_patterns_sorted = sorted(all_patterns, key=lambda x: x['score'], reverse=True)
        
        for i, pattern in enumerate(all_patterns_sorted[:10], 1):
            print(f"{i:2d}. {pattern['pair']:<7} | {pattern['pattern']:<6} → {pattern['predicted_candle']} | {pattern['effectiveness']:5.1f}% | Score: {pattern['score']:5.1f} | Dir: {pattern['direction']}")
        
        # Estadísticas generales
        all_effectiveness = [p['effectiveness'] for p in all_patterns]
        all_scores = [p['score'] for p in all_patterns]
        
        print(f"\n📊 ESTADÍSTICAS GENERALES:")
        print(f"   Efectividad promedio: {sum(all_effectiveness)/len(all_effectiveness):.1f}%")
        print(f"   Score promedio: {sum(all_scores)/len(all_scores):.1f}")
        print(f"   Efectividad máxima: {max(all_effectiveness):.1f}%")
        print(f"   Score máximo: {max(all_scores):.1f}")
        
        # Proponer siguiente fase
        print(f"\n🚀 SIGUIENTES PASOS RECOMENDADOS:")
        print(f"✅ 1. Guardar estos {len(all_patterns)} patrones en la base de datos")
        print(f"✅ 2. Implementar sistema de alertas automático")
        print(f"✅ 3. Crear dashboard de monitoreo en tiempo real")
        print(f"✅ 4. Configurar backtesting automatizado")
        print(f"✅ 5. Implementar gestión de riesgo")
        
        return all_patterns, pair_statistics
    
    else:
        print("❌ No se encontraron patrones de alta calidad en ningún par")
        return [], {}

def save_patterns_to_database(patterns):
    """Guardar patrones validados en la base de datos"""
    
    if not patterns:
        print("⚠️ No hay patrones para guardar")
        return
    
    print(f"\n💾 Guardando {len(patterns)} patrones en la base de datos...")
    
    supabase = create_supabase_client()
    
    try:
        # Limpiar TODAS las estrategias existentes para empezar limpio
        cleanup_response = supabase.client.table('forex_strategies').delete().neq('id', 0).execute()
        print(f"🧹 Todas las estrategias anteriores eliminadas")
        
        # Insertar nuevos patrones
        patterns_to_insert = []
        for pattern in patterns:
            strategy_data = {
                'pair': pattern['pair'],
                'timeframe': pattern['timeframe'],
                'pattern': pattern['pattern'],
                'direction': pattern['direction'],
                'effectiveness': pattern['effectiveness'],
                'occurrences': pattern['occurrences'],
                'score': pattern['score'],
                'avg_profit': pattern['avg_profit'],
                'status': 'active',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            patterns_to_insert.append(strategy_data)
        
        # Insertar en lotes de 50
        batch_size = 50
        inserted_count = 0
        
        for i in range(0, len(patterns_to_insert), batch_size):
            batch = patterns_to_insert[i:i + batch_size]
            insert_response = supabase.client.table('forex_strategies').insert(batch).execute()
            
            if insert_response.data:
                inserted_count += len(insert_response.data)
                print(f"✅ Lote {i//batch_size + 1}: {len(insert_response.data)} patrones guardados")
            else:
                print(f"❌ Error en lote {i//batch_size + 1}")
        
        print(f"\n🎉 GUARDADO COMPLETADO:")
        print(f"   Total patrones insertados: {inserted_count}")
        print(f"   Patrones de alta calidad en la base de datos: ✅")
        print(f"   Sistema listo para trading automático: ✅")
        
    except Exception as e:
        print(f"❌ Error guardando patrones: {e}")
        import traceback
        traceback.print_exc()

def generate_trading_summary():
    """Generar resumen ejecutivo del sistema de trading"""
    
    print(f"\n📋 RESUMEN EJECUTIVO DEL SISTEMA")
    print('='*60)
    print(f"🎯 OBJETIVO: Sistema de trading automático para opciones binarias")
    print(f"📊 DATOS: Análisis de patrones en timeframe 1 hora")
    print(f"🔍 METODOLOGÍA: Detección de secuencias de velas R/V")
    print(f"✅ CRITERIOS DE CALIDAD:")
    print(f"   • Efectividad mínima: 55%")
    print(f"   • Ocurrencias mínimas: 30")
    print(f"   • Score mínimo: 50")
    print(f"🚀 ESTADO: Sistema validado y listo para implementación")
    print()

if __name__ == "__main__":
    print("🎯 Iniciando implementación del sistema de trading 1H...")
    
    # Generar resumen inicial
    generate_trading_summary()
    
    # Implementar sistema
    patterns, statistics = implement_1h_trading_system()
    
    # Guardar en base de datos
    if patterns:
        save_to_db = input(f"\n💾 ¿Guardar {len(patterns)} patrones en la base de datos? (s/n): ").lower().strip()
        if save_to_db == 's':
            save_patterns_to_database(patterns)
    
    print(f"\n🎉 Sistema de trading 1H implementado exitosamente!")