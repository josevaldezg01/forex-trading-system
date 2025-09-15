# backend/supabase_client.py
import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import asyncio
from pathlib import Path

try:
    from dotenv import load_dotenv

    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass

try:
    from supabase import create_client, Client
except ImportError:
    print("❌ Error: Instala supabase con: pip install supabase")
    exit(1)

from config import SUPABASE_CONFIG, TIMEFRAMES_CONFIG

# Configurar logging
logger = logging.getLogger(__name__)


class SupabaseClient:
    """Cliente para interactuar con Supabase (PostgreSQL)"""

    def __init__(self):
        self.url = SUPABASE_CONFIG['url']
        self.key = SUPABASE_CONFIG['key']
        self.client: Optional[Client] = None
        self.max_retries = SUPABASE_CONFIG.get('max_retries', 3)
        self.retry_delay = SUPABASE_CONFIG.get('retry_delay', 1)

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL y SUPABASE_KEY son requeridos")

        self._connect()

    def _connect(self) -> None:
        """Establecer conexión con Supabase"""
        try:
            self.client = create_client(self.url, self.key)
            logger.info("✅ Conexión con Supabase establecida")
        except Exception as e:
            logger.error(f"❌ Error conectando con Supabase: {e}")
            raise

    def test_connection(self) -> bool:
        """Probar conexión con Supabase"""
        try:
            # Probar con una query simple
            result = self.client.table('forex_config').select('*').limit(1).execute()
            logger.info("✅ Test de conexión exitoso")
            return True
        except Exception as e:
            logger.error(f"❌ Test de conexión fallido: {e}")
            return False

    def insert_strategy(self, strategy: Dict[str, Any]) -> bool:
        """Insertar nueva estrategia en la base de datos"""
        try:
            # Validar datos requeridos
            required_fields = [
                'pair', 'timeframe', 'pattern', 'direction',
                'effectiveness', 'occurrences', 'wins', 'losses'
            ]

            for field in required_fields:
                if field not in strategy:
                    raise ValueError(f"Campo requerido faltante: {field}")

            # Preparar datos para inserción
            insert_data = {
                'pair': strategy['pair'],
                'timeframe': strategy['timeframe'],
                'pattern': strategy['pattern'],
                'direction': strategy['direction'],
                'effectiveness': float(strategy['effectiveness']),
                'occurrences': int(strategy['occurrences']),
                'wins': int(strategy['wins']),
                'losses': int(strategy['losses']),
                'avg_profit': float(strategy.get('avg_profit', 0.0)),
                'score': float(strategy.get('score', 0.0)),
                'trigger_condition': strategy.get('trigger_condition', ''),
                'analysis_date': datetime.now(timezone.utc).isoformat()
            }

            # Insertar en base de datos
            result = self.client.table('forex_strategies').insert(insert_data).execute()

            if result.data:
                logger.info(f"✅ Estrategia insertada: {strategy['pair']} {strategy['timeframe']} {strategy['pattern']}")
                return True
            else:
                logger.error(f"❌ Error insertando estrategia: Sin datos en respuesta")
                return False

        except Exception as e:
            logger.error(f"❌ Error insertando estrategia: {e}")
            return False

    def insert_strategies_batch(self, strategies: List[Dict[str, Any]]) -> int:
        """Insertar múltiples estrategias en lote"""
        successful_inserts = 0

        try:
            # Preparar datos en lotes de 100
            batch_size = 100

            for i in range(0, len(strategies), batch_size):
                batch = strategies[i:i + batch_size]
                insert_data = []

                for strategy in batch:
                    try:
                        data = {
                            'pair': strategy['pair'],
                            'timeframe': strategy['timeframe'],
                            'pattern': strategy['pattern'],
                            'direction': strategy['direction'],
                            'effectiveness': float(strategy['effectiveness']),
                            'occurrences': int(strategy['occurrences']),
                            'wins': int(strategy['wins']),
                            'losses': int(strategy['losses']),
                            'avg_profit': float(strategy.get('avg_profit', 0.0)),
                            'score': float(strategy.get('score', 0.0)),
                            'trigger_condition': strategy.get('trigger_condition', ''),
                            'analysis_date': datetime.now(timezone.utc).isoformat()
                        }
                        insert_data.append(data)
                    except Exception as e:
                        logger.warning(f"⚠️ Error preparando estrategia: {e}")
                        continue

                # Insertar lote
                if insert_data:
                    result = self.client.table('forex_strategies').insert(insert_data).execute()
                    if result.data:
                        successful_inserts += len(result.data)
                        logger.info(f"✅ Lote insertado: {len(result.data)} estrategias")

            logger.info(f"✅ Total insertado: {successful_inserts}/{len(strategies)} estrategias")
            return successful_inserts

        except Exception as e:
            logger.error(f"❌ Error en inserción por lotes: {e}")
            return successful_inserts

    def insert_analysis_summary(self, summary: Dict[str, Any]) -> bool:
        """Insertar resumen de análisis"""
        try:
            insert_data = {
                'timeframe': summary['timeframe'],
                'total_strategies': int(summary.get('total_strategies', 0)),
                'avg_effectiveness': float(summary.get('avg_effectiveness', 0.0)),
                'analysis_duration': summary.get('analysis_duration'),
                'pairs_analyzed': summary.get('pairs_analyzed', []),
                'timestamp': summary['timestamp'],
            }

            result = self.client.table('forex_analysis_summary').insert(insert_data).execute()

            if result.data:
                logger.info(f"✅ Resumen insertado: {summary['timeframe']}")
                return True
            else:
                logger.error("❌ Error insertando resumen: Sin datos en respuesta")
                return False

        except Exception as e:
            logger.error(f"❌ Error insertando resumen: {e}")
            return False

    def insert_alert(self, alert: Dict[str, Any]) -> bool:
        """Insertar alerta"""
        try:
            insert_data = {
                'alert_type': alert['alert_type'],
                'timeframe': alert.get('timeframe'),
                'strategy_id': alert.get('strategy_id'),
                'message': alert['message'],
                'details': alert.get('details', {}),
                'email_sent': alert.get('email_sent', False),
                'processed': alert.get('processed', False)
            }

            result = self.client.table('forex_alerts').insert(insert_data).execute()

            if result.data:
                logger.info(f"✅ Alerta insertada: {alert['alert_type']}")
                return True
            else:
                logger.error("❌ Error insertando alerta")
                return False

        except Exception as e:
            logger.error(f"❌ Error insertando alerta: {e}")
            return False

    def get_recent_strategies(self, timeframe: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Obtener estrategias recientes"""
        try:
            query = self.client.table('forex_strategies').select('*')

            if timeframe:
                query = query.eq('timeframe', timeframe)

            result = query.order('analysis_date', desc=True).limit(limit).execute()

            if result.data:
                logger.info(f"✅ Obtenidas {len(result.data)} estrategias recientes")
                return result.data
            else:
                logger.info("ℹ️ No se encontraron estrategias")
                return []

        except Exception as e:
            logger.error(f"❌ Error obteniendo estrategias: {e}")
            return []

    def get_best_strategies(self, timeframe: str = None, min_effectiveness: float = 80.0, limit: int = 50) -> List[
        Dict[str, Any]]:
        """Obtener mejores estrategias"""
        try:
            query = self.client.table('forex_strategies').select('*')

            if timeframe:
                query = query.eq('timeframe', timeframe)

            query = query.gte('effectiveness', min_effectiveness)
            result = query.order('score', desc=True).limit(limit).execute()

            if result.data:
                logger.info(f"✅ Obtenidas {len(result.data)} mejores estrategias")
                return result.data
            else:
                logger.info("ℹ️ No se encontraron estrategias con esa efectividad")
                return []

        except Exception as e:
            logger.error(f"❌ Error obteniendo mejores estrategias: {e}")
            return []

    def get_strategy_by_pattern(self, pair: str, timeframe: str, pattern: str) -> Optional[Dict[str, Any]]:
        """Buscar estrategia específica por patrón"""
        try:
            result = (self.client.table('forex_strategies')
                      .select('*')
                      .eq('pair', pair)
                      .eq('timeframe', timeframe)
                      .eq('pattern', pattern)
                      .order('analysis_date', desc=True)
                      .limit(1)
                      .execute())

            if result.data:
                return result.data[0]
            else:
                return None

        except Exception as e:
            logger.error(f"❌ Error buscando estrategia: {e}")
            return None

    def cleanup_old_strategies(self, days: int = 30) -> int:
        """Limpiar estrategias antiguas"""
        try:
            cutoff_date = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(days=days)

            result = (self.client.table('forex_strategies')
                      .delete()
                      .lt('analysis_date', cutoff_date.isoformat())
                      .execute())

            deleted_count = len(result.data) if result.data else 0
            logger.info(f"✅ Limpieza completada: {deleted_count} estrategias eliminadas")
            return deleted_count

        except Exception as e:
            logger.error(f"❌ Error en limpieza: {e}")
            return 0

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Obtener valor de configuración"""
        try:
            result = (self.client.table('forex_config')
                      .select('config_value')
                      .eq('config_key', key)
                      .execute())

            if result.data:
                return result.data[0]['config_value']
            else:
                return default

        except Exception as e:
            logger.error(f"❌ Error obteniendo configuración: {e}")
            return default

    def set_config_value(self, key: str, value: str, description: str = None) -> bool:
        """Establecer valor de configuración"""
        try:
            # Verificar si existe
            existing = (self.client.table('forex_config')
                        .select('id')
                        .eq('config_key', key)
                        .execute())

            if existing.data:
                # Actualizar
                result = (self.client.table('forex_config')
                          .update({'config_value': value, 'updated_at': datetime.now(timezone.utc).isoformat()})
                          .eq('config_key', key)
                          .execute())
            else:
                # Insertar
                result = (self.client.table('forex_config')
                          .insert({
                    'config_key': key,
                    'config_value': value,
                    'description': description or f'Configuración para {key}'
                })
                          .execute())

            if result.data:
                logger.info(f"✅ Configuración actualizada: {key} = {value}")
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"❌ Error estableciendo configuración: {e}")
            return False

    def get_database_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de la base de datos"""
        try:
            stats = {}

            # Total de estrategias
            result = self.client.table('forex_strategies').select('*', count='exact').execute()
            stats['total_strategies'] = result.count

            # Estrategias por timeframe
            timeframe_stats = {}
            for tf in TIMEFRAMES_CONFIG.keys():
                result = (self.client.table('forex_strategies')
                          .select('*', count='exact')
                          .eq('timeframe', tf)
                          .execute())
                timeframe_stats[tf] = result.count
            stats['by_timeframe'] = timeframe_stats

            # Última actualización
            result = (self.client.table('forex_strategies')
                      .select('analysis_date')
                      .order('analysis_date', desc=True)
                      .limit(1)
                      .execute())

            if result.data:
                stats['last_update'] = result.data[0]['analysis_date']

            logger.info("✅ Estadísticas obtenidas")
            return stats

        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {}


# Función de utilidad para crear cliente
def create_supabase_client() -> SupabaseClient:
    """Crear instancia del cliente Supabase"""
    return SupabaseClient()


# Test del cliente
if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)

    try:
        print("🔄 Probando cliente Supabase...")
        client = create_supabase_client()

        # Test de conexión
        if client.test_connection():
            print("✅ Conexión exitosa")

            # Obtener estadísticas
            stats = client.get_database_stats()
            print(f"📊 Estadísticas: {stats}")

            # Test de configuración
            test_value = client.get_config_value('min_effectiveness_threshold', '70.0')
            print(f"⚙️ Configuración de prueba: {test_value}")

        else:
            print("❌ Error de conexión")

    except Exception as e:
        print(f"❌ Error: {e}")