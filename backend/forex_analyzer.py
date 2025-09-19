# backend/forex_analyzer.py
import os
import sys
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from pathlib import Path

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    print(f"Cargando .env desde: {env_path}")
except ImportError:
    print("python-dotenv no instalado, usando variables de sistema")

# Imports locales
from config import TIMEFRAMES_CONFIG, CURRENCY_PAIRS, validate_config, get_active_timeframes, is_production
from data_collector import create_data_collector
from pattern_detector import create_pattern_detector
from supabase_client import create_supabase_client
from alert_system import create_alert_system

# Configurar logging
log_level = logging.DEBUG if not is_production() else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ForexAnalyzer:
    """Analizador principal del sistema Forex"""
    
    def __init__(self):
        self.data_collector = create_data_collector()
        self.db_client = create_supabase_client()
        self.pattern_detector = create_pattern_detector(self.db_client)
        self.alert_system = create_alert_system()
        self.force_all = os.getenv('FORCE_ALL_TIMEFRAMES', 'false').lower() == 'true'
        
        # Estadísticas de la sesión
        self.session_stats = {
            'start_time': datetime.now(timezone.utc),
            'pairs_processed': 0,
            'strategies_found': 0,
            'alerts_sent': 0,
            'errors': 0,
            'patterns_found': 0,
            'strategies_updated': 0
        }
    
    def should_process_timeframe(self, timeframe: str) -> bool:
        """Determina si debe procesar un timeframe según la hora actual y modo de ejecución"""
        current_time = datetime.now(timezone.utc)
        current_hour = current_time.hour
        current_minute = current_time.minute
        weekday = current_time.weekday()  # 0=Monday, 6=Sunday
        
        # Modo forzado - siempre procesar
        if self.force_all:
            logger.info(f"Modo forzado: analizando {timeframe}")
            return True
        
        # Verificar si es fin de semana (mercado cerrado)
        if weekday >= 5:  # Saturday=5, Sunday=6
            logger.info(f"Fin de semana: saltando {timeframe}")
            return False
        
        # Solo procesar 1h por ahora (datos confiables)
        if timeframe != '1h':
            logger.debug(f"Timeframe {timeframe} no activo actualmente")
            return False
        
        # Procesar cada hora en punto para 1h
        if timeframe == '1h' and current_minute < 5:
            logger.info(f"Hora en punto: procesando {timeframe}")
            return True
        
        return False
    
    def analyze_pair_with_accumulation(self, pair: str, timeframe: str) -> Dict[str, Any]:
        """Analiza un par y actualiza las estrategias con acumulación histórica"""
        
        analysis_result = {
            'pair': pair,
            'timeframe': timeframe,
            'patterns_found': 0,
            'patterns_updated': 0,
            'success': False,
            'error': None,
            'alerts_sent': 0
        }
        
        try:
            logger.info(f"Analizando {pair} {timeframe} con acumulación histórica...")
            
            # Obtener datos históricos
            historical_data = self.data_collector.get_forex_data(pair, timeframe)
            
            if historical_data is None or historical_data.empty:
                logger.warning(f"No se pudieron obtener datos para {pair} {timeframe}")
                analysis_result['error'] = 'No data available'
                return analysis_result
            
            logger.info(f"Datos obtenidos: {len(historical_data)} velas para {pair} {timeframe}")
            
            # Detectar patrones y actualizar base de datos
            patterns = self.pattern_detector.detect_and_update_patterns(pair, timeframe, historical_data)
            
            analysis_result['patterns_found'] = len(patterns)
            analysis_result['patterns_updated'] = len(patterns)
            analysis_result['success'] = True
            
            # Actualizar estadísticas de sesión
            self.session_stats['patterns_found'] += len(patterns)
            self.session_stats['strategies_updated'] += len(patterns)
            
            # Generar alertas si es necesario
            if patterns and self.alert_system:
                alerts_sent = self._generate_pattern_alerts(patterns)
                self.session_stats['alerts_sent'] += alerts_sent
                analysis_result['alerts_sent'] = alerts_sent
            
            logger.info(f"Completado {pair} {timeframe}: {len(patterns)} patrones actualizados")
            
        except Exception as e:
            logger.error(f"Error analizando {pair} {timeframe}: {e}")
            analysis_result['error'] = str(e)
            self.session_stats['errors'] += 1
        
        return analysis_result
    
    def analyze_pair(self, pair: str, timeframe: str) -> Dict[str, Any]:
        """Análisis básico de un par (compatibilidad con versión original)"""
        return self.analyze_pair_with_accumulation(pair, timeframe)
    
    def process_pair(self, pair: str, timeframe: str) -> bool:
        """Procesa un par específico"""
        try:
            result = self.analyze_pair_with_accumulation(pair, timeframe)
            if result['success']:
                self.session_stats['pairs_processed'] += 1
                return True
            else:
                self.session_stats['errors'] += 1
                return False
        except Exception as e:
            logger.error(f"Error procesando {pair} {timeframe}: {e}")
            self.session_stats['errors'] += 1
            return False
    
    def run_full_analysis_with_accumulation(self) -> Dict[str, Any]:
        """Ejecuta análisis completo de todos los pares con acumulación histórica"""
        
        logger.info("Iniciando análisis completo con acumulación histórica...")
        
        start_time = datetime.now(timezone.utc)
        results = {
            'start_time': start_time.isoformat(),
            'pairs_analyzed': 0,
            'total_patterns': 0,
            'strategies_updated': 0,
            'errors': 0,
            'pair_results': [],
            'master_summary': None,
            'alerts_sent': 0
        }
        
        # Obtener pares activos
        active_pairs = self._get_active_pairs()
        active_timeframes = get_active_timeframes()
        
        logger.info(f"Analizando {len(active_pairs)} pares en {len(active_timeframes)} timeframes")
        
        # Procesar cada par y timeframe
        for pair in active_pairs:
            for timeframe in active_timeframes:
                if self.should_process_timeframe(timeframe):
                    
                    pair_result = self.analyze_pair_with_accumulation(pair, timeframe)
                    results['pair_results'].append(pair_result)
                    
                    if pair_result['success']:
                        results['total_patterns'] += pair_result['patterns_found']
                        results['strategies_updated'] += pair_result['patterns_updated']
                        results['alerts_sent'] += pair_result.get('alerts_sent', 0)
                    else:
                        results['errors'] += 1
                    
                    results['pairs_analyzed'] += 1
                    self.session_stats['pairs_processed'] += 1
                    
                    # Pequeña pausa para no sobrecargar APIs
                    time.sleep(1)
        
        # Generar resumen de master
        results['master_summary'] = self._generate_master_summary()
        
        # Estadísticas finales
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        results.update({
            'end_time': end_time.isoformat(),
            'duration_seconds': duration,
            'session_stats': self.session_stats
        })
        
        logger.info(f"Análisis completo finalizado: {results['pairs_analyzed']} pares, {results['total_patterns']} patrones, {results['strategies_updated']} actualizaciones")
        
        return results
    
    def run_analysis(self) -> Dict[str, Any]:
        """Método principal de análisis (compatible con versión original)"""
        return self.run_full_analysis_with_accumulation()
    
    def run_continuous_analysis(self, interval_minutes: int = 60) -> None:
        """Ejecuta análisis continuo cada X minutos"""
        
        logger.info(f"Iniciando análisis continuo cada {interval_minutes} minutos...")
        
        while True:
            try:
                current_time = datetime.now(timezone.utc)
                logger.info(f"Ejecutando análisis continuo a las {current_time.strftime('%H:%M:%S UTC')}")
                
                # Ejecutar análisis completo
                results = self.run_full_analysis_with_accumulation()
                
                # Log de resultados
                logger.info(f"Análisis completado - Pares: {results['pairs_analyzed']}, Patrones: {results['total_patterns']}")
                
                # Esperar hasta el siguiente intervalo
                sleep_seconds = interval_minutes * 60
                logger.info(f"Esperando {interval_minutes} minutos hasta el próximo análisis...")
                time.sleep(sleep_seconds)
                
            except KeyboardInterrupt:
                logger.info("Análisis continuo interrumpido por usuario")
                break
            except Exception as e:
                logger.error(f"Error en análisis continuo: {e}")
                # Esperar menos tiempo en caso de error
                time.sleep(300)  # 5 minutos
    
    def get_market_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual del mercado"""
        current_time = datetime.now(timezone.utc)
        weekday = current_time.weekday()
        
        is_weekend = weekday >= 5
        is_market_hours = 0 <= current_time.hour <= 23
        
        # Horario de sesiones principales
        london_session = 8 <= current_time.hour <= 17
        new_york_session = 13 <= current_time.hour <= 22
        tokyo_session = 0 <= current_time.hour <= 9 or current_time.hour >= 23
        sydney_session = 22 <= current_time.hour <= 23 or 0 <= current_time.hour <= 7
        
        return {
            'current_time': current_time.isoformat(),
            'weekday': weekday,
            'is_weekend': is_weekend,
            'is_market_hours': is_market_hours,
            'can_trade': not is_weekend and is_market_hours,
            'sessions': {
                'london': london_session,
                'new_york': new_york_session,
                'tokyo': tokyo_session,
                'sydney': sydney_session
            },
            'active_sessions': sum([london_session, new_york_session, tokyo_session, sydney_session])
        }
    
    def _generate_master_summary(self) -> Dict[str, Any]:
        """Genera resumen del estado actual del master"""
        
        try:
            # Contar estrategias en master por tipo
            master_query = self.db_client.client.table('forex_strategies_master').select('strategy_type, is_active').execute()
            
            if not master_query.data:
                return {'error': 'No data in master'}
            
            summary = {
                'total_strategies': len(master_query.data),
                'by_type': {},
                'active_count': 0,
                'inactive_count': 0
            }
            
            for record in master_query.data:
                strategy_type = record['strategy_type']
                is_active = record['is_active']
                
                summary['by_type'][strategy_type] = summary['by_type'].get(strategy_type, 0) + 1
                
                if is_active:
                    summary['active_count'] += 1
                else:
                    summary['inactive_count'] += 1
            
            # Top estrategias por efectividad
            top_query = self.db_client.client.table('forex_strategies_master').select('pair, pattern, direction, effectiveness, occurrences').order('effectiveness', desc=True).limit(5).execute()
            
            if top_query.data:
                summary['top_strategies'] = top_query.data
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generando resumen master: {e}")
            return {'error': str(e)}
    
    def _get_active_pairs(self) -> List[str]:
        """Obtiene lista de pares activos"""
        return ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD']
    
    def _generate_pattern_alerts(self, patterns: List[Dict[str, Any]]) -> int:
        """Genera alertas para patrones de alta calidad"""
        
        alerts_sent = 0
        
        try:
            for pattern in patterns:
                # Solo alertar patrones de alta calidad
                if pattern['effectiveness'] >= 70 and pattern['occurrences'] >= 30:
                    
                    alert_data = {
                        'pair': pattern['pair'],
                        'timeframe': pattern['timeframe'],
                        'pattern': pattern['pattern'],
                        'direction': pattern['direction'],
                        'effectiveness': pattern['effectiveness'],
                        'occurrences': pattern['occurrences'],
                        'score': pattern.get('score', 0),
                        'message': f"Patrón de alta calidad: {pattern['pair']} {pattern['pattern']} → {pattern['direction']} ({pattern['effectiveness']:.1f}%)",
                        'priority': 'high' if pattern['effectiveness'] >= 80 else 'medium',
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    
                    if self.alert_system and self.alert_system.send_alert(alert_data):
                        alerts_sent += 1
                        logger.info(f"Alerta enviada: {pattern['pair']} {pattern['pattern']} ({pattern['effectiveness']:.1f}%)")
            
        except Exception as e:
            logger.error(f"Error generando alertas: {e}")
        
        return alerts_sent
    
    def cleanup_old_data(self, days_old: int = 30) -> Dict[str, int]:
        """Limpia datos antiguos del sistema"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
            
            # Solo limpiar forex_strategies (no master - mantiene historial)
            cleanup_result = self.db_client.client.table('forex_strategies').delete().lt('created_at', cutoff_date.isoformat()).execute()
            
            cleaned_count = len(cleanup_result.data) if cleanup_result.data else 0
            
            logger.info(f"Limpieza completada: {cleaned_count} registros antiguos eliminados de forex_strategies")
            
            return {
                'cleaned_strategies': cleaned_count,
                'cutoff_date': cutoff_date.isoformat(),
                'days_old': days_old
            }
            
        except Exception as e:
            logger.error(f"Error en limpieza: {e}")
            return {'error': str(e)}
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas generales del sistema"""
        try:
            # Contar estrategias activas
            active_query = self.db_client.client.table('forex_strategies').select('id').execute()
            active_count = len(active_query.data) if active_query.data else 0
            
            # Contar estrategias en master
            master_query = self.db_client.client.table('forex_strategies_master').select('id').execute()
            master_count = len(master_query.data) if master_query.data else 0
            
            # Obtener estadísticas de efectividad
            effectiveness_query = self.db_client.client.table('forex_strategies').select('effectiveness, score, occurrences').execute()
            
            stats = {
                'active_strategies': active_count,
                'master_strategies': master_count,
                'avg_effectiveness': 0,
                'max_effectiveness': 0,
                'avg_score': 0,
                'max_score': 0,
                'total_occurrences': 0
            }
            
            if effectiveness_query.data:
                effectiveness_values = [r['effectiveness'] for r in effectiveness_query.data]
                score_values = [r['score'] for r in effectiveness_query.data]
                occurrences_values = [r['occurrences'] for r in effectiveness_query.data]
                
                stats.update({
                    'avg_effectiveness': sum(effectiveness_values) / len(effectiveness_values),
                    'max_effectiveness': max(effectiveness_values),
                    'avg_score': sum(score_values) / len(score_values),
                    'max_score': max(score_values),
                    'total_occurrences': sum(occurrences_values)
                })
            
            # Agregar estadísticas de sesión y mercado
            stats.update({
                'session_stats': self.session_stats,
                'market_status': self.get_market_status()
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {'error': str(e)}
    
    def get_best_strategies(self, limit: int = 10, min_effectiveness: float = 60.0) -> List[Dict[str, Any]]:
        """Obtiene las mejores estrategias activas"""
        try:
            best_query = self.db_client.client.table('forex_strategies').select('*').gte('effectiveness', min_effectiveness).order('effectiveness', desc=True).limit(limit).execute()
            
            return best_query.data if best_query.data else []
            
        except Exception as e:
            logger.error(f"Error obteniendo mejores estrategias: {e}")
            return []
    
    def get_strategy_performance(self, pair: str, pattern: str, timeframe: str = None) -> Dict[str, Any]:
        """Obtiene el rendimiento de una estrategia específica"""
        try:
            query = self.db_client.client.table('forex_strategies_master').select('*').eq('pair', pair).eq('pattern', pattern)
            
            if timeframe:
                query = query.eq('timeframe', timeframe)
            
            response = query.execute()
            
            if response.data and len(response.data) > 0:
                strategy = response.data[0]
                
                # Calcular métricas adicionales
                win_rate = (strategy['wins'] / strategy['occurrences'] * 100) if strategy['occurrences'] > 0 else 0
                loss_rate = 100 - win_rate
                
                performance = {
                    'strategy': strategy,
                    'metrics': {
                        'win_rate': win_rate,
                        'loss_rate': loss_rate,
                        'total_trades': strategy['occurrences'],
                        'profit_factor': strategy['wins'] / max(strategy['losses'], 1),
                        'effectiveness': strategy['effectiveness']
                    }
                }
                
                return performance
            else:
                return {'error': 'Strategy not found'}
                
        except Exception as e:
            logger.error(f"Error obteniendo rendimiento de estrategia: {e}")
            return {'error': str(e)}
    
    def backup_strategies(self, backup_path: str = None) -> Dict[str, Any]:
        """Crea backup de las estrategias"""
        try:
            if backup_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"backup_strategies_{timestamp}.json"
            
            # Obtener todas las estrategias activas
            active_strategies = self.db_client.client.table('forex_strategies').select('*').execute()
            
            # Obtener todas las estrategias master
            master_strategies = self.db_client.client.table('forex_strategies_master').select('*').execute()
            
            backup_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'active_strategies': active_strategies.data if active_strategies.data else [],
                'master_strategies': master_strategies.data if master_strategies.data else []
            }
            
            import json
            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            return {
                'backup_file': backup_path,
                'active_count': len(backup_data['active_strategies']),
                'master_count': len(backup_data['master_strategies']),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error creando backup: {e}")
            return {'error': str(e), 'success': False}

def main():
    """Función principal del analizador"""
    
    print("Iniciando Forex Analyzer con acumulación histórica...")
    
    # Validar configuración
    if not validate_config():
        print("Error en configuración - abortando")
        sys.exit(1)
    
    # Crear analizador
    analyzer = ForexAnalyzer()
    
    try:
        # Mostrar estado del sistema
        print("\nObteniendo estado del sistema...")
        system_stats = analyzer.get_system_statistics()
        
        if 'error' not in system_stats:
            print(f"Estado del sistema:")
            print(f"  Estrategias activas: {system_stats.get('active_strategies', 0)}")
            print(f"  Estrategias master: {system_stats.get('master_strategies', 0)}")
            print(f"  Efectividad promedio: {system_stats.get('avg_effectiveness', 0):.1f}%")
            print(f"  Score promedio: {system_stats.get('avg_score', 0):.1f}")
            
            market_status = system_stats.get('market_status', {})
            if market_status:
                print(f"  Estado del mercado: {'ABIERTO' if market_status.get('can_trade') else 'CERRADO'}")
                print(f"  Sesiones activas: {market_status.get('active_sessions', 0)}")
        
        # Ejecutar análisis completo
        print("\nEjecutando análisis completo...")
        results = analyzer.run_full_analysis_with_accumulation()
        
        # Mostrar resultados
        print(f"\nRESULTADOS DEL ANÁLISIS:")
        print(f"Pares analizados: {results['pairs_analyzed']}")
        print(f"Patrones detectados: {results['total_patterns']}")
        print(f"Estrategias actualizadas: {results['strategies_updated']}")
        print(f"Alertas enviadas: {results['alerts_sent']}")
        print(f"Errores: {results['errors']}")
        print(f"Duración: {results['duration_seconds']:.1f} segundos")
        
        # Mostrar resumen del master
        if results['master_summary'] and 'error' not in results['master_summary']:
            master = results['master_summary']
            print(f"\nESTADO DEL MASTER:")
            print(f"Total estrategias: {master.get('total_strategies', 0)}")
            print(f"Activas: {master.get('active_count', 0)}")
            print(f"Inactivas: {master.get('inactive_count', 0)}")
            
            if 'by_type' in master:
                print("Distribución por tipo:")
                for strategy_type, count in master['by_type'].items():
                    print(f"  {strategy_type}: {count}")
            
            if 'top_strategies' in master:
                print("\nTop 5 estrategias por efectividad:")
                for i, strategy in enumerate(master['top_strategies'], 1):
                    print(f"  {i}. {strategy['pair']} {strategy['pattern']} → {strategy['direction']}: {strategy['effectiveness']:.1f}% ({strategy['occurrences']} occ)")
        
        # Mostrar mejores estrategias activas
        print("\nMejores estrategias activas:")
        best_strategies = analyzer.get_best_strategies(limit=5)
        
        if best_strategies:
            for i, strategy in enumerate(best_strategies, 1):
                print(f"  {i}. {strategy['pair']} {strategy['pattern']} → {strategy['direction']}: {strategy['effectiveness']:.1f}% (Score: {strategy['score']:.1f})")
        else:
            print("  No hay estrategias activas con alta efectividad")
        
    except Exception as e:
        print(f"Error en análisis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()