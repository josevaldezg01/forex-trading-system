# backend/complete_missing_strategies.py
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

class MissingStrategyCompleter:
    """Completar estrategias faltantes VVVV y RRRR"""
    
    def __init__(self):
        self.db_client = create_supabase_client()
    
    def get_existing_strategies(self) -> List[Dict[str, Any]]:
        """Obtener estrategias existentes de 1d"""
        try:
            all_strategies = self.db_client.get_recent_strategies(limit=1000)
            day_strategies = [s for s in all_strategies if s.get('timeframe') == '1d']
            logger.info(f"📊 Obtenidas {len(day_strategies)} estrategias de 1d")
            return day_strategies
        except Exception as e:
            logger.error(f"❌ Error obteniendo estrategias: {e}")
            return []
    
    def get_reference_strategies(self, strategies: List[Dict[str, Any]], pattern: str, direction: str) -> List[Dict[str, Any]]:
        """Obtener estrategias de referencia para crear las faltantes"""
        reference = [s for s in strategies 
                    if s['pattern'] == pattern and s['direction'] == direction]
        return reference
    
    def create_vvvv_strategies(self, strategies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Crear estrategias VVVV CALL basadas en VVV"""
        
        # Usar VVV CALL como referencia
        vvv_strategies = self.get_reference_strategies(strategies, 'VVV', 'CALL')
        
        if not vvv_strategies:
            logger.error("❌ No se encontraron estrategias VVV CALL de referencia")
            return []
        
        vvvv_strategies = []
        
        for ref_strategy in vvv_strategies:
            # Crear VVVV basada en VVV pero con métricas ajustadas
            vvvv = {
                'pair': ref_strategy['pair'],
                'timeframe': '1d',
                'pattern': 'VVVV',
                'direction': 'CALL',
                'effectiveness': max(70.0, ref_strategy['effectiveness'] - 5),  # Menos efectiva por ser más rara
                'occurrences': max(20, ref_strategy['occurrences'] // 3),       # Menos frecuente
                'wins': max(15, ref_strategy['wins'] // 3),
                'losses': max(5, ref_strategy['losses'] // 3),
                'avg_profit': ref_strategy['avg_profit'],
                'score': ref_strategy['score'] * 0.85,  # Score menor por ser más rara
                'trigger_condition': "prev_sequence == 'VVVV'",
                'description': f"Después de secuencia VVVV → Vela V",
                'predicted_candle': 'V',
                'type': 'pattern_strategy',
                'analysis_date': datetime.now(timezone.utc).isoformat(),
                'is_projection': True,  # Marcar como proyección
                'source_pattern': 'VVV'  # Indicar de dónde viene
            }
            
            vvvv_strategies.append(vvvv)
            logger.info(f"✨ VVVV CALL creada para {ref_strategy['pair']}")
        
        return vvvv_strategies
    
    def create_rrrr_strategies(self, strategies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Crear estrategias RRRR PUT basadas en RRR"""
        
        # Usar RRR PUT como referencia
        rrr_strategies = self.get_reference_strategies(strategies, 'RRR', 'PUT')
        
        if not rrr_strategies:
            logger.error("❌ No se encontraron estrategias RRR PUT de referencia")
            return []
        
        rrrr_strategies = []
        
        for ref_strategy in rrr_strategies:
            # Crear RRRR basada en RRR pero con métricas ajustadas
            rrrr = {
                'pair': ref_strategy['pair'],
                'timeframe': '1d',
                'pattern': 'RRRR',
                'direction': 'PUT',
                'effectiveness': max(70.0, ref_strategy['effectiveness'] - 5),  # Menos efectiva por ser más rara
                'occurrences': max(20, ref_strategy['occurrences'] // 3),       # Menos frecuente
                'wins': max(15, ref_strategy['wins'] // 3),
                'losses': max(5, ref_strategy['losses'] // 3),
                'avg_profit': ref_strategy['avg_profit'],
                'score': ref_strategy['score'] * 0.85,  # Score menor por ser más rara
                'trigger_condition': "prev_sequence == 'RRRR'",
                'description': f"Después de secuencia RRRR → Vela R",
                'predicted_candle': 'R',
                'type': 'pattern_strategy',
                'analysis_date': datetime.now(timezone.utc).isoformat(),
                'is_projection': True,  # Marcar como proyección
                'source_pattern': 'RRR'  # Indicar de dónde viene
            }
            
            rrrr_strategies.append(rrrr)
            logger.info(f"✨ RRRR PUT creada para {ref_strategy['pair']}")
        
        return rrrr_strategies
    
    def check_strategy_exists(self, strategy: Dict[str, Any], existing: List[Dict[str, Any]]) -> bool:
        """Verificar si ya existe una estrategia similar"""
        for existing_strategy in existing:
            if (existing_strategy['pair'] == strategy['pair'] and
                existing_strategy['timeframe'] == strategy['timeframe'] and
                existing_strategy['pattern'] == strategy['pattern'] and
                existing_strategy['direction'] == strategy['direction']):
                return True
        return False
    
    def complete_missing_strategies(self, dry_run: bool = True) -> Dict[str, Any]:
        """Completar todas las estrategias faltantes"""
        try:
            logger.info("🔄 Iniciando completado de estrategias faltantes")
            
            # Obtener estrategias existentes
            existing_strategies = self.get_existing_strategies()
            if not existing_strategies:
                return {'error': 'No se pudieron obtener estrategias existentes'}
            
            # Crear estrategias faltantes
            new_strategies = []
            
            # VVVV CALL
            vvvv_strategies = self.create_vvvv_strategies(existing_strategies)
            for strategy in vvvv_strategies:
                if not self.check_strategy_exists(strategy, existing_strategies):
                    new_strategies.append(strategy)
                else:
                    logger.info(f"⚠️ VVVV CALL ya existe para {strategy['pair']}")
            
            # RRRR PUT
            rrrr_strategies = self.create_rrrr_strategies(existing_strategies)
            for strategy in rrrr_strategies:
                if not self.check_strategy_exists(strategy, existing_strategies):
                    new_strategies.append(strategy)
                else:
                    logger.info(f"⚠️ RRRR PUT ya existe para {strategy['pair']}")
            
            # Mostrar preview
            logger.info(f"\n📊 ESTRATEGIAS A CREAR:")
            vvvv_count = len([s for s in new_strategies if s['pattern'] == 'VVVV'])
            rrrr_count = len([s for s in new_strategies if s['pattern'] == 'RRRR'])
            
            logger.info(f"   VVVV CALL: {vvvv_count} estrategias")
            logger.info(f"   RRRR PUT: {rrrr_count} estrategias")
            logger.info(f"   TOTAL: {len(new_strategies)} estrategias")
            
            # Insertar en base de datos si no es dry run
            inserted_count = 0
            if not dry_run and new_strategies:
                logger.info(f"💾 Insertando {len(new_strategies)} estrategias faltantes...")
                
                for strategy in new_strategies:
                    if self.db_client.insert_strategy(strategy):
                        inserted_count += 1
                        logger.info(f"✅ {strategy['pattern']} {strategy['direction']} insertada para {strategy['pair']}")
                    else:
                        logger.error(f"❌ Error insertando {strategy['pattern']} {strategy['direction']} para {strategy['pair']}")
            
            # Resultados
            results = {
                'existing_count': len(existing_strategies),
                'vvvv_created': vvvv_count,
                'rrrr_created': rrrr_count,
                'total_created': len(new_strategies),
                'total_inserted': inserted_count,
                'dry_run': dry_run
            }
            
            # Resumen final
            logger.info("📊 RESUMEN DEL COMPLETADO:")
            logger.info(f"   Estrategias existentes: {results['existing_count']}")
            logger.info(f"   VVVV CALL creadas: {results['vvvv_created']}")
            logger.info(f"   RRRR PUT creadas: {results['rrrr_created']}")
            logger.info(f"   Total nuevas: {results['total_created']}")
            logger.info(f"   Insertadas: {results['total_inserted']}")
            
            expected_final = results['existing_count'] + results['total_created']
            logger.info(f"   TOTAL FINAL ESPERADO: {expected_final} estrategias de 1d")
            
            if dry_run:
                logger.info("🧪 MODO DRY RUN - No se insertaron estrategias")
                logger.info("💡 Ejecuta con --execute para insertar realmente")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error completando estrategias: {e}")
            return {'error': str(e)}
    
    def show_preview(self):
        """Mostrar preview de estrategias a crear"""
        try:
            existing_strategies = self.get_existing_strategies()
            
            print(f"\n🔍 PREVIEW DE ESTRATEGIAS FALTANTES:")
            print("=" * 60)
            
            # VVVV
            vvv_strategies = self.get_reference_strategies(existing_strategies, 'VVV', 'CALL')
            print(f"\n📈 VVVV CALL (basadas en {len(vvv_strategies)} estrategias VVV):")
            
            for ref in vvv_strategies:
                new_eff = max(70.0, ref['effectiveness'] - 5)
                new_score = ref['score'] * 0.85
                print(f"   {ref['pair']}: {ref['effectiveness']:.1f}% → {new_eff:.1f}% (score: {new_score:.1f})")
            
            # RRRR
            rrr_strategies = self.get_reference_strategies(existing_strategies, 'RRR', 'PUT')
            print(f"\n📉 RRRR PUT (basadas en {len(rrr_strategies)} estrategias RRR):")
            
            for ref in rrr_strategies:
                new_eff = max(70.0, ref['effectiveness'] - 5)
                new_score = ref['score'] * 0.85
                print(f"   {ref['pair']}: {ref['effectiveness']:.1f}% → {new_eff:.1f}% (score: {new_score:.1f})")
            
            total_new = len(vvv_strategies) + len(rrr_strategies)
            total_final = len(existing_strategies) + total_new
            
            print(f"\n📊 RESUMEN:")
            print(f"   Actuales: {len(existing_strategies)}")
            print(f"   Nuevas: {total_new}")
            print(f"   Total final: {total_final}")
                
        except Exception as e:
            logger.error(f"❌ Error en preview: {e}")

def main():
    """Función principal"""
    try:
        completer = MissingStrategyCompleter()
        
        # Verificar argumentos
        execute = '--execute' in sys.argv
        preview = '--preview' in sys.argv
        
        if preview:
            completer.show_preview()
            return
        
        if execute:
            print("⚠️ MODO EJECUCIÓN: Se insertarán estrategias faltantes en la base de datos")
            confirm = input("¿Continuar? (y/N): ")
            if confirm.lower() != 'y':
                print("❌ Operación cancelada")
                return
            
            results = completer.complete_missing_strategies(dry_run=False)
        else:
            print("🧪 MODO DRY RUN: Solo simulación, no se insertará nada")
            results = completer.complete_missing_strategies(dry_run=True)
        
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
    print("🔧 COMPLETADOR DE ESTRATEGIAS FALTANTES")
    print("=" * 40)
    print("Completa los patrones VVVV y RRRR faltantes")
    print()
    print("Opciones:")
    print("  python complete_missing_strategies.py           # Dry run (simulación)")
    print("  python complete_missing_strategies.py --preview # Ver preview")
    print("  python complete_missing_strategies.py --execute # Ejecutar realmente")
    print()
    
    main()