# backend/create_mirror_strategies.py
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

class MirrorStrategyCreator:
    """Creador de estrategias espejo para patrones complementarios"""
    
    def __init__(self):
        self.db_client = create_supabase_client()
    
    def get_existing_strategies(self) -> List[Dict[str, Any]]:
        """Obtener todas las estrategias existentes"""
        try:
            strategies = self.db_client.get_recent_strategies(limit=1000)
            logger.info(f"📊 Obtenidas {len(strategies)} estrategias existentes")
            return strategies
        except Exception as e:
            logger.error(f"❌ Error obteniendo estrategias: {e}")
            return []
    
    def create_mirror_strategy(self, original: Dict[str, Any]) -> Dict[str, Any]:
        """Crear estrategia espejo de una estrategia verde"""
        # Mapear patrones verdes a rojos
        pattern_mirror = {
            'V': 'R',
            'VV': 'RR', 
            'VVV': 'RRR',
            'VVVV': 'RRRR'
        }
        
        # Mapear direcciones
        direction_mirror = {
            'CALL': 'PUT',
            'PUT': 'CALL'
        }
        
        original_pattern = original['pattern']
        
        # Solo crear espejo para patrones verdes
        if original_pattern not in pattern_mirror:
            return None
        
        # Crear estrategia espejo con métricas similares pero ajustadas
        mirror = {
            'pair': original['pair'],
            'timeframe': original['timeframe'],
            'pattern': pattern_mirror[original_pattern],
            'direction': direction_mirror[original['direction']],
            'effectiveness': original['effectiveness'],  # Usar misma efectividad como baseline
            'occurrences': original['occurrences'],      # Mismas ocurrencias esperadas
            'wins': original['wins'],
            'losses': original['losses'],
            'avg_profit': original['avg_profit'],
            'score': original['score'] * 0.95,  # Score ligeramente menor por ser proyección
            'trigger_condition': f"prev_sequence == '{pattern_mirror[original_pattern]}'",
            'description': f"Después de secuencia {pattern_mirror[original_pattern]} → Vela R",
            'predicted_candle': 'R',
            'type': 'mirror_strategy',  # Marcar como estrategia espejo
            'analysis_date': datetime.now(timezone.utc).isoformat(),
            'original_strategy_id': original.get('id'),
            'is_projection': True  # Indicar que es proyección, no datos reales
        }
        
        return mirror
    
    def filter_strategies_for_mirroring(self, strategies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filtrar estrategias que necesitan espejos"""
        green_patterns = ['V', 'VV', 'VVV', 'VVVV']
        
        candidates = []
        for strategy in strategies:
            if (strategy['pattern'] in green_patterns and 
                strategy['direction'] == 'CALL' and
                strategy['effectiveness'] > 75.0):  # Solo espejar estrategias buenas
                candidates.append(strategy)
        
        logger.info(f"🔍 {len(candidates)} estrategias verdes candidatas para espejo")
        return candidates
    
    def check_mirror_exists(self, mirror: Dict[str, Any], existing: List[Dict[str, Any]]) -> bool:
        """Verificar si ya existe una estrategia espejo similar"""
        for strategy in existing:
            if (strategy['pair'] == mirror['pair'] and
                strategy['timeframe'] == mirror['timeframe'] and
                strategy['pattern'] == mirror['pattern']):
                return True
        return False
    
    def create_all_mirrors(self, dry_run: bool = True) -> Dict[str, Any]:
        """Crear todas las estrategias espejo"""
        try:
            logger.info("🔄 Iniciando creación de estrategias espejo")
            
            # Obtener estrategias existentes
            existing_strategies = self.get_existing_strategies()
            if not existing_strategies:
                logger.error("❌ No se pudieron obtener estrategias existentes")
                return {'error': 'No se pudieron obtener estrategias'}
            
            # Filtrar candidatas
            candidates = self.filter_strategies_for_mirroring(existing_strategies)
            
            created_mirrors = []
            skipped_mirrors = []
            
            for original in candidates:
                mirror = self.create_mirror_strategy(original)
                if mirror is None:
                    continue
                
                # Verificar si ya existe
                if self.check_mirror_exists(mirror, existing_strategies):
                    skipped_mirrors.append(f"{mirror['pair']} {mirror['pattern']}")
                    continue
                
                created_mirrors.append(mirror)
                
                # Mostrar preview
                logger.info(f"✨ Espejo creado: {original['pair']} {original['pattern']} → {mirror['pattern']}")
                logger.info(f"   Original: {original['direction']} {original['effectiveness']:.1f}%")
                logger.info(f"   Espejo:   {mirror['direction']} {mirror['effectiveness']:.1f}%")
            
            # Insertar en base de datos si no es dry run
            inserted_count = 0
            if not dry_run and created_mirrors:
                logger.info(f"💾 Insertando {len(created_mirrors)} estrategias espejo...")
                
                for mirror in created_mirrors:
                    if self.db_client.insert_strategy(mirror):
                        inserted_count += 1
                    else:
                        logger.error(f"❌ Error insertando {mirror['pair']} {mirror['pattern']}")
            
            # Resultados
            results = {
                'total_existing': len(existing_strategies),
                'candidates': len(candidates),
                'mirrors_created': len(created_mirrors),
                'mirrors_inserted': inserted_count,
                'skipped': len(skipped_mirrors),
                'skipped_list': skipped_mirrors,
                'dry_run': dry_run
            }
            
            # Resumen
            logger.info("📊 RESUMEN DE ESPEJOS:")
            logger.info(f"   Estrategias existentes: {results['total_existing']}")
            logger.info(f"   Candidatas para espejo: {results['candidates']}")
            logger.info(f"   Espejos creados: {results['mirrors_created']}")
            logger.info(f"   Espejos insertados: {results['mirrors_inserted']}")
            logger.info(f"   Saltados (ya existen): {results['skipped']}")
            
            if dry_run:
                logger.info("🧪 MODO DRY RUN - No se insertaron estrategias")
                logger.info("💡 Ejecuta con --execute para insertar realmente")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error creando espejos: {e}")
            return {'error': str(e)}
    
    def show_preview(self, limit: int = 5):
        """Mostrar preview de espejos que se crearían"""
        try:
            existing_strategies = self.get_existing_strategies()
            candidates = self.filter_strategies_for_mirroring(existing_strategies)
            
            print(f"\n🔍 PREVIEW DE ESTRATEGIAS ESPEJO (top {limit}):")
            print("=" * 80)
            
            for i, original in enumerate(candidates[:limit]):
                mirror = self.create_mirror_strategy(original)
                if mirror:
                    print(f"\n{i+1}. {original['pair']} {original['timeframe']}")
                    print(f"   Original: {original['pattern']} → {original['direction']} ({original['effectiveness']:.1f}%)")
                    print(f"   Espejo:   {mirror['pattern']} → {mirror['direction']} ({mirror['effectiveness']:.1f}%)")
            
            if len(candidates) > limit:
                print(f"\n... y {len(candidates) - limit} más")
                
        except Exception as e:
            logger.error(f"❌ Error en preview: {e}")

def main():
    """Función principal"""
    try:
        creator = MirrorStrategyCreator()
        
        # Verificar argumentos
        execute = '--execute' in sys.argv
        preview = '--preview' in sys.argv
        
        if preview:
            creator.show_preview(10)
            return
        
        if execute:
            print("⚠️  MODO EJECUCIÓN: Se insertarán estrategias espejo en la base de datos")
            confirm = input("¿Continuar? (y/N): ")
            if confirm.lower() != 'y':
                print("❌ Operación cancelada")
                return
            
            results = creator.create_all_mirrors(dry_run=False)
        else:
            print("🧪 MODO DRY RUN: Solo simulación, no se insertará nada")
            results = creator.create_all_mirrors(dry_run=True)
        
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
    print("🔄 CREADOR DE ESTRATEGIAS ESPEJO")
    print("=" * 40)
    print("Opciones:")
    print("  python create_mirror_strategies.py           # Dry run (simulación)")
    print("  python create_mirror_strategies.py --preview # Ver preview")
    print("  python create_mirror_strategies.py --execute # Ejecutar realmente")
    print()
    
    main()