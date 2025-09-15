# backend/fix_strategy_balance.py
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

class StrategyBalanceFixer:
    """Crear sistema completo y balanceado de estrategias"""
    
    def __init__(self):
        self.db_client = create_supabase_client()
        
        # Todos los pares que deberían tener estrategias
        self.ALL_PAIRS = ['EURUSD', 'USDJPY', 'USDCAD', 'USDCHF', 'AUDUSD', 'NZDUSD']
        
        # Patrones y sus direcciones esperadas
        self.PATTERN_CONFIG = {
            # Cada patrón debería tener AMBAS direcciones
            'V': {'primary': 'CALL', 'secondary': 'PUT'},
            'VV': {'primary': 'CALL', 'secondary': 'PUT'},
            'VVV': {'primary': 'CALL', 'secondary': 'PUT'},
            'VVVV': {'primary': 'CALL', 'secondary': 'PUT'},
            'R': {'primary': 'PUT', 'secondary': 'CALL'},
            'RR': {'primary': 'PUT', 'secondary': 'CALL'},
            'RRR': {'primary': 'PUT', 'secondary': 'CALL'},
            'RRRR': {'primary': 'PUT', 'secondary': 'CALL'}
        }
    
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
    
    def organize_existing_strategies(self, strategies: List[Dict[str, Any]]) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Organizar estrategias existentes por patrón, dirección y par"""
        organized = {}
        
        for strategy in strategies:
            pattern = strategy['pattern']
            direction = strategy['direction']
            pair = strategy['pair']
            
            if pattern not in organized:
                organized[pattern] = {}
            if direction not in organized[pattern]:
                organized[pattern][direction] = {}
            
            organized[pattern][direction][pair] = strategy
        
        return organized
    
    def create_missing_strategy(self, pattern: str, direction: str, pair: str, 
                              reference_strategy: Dict[str, Any] = None) -> Dict[str, Any]:
        """Crear una estrategia faltante"""
        
        # Si no hay referencia, usar valores base
        if reference_strategy is None:
            base_effectiveness = 75.0
            base_score = 60.0
            base_occurrences = 30
            base_wins = 23
            base_losses = 7
            base_avg_profit = 0.75
        else:
            # Usar referencia con pequeños ajustes
            base_effectiveness = reference_strategy['effectiveness']
            base_score = reference_strategy['score']
            base_occurrences = reference_strategy['occurrences']
            base_wins = reference_strategy['wins'] 
            base_losses = reference_strategy['losses']
            base_avg_profit = reference_strategy['avg_profit']
        
        # Determinar vela predicha
        predicted_candle = 'V' if direction == 'CALL' else 'R'
        
        # Crear estrategia
        strategy = {
            'pair': pair,
            'timeframe': '1d',
            'pattern': pattern,
            'direction': direction,
            'effectiveness': round(base_effectiveness, 1),
            'occurrences': base_occurrences,
            'wins': base_wins,
            'losses': base_losses,
            'avg_profit': base_avg_profit,
            'score': round(base_score, 1),
            'trigger_condition': f"prev_sequence == '{pattern}'",
            'description': f"Después de secuencia {pattern} → Vela {predicted_candle}",
            'predicted_candle': predicted_candle,
            'type': 'balance_strategy',
            'analysis_date': datetime.now(timezone.utc).isoformat(),
            'is_projection': True,
            'source': 'balance_fixer'
        }
        
        return strategy
    
    def find_best_reference(self, organized: Dict, pattern: str, direction: str) -> Dict[str, Any]:
        """Encontrar la mejor estrategia de referencia para crear una faltante"""
        
        # Primero intentar mismo patrón, misma dirección
        if pattern in organized and direction in organized[pattern]:
            strategies = list(organized[pattern][direction].values())
            if strategies:
                # Retornar la de mayor efectividad
                return max(strategies, key=lambda s: s['effectiveness'])
        
        # Si no, intentar mismo patrón, dirección opuesta
        opposite_direction = 'PUT' if direction == 'CALL' else 'CALL'
        if pattern in organized and opposite_direction in organized[pattern]:
            strategies = list(organized[pattern][opposite_direction].values())
            if strategies:
                return max(strategies, key=lambda s: s['effectiveness'])
        
        # Si no, intentar patrón similar (misma longitud)
        pattern_length = len(pattern)
        for other_pattern, pattern_data in organized.items():
            if len(other_pattern) == pattern_length and direction in pattern_data:
                strategies = list(pattern_data[direction].values())
                if strategies:
                    return max(strategies, key=lambda s: s['effectiveness'])
        
        # Si no hay nada, retornar None
        return None
    
    def fix_balance(self, dry_run: bool = True) -> Dict[str, Any]:
        """Corregir balance completo del sistema"""
        try:
            logger.info("🔧 Iniciando corrección de balance")
            
            # Obtener estrategias existentes
            existing_strategies = self.get_existing_strategies()
            organized = self.organize_existing_strategies(existing_strategies)
            
            missing_strategies = []
            
            # Para cada patrón
            for pattern, config in self.PATTERN_CONFIG.items():
                primary_direction = config['primary']
                secondary_direction = config['secondary']
                
                logger.info(f"🔍 Verificando patrón {pattern} ({primary_direction}/{secondary_direction})")
                
                # Verificar que existan estrategias para ambas direcciones en todos los pares
                for direction in [primary_direction, secondary_direction]:
                    for pair in self.ALL_PAIRS:
                        
                        # Verificar si existe
                        exists = (pattern in organized and 
                                direction in organized[pattern] and 
                                pair in organized[pattern][direction])
                        
                        if not exists:
                            # Encontrar referencia
                            reference = self.find_best_reference(organized, pattern, direction)
                            
                            # Crear estrategia faltante
                            missing_strategy = self.create_missing_strategy(
                                pattern, direction, pair, reference
                            )
                            
                            missing_strategies.append(missing_strategy)
                            
                            logger.info(f"  ➕ {pattern} {direction} {pair} (ref: {reference['pair'] if reference else 'base'})")
            
            # Mostrar resumen
            logger.info(f"\n📊 RESUMEN DE BALANCE:")
            logger.info(f"   Estrategias existentes: {len(existing_strategies)}")
            logger.info(f"   Estrategias faltantes: {len(missing_strategies)}")
            logger.info(f"   Total después de balance: {len(existing_strategies) + len(missing_strategies)}")
            
            # Verificar balance esperado
            expected_total = len(self.PATTERN_CONFIG) * 2 * len(self.ALL_PAIRS)  # 8 patrones × 2 direcciones × 6 pares
            logger.info(f"   Total esperado perfecto: {expected_total}")
            
            # Insertar estrategias faltantes
            inserted_count = 0
            if not dry_run and missing_strategies:
                logger.info(f"💾 Insertando {len(missing_strategies)} estrategias faltantes...")
                
                for strategy in missing_strategies:
                    if self.db_client.insert_strategy(strategy):
                        inserted_count += 1
                    else:
                        logger.error(f"❌ Error insertando {strategy['pattern']} {strategy['direction']} {strategy['pair']}")
            
            # Resultados
            results = {
                'existing_count': len(existing_strategies),
                'missing_count': len(missing_strategies),
                'inserted_count': inserted_count,
                'expected_total': expected_total,
                'dry_run': dry_run
            }
            
            if dry_run:
                logger.info("🧪 MODO DRY RUN - No se insertaron estrategias")
                logger.info("💡 Ejecuta con --execute para insertar realmente")
            else:
                final_total = len(existing_strategies) + inserted_count
                logger.info(f"✅ Balance completado: {final_total} estrategias totales")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error corrigiendo balance: {e}")
            return {'error': str(e)}
    
    def show_balance_preview(self):
        """Mostrar preview del balance a realizar"""
        try:
            existing_strategies = self.get_existing_strategies()
            organized = self.organize_existing_strategies(existing_strategies)
            
            print(f"\n🔍 PREVIEW DE BALANCE COMPLETO:")
            print("=" * 80)
            
            missing_count = 0
            
            for pattern, config in self.PATTERN_CONFIG.items():
                primary_direction = config['primary']
                secondary_direction = config['secondary']
                
                print(f"\n🔢 PATRÓN {pattern}:")
                
                for direction in [primary_direction, secondary_direction]:
                    existing_pairs = []
                    missing_pairs = []
                    
                    for pair in self.ALL_PAIRS:
                        exists = (pattern in organized and 
                                direction in organized[pattern] and 
                                pair in organized[pattern][direction])
                        
                        if exists:
                            existing_pairs.append(pair)
                        else:
                            missing_pairs.append(pair)
                            missing_count += 1
                    
                    status = "✅" if not missing_pairs else f"❌ Faltan {len(missing_pairs)}"
                    print(f"   {direction}: {len(existing_pairs)}/6 pares - {status}")
                    
                    if missing_pairs:
                        print(f"      Faltantes: {', '.join(missing_pairs)}")
            
            expected_total = len(self.PATTERN_CONFIG) * 2 * len(self.ALL_PAIRS)
            
            print(f"\n📊 RESUMEN:")
            print(f"   Estrategias actuales: {len(existing_strategies)}")
            print(f"   Estrategias faltantes: {missing_count}")
            print(f"   Total después de balance: {len(existing_strategies) + missing_count}")
            print(f"   Total esperado perfecto: {expected_total}")
            
        except Exception as e:
            logger.error(f"❌ Error en preview: {e}")

def main():
    """Función principal"""
    try:
        fixer = StrategyBalanceFixer()
        
        # Verificar argumentos
        execute = '--execute' in sys.argv
        preview = '--preview' in sys.argv
        
        if preview:
            fixer.show_balance_preview()
            return
        
        if execute:
            print("⚠️ MODO EJECUCIÓN: Se crearán estrategias para balance completo")
            confirm = input("¿Continuar? (y/N): ")
            if confirm.lower() != 'y':
                print("❌ Operación cancelada")
                return
            
            results = fixer.fix_balance(dry_run=False)
        else:
            print("🧪 MODO DRY RUN: Solo simulación, no se insertará nada")
            results = fixer.fix_balance(dry_run=True)
        
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
    print("🔧 CORRECTOR DE BALANCE DE ESTRATEGIAS")
    print("=" * 40)
    print("Crea sistema completo: 8 patrones × 2 direcciones × 6 pares = 96 estrategias")
    print()
    print("Opciones:")
    print("  python fix_strategy_balance.py           # Dry run (simulación)")
    print("  python fix_strategy_balance.py --preview # Ver preview")
    print("  python fix_strategy_balance.py --execute # Ejecutar realmente")
    print()
    
    main()