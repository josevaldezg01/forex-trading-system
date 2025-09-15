# backend/expand_strategies_timeframes.py
import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    print(f"📄 Cargando .env desde: {env_path}")
except ImportError:
    pass

from supabase_client import create_supabase_client

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TimeframeExpander:
    """Expandir estrategias existentes a múltiples temporalidades"""
    
    # Temporalidades objetivo
    TARGET_TIMEFRAMES = ['1m', '5m', '15m', '30m', '1h', '4h']
    
    # Factores de ajuste por temporalidad
    TIMEFRAME_ADJUSTMENTS = {
        '1m': {'score_factor': 1.0, 'effectiveness_adj': 0},     # Base
        '5m': {'score_factor': 1.05, 'effectiveness_adj': 2},   # Ligeramente mejor
        '15m': {'score_factor': 1.1, 'effectiveness_adj': 3},   # Mejor para patrones
        '30m': {'score_factor': 1.08, 'effectiveness_adj': 2},  # Buena estabilidad
        '1h': {'score_factor': 1.15, 'effectiveness_adj': 4},   # Muy estable
        '4h': {'score_factor': 1.2, 'effectiveness_adj': 5}     # Máxima estabilidad
    }
    
    def __init__(self):
        self.db_client = create_supabase_client()
    
    def get_base_strategies(self) -> List[Dict[str, Any]]:
        """Obtener estrategias base (solo 1d por ahora)"""
        try:
            all_strategies = self.db_client.get_recent_strategies(limit=1000)
            
            # Filtrar solo estrategias de 1d
            base_strategies = [s for s in all_strategies if s.get('timeframe') == '1d']
            
            logger.info(f"📊 Obtenidas {len(base_strategies)} estrategias base de 1d")
            return base_strategies
        except Exception as e:
            logger.error(f"❌ Error obteniendo estrategias base: {e}")
            return []
    
    def create_timeframe_variant(self, base_strategy: Dict[str, Any], target_timeframe: str) -> Dict[str, Any]:
        """Crear variante de estrategia para una temporalidad específica"""
        
        if target_timeframe not in self.TIMEFRAME_ADJUSTMENTS:
            return None
        
        adjustments = self.TIMEFRAME_ADJUSTMENTS[target_timeframe]
        
        # Calcular métricas ajustadas
        base_effectiveness = base_strategy['effectiveness']
        new_effectiveness = min(95.0, base_effectiveness + adjustments['effectiveness_adj'])
        
        base_score = base_strategy['score']
        new_score = base_score * adjustments['score_factor']
        
        # Crear estrategia para nueva temporalidad
        variant = {
            'pair': base_strategy['pair'],
            'timeframe': target_timeframe,
            'pattern': base_strategy['pattern'],
            'direction': base_strategy['direction'],
            'effectiveness': round(new_effectiveness, 1),
            'occurrences': base_strategy['occurrences'],  # Mantener ocurrencias base
            'wins': base_strategy['wins'],
            'losses': base_strategy['losses'],
            'avg_profit': base_strategy['avg_profit'],
            'score': round(new_score, 1),
            'trigger_condition': base_strategy.get('trigger_condition', f"prev_sequence == '{base_strategy['pattern']}'"),
            'description': base_strategy.get('description', f"Después de secuencia {base_strategy['pattern']} → Vela {base_strategy.get('predicted_candle', 'V' if base_strategy['direction'] == 'CALL' else 'R')}").replace('1d', target_timeframe),
            'predicted_candle': base_strategy.get('predicted_candle', 'V' if base_strategy['direction'] == 'CALL' else 'R'),
            'type': base_strategy.get('type', 'pattern_strategy'),
            'analysis_date': datetime.now(timezone.utc).isoformat(),
            'base_strategy_id': base_strategy.get('id'),
            'is_projection': True,  # Marcar como proyección
            'source_timeframe': '1d'  # Indicar de dónde viene
        }
        
        return variant
    
    def check_variant_exists(self, variant: Dict[str, Any], existing: List[Dict[str, Any]]) -> bool:
        """Verificar si ya existe una variante similar"""
        for strategy in existing:
            if (strategy['pair'] == variant['pair'] and
                strategy['timeframe'] == variant['timeframe'] and
                strategy['pattern'] == variant['pattern'] and
                strategy['direction'] == variant['direction']):
                return True
        return False
    
    def expand_all_timeframes(self, dry_run: bool = True) -> Dict[str, Any]:
        """Expandir todas las estrategias a múltiples temporalidades"""
        try:
            logger.info("🔄 Iniciando expansión a múltiples temporalidades")
            
            # Obtener estrategias base
            base_strategies = self.get_base_strategies()
            if not base_strategies:
                logger.error("❌ No se encontraron estrategias base")
                return {'error': 'No se encontraron estrategias base'}
            
            # Obtener estrategias existentes para verificar duplicados
            all_existing = self.db_client.get_recent_strategies(limit=2000)
            
            created_variants = []
            skipped_variants = []
            
            # Procesar cada estrategia base
            for base_strategy in base_strategies:
                logger.info(f"📈 Procesando: {base_strategy['pair']} {base_strategy['pattern']}")
                
                # Crear variantes para cada temporalidad
                for timeframe in self.TARGET_TIMEFRAMES:
                    variant = self.create_timeframe_variant(base_strategy, timeframe)
                    if variant is None:
                        continue
                    
                    # Verificar si ya existe
                    if self.check_variant_exists(variant, all_existing):
                        skipped_variants.append(f"{variant['pair']} {variant['timeframe']} {variant['pattern']}")
                        continue
                    
                    created_variants.append(variant)
                    
                    # Mostrar preview
                    logger.info(f"  ✨ {timeframe}: {variant['direction']} {variant['effectiveness']:.1f}% (score: {variant['score']:.1f})")
            
            # Insertar en base de datos si no es dry run
            inserted_count = 0
            if not dry_run and created_variants:
                logger.info(f"💾 Insertando {len(created_variants)} variantes de temporalidad...")
                
                # Insertar en lotes para mejor rendimiento
                batch_size = 50
                for i in range(0, len(created_variants), batch_size):
                    batch = created_variants[i:i+batch_size]
                    
                    for variant in batch:
                        if self.db_client.insert_strategy(variant):
                            inserted_count += 1
                        else:
                            logger.error(f"❌ Error insertando {variant['pair']} {variant['timeframe']} {variant['pattern']}")
                    
                    logger.info(f"📦 Lote {i//batch_size + 1}: {len(batch)} variantes procesadas")
            
            # Resultados
            results = {
                'base_strategies': len(base_strategies),
                'target_timeframes': len(self.TARGET_TIMEFRAMES),
                'variants_created': len(created_variants),
                'variants_inserted': inserted_count,
                'skipped': len(skipped_variants),
                'skipped_list': skipped_variants[:10],  # Solo primeras 10
                'dry_run': dry_run
            }
            
            # Resumen por temporalidad
            timeframe_summary = {}
            for variant in created_variants:
                tf = variant['timeframe']
                if tf not in timeframe_summary:
                    timeframe_summary[tf] = 0
                timeframe_summary[tf] += 1
            
            # Mostrar resumen
            logger.info("📊 RESUMEN DE EXPANSIÓN:")
            logger.info(f"   Estrategias base (1d): {results['base_strategies']}")
            logger.info(f"   Temporalidades objetivo: {results['target_timeframes']}")
            logger.info(f"   Variantes creadas: {results['variants_created']}")
            logger.info(f"   Variantes insertadas: {results['variants_inserted']}")
            logger.info(f"   Saltadas (ya existen): {results['skipped']}")
            
            logger.info("\n📈 DISTRIBUCIÓN POR TEMPORALIDAD:")
            for tf, count in sorted(timeframe_summary.items()):
                logger.info(f"   {tf}: {count} estrategias")
            
            if dry_run:
                logger.info("🧪 MODO DRY RUN - No se insertaron variantes")
                logger.info("💡 Ejecuta con --execute para insertar realmente")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error expandiendo temporalidades: {e}")
            return {'error': str(e)}
    
    def show_preview(self, limit: int = 3):
        """Mostrar preview de expansión"""
        try:
            base_strategies = self.get_base_strategies()
            
            print(f"\n🔍 PREVIEW DE EXPANSIÓN A TEMPORALIDADES (top {limit}):")
            print("=" * 80)
            
            for i, base_strategy in enumerate(base_strategies[:limit]):
                print(f"\n{i+1}. {base_strategy['pair']} {base_strategy['pattern']} {base_strategy['direction']}")
                print(f"   Base (1d): {base_strategy['effectiveness']:.1f}% (score: {base_strategy['score']:.1f})")
                
                print("   Expansiones:")
                for tf in self.TARGET_TIMEFRAMES:
                    variant = self.create_timeframe_variant(base_strategy, tf)
                    if variant:
                        print(f"     {tf}: {variant['effectiveness']:.1f}% (score: {variant['score']:.1f})")
            
            if len(base_strategies) > limit:
                print(f"\n... y {len(base_strategies) - limit} estrategias más")
            
            total_variants = len(base_strategies) * len(self.TARGET_TIMEFRAMES)
            print(f"\n📊 TOTAL ESPERADO: {total_variants} variantes de temporalidad")
                
        except Exception as e:
            logger.error(f"❌ Error en preview: {e}")
    
    def show_current_distribution(self):
        """Mostrar distribución actual de estrategias por temporalidad"""
        try:
            all_strategies = self.db_client.get_recent_strategies(limit=2000)
            
            # Contar por temporalidad
            timeframe_counts = {}
            for strategy in all_strategies:
                tf = strategy.get('timeframe', 'unknown')
                timeframe_counts[tf] = timeframe_counts.get(tf, 0) + 1
            
            print("\n📊 DISTRIBUCIÓN ACTUAL DE ESTRATEGIAS:")
            print("=" * 50)
            total = 0
            for tf, count in sorted(timeframe_counts.items()):
                print(f"   {tf}: {count} estrategias")
                total += count
            
            print(f"\n   TOTAL: {total} estrategias")
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo distribución: {e}")

def main():
    """Función principal"""
    try:
        expander = TimeframeExpander()
        
        # Verificar argumentos
        execute = '--execute' in sys.argv
        preview = '--preview' in sys.argv
        status = '--status' in sys.argv
        
        if status:
            expander.show_current_distribution()
            return
        
        if preview:
            expander.show_preview(5)
            return
        
        if execute:
            print("⚠️ MODO EJECUCIÓN: Se insertarán variantes de temporalidad en la base de datos")
            expander.show_current_distribution()
            confirm = input("\n¿Continuar con la expansión? (y/N): ")
            if confirm.lower() != 'y':
                print("❌ Operación cancelada")
                return
            
            results = expander.expand_all_timeframes(dry_run=False)
        else:
            print("🧪 MODO DRY RUN: Solo simulación, no se insertará nada")
            results = expander.expand_all_timeframes(dry_run=True)
        
        if 'error' in results:
            print(f"❌ Error: {results['error']}")
            sys.exit(1)
        
        print("\n✅ Proceso completado exitosamente")
        
    except KeyboardInterrupt:
        print("\n⚠️ Operación interrumpida por usuario")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🔄 EXPANSOR DE TEMPORALIDADES")
    print("=" * 40)
    print("Opciones:")
    print("  python expand_strategies_timeframes.py           # Dry run (simulación)")
    print("  python expand_strategies_timeframes.py --preview # Ver preview")
    print("  python expand_strategies_timeframes.py --status  # Ver distribución actual")
    print("  python expand_strategies_timeframes.py --execute # Ejecutar realmente")
    print()
    
    main()