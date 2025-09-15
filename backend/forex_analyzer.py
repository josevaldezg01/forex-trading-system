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
    print(f"📄 Cargando .env desde: {env_path}")
except ImportError:
    print("⚠️ python-dotenv no instalado, usando variables de sistema")

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
        self.pattern_detector = create_pattern_detector()
        self.db_client = create_supabase_client()
        self.alert_system = create_alert_system()
        self.force_all = os.getenv('FORCE_ALL_TIMEFRAMES', 'false').lower() == 'true'

        # Estadísticas de la sesión
        self.session_stats = {
            'start_time': datetime.now(timezone.utc),
            'pairs_processed': 0,
            'strategies_found': 0,
            'alerts_sent': 0,
            'errors': 0
        }

    def should_process_timeframe(self, timeframe: str) -> bool:
        """Determina si debe procesar un timeframe según la hora actual y modo de ejecución"""
        current_time = datetime.now(timezone.utc)
        current_hour = current_time.hour
        current_minute = current_time.minute
        weekday = current_time.weekday()  # 0=Monday, 6=Sunday

        # Modo forzado - siempre procesar
        if self.force_all:
            logger.info(f"🔧 Modo forzado: analizando {timeframe}")
            return True

        # Modo manual/desarrollo - analizar si hay datos recientes disponibles
        if not is_production():
            logger.info(f"🧪 Modo desarrollo: analizando {timeframe} con datos recientes")
            return True

        # Modo producción - solo en horarios programados
        logger.debug(f"⏰ Modo producción: verificando horario para {timeframe}")

        if timeframe == '1m':
            return True
        elif timeframe == '5m':
            return current_minute % 5 == 0
        elif timeframe == '15m':
            return current_minute % 15 == 0
        elif timeframe == '30m':
            return current_minute % 30 == 0
        elif timeframe == '1h':
            return current_minute == 0  # Solo en punto
        elif timeframe == '4h':
            return current_minute == 0 and current_hour % 4 == 0
        elif timeframe == '1d':
            return current_minute == 0 and current_hour == 0  # Medianoche UTC
        elif timeframe == '1w':
            return (current_minute == 0 and current_hour == 0 and
                    weekday == 0)  # Lunes medianoche
        elif timeframe == '1M':
            return (current_minute == 0 and current_hour == 0 and
                    current_time.day == 1)  # Primer día del mes

        return False

    def get_analysis_period_info(self, timeframe: str) -> Dict[str, Any]:
        """Obtiene información sobre el período de análisis"""
        current_time = datetime.now(timezone.utc)

        # Calcular últimos períodos completados
        if timeframe == '1h':
            # Última hora completa
            last_complete = current_time.replace(minute=0, second=0, microsecond=0)
            if current_time.minute == 0:
                last_complete = last_complete - timedelta(hours=1)
            periods_to_analyze = 1

        elif timeframe == '1d':
            # Último día completo
            last_complete = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            if current_time.hour == 0 and current_time.minute == 0:
                last_complete = last_complete - timedelta(days=1)
            periods_to_analyze = 1

        elif timeframe == '4h':
            # Último período de 4h completo
            hours_since_midnight = current_time.hour
            last_4h_start = (hours_since_midnight // 4) * 4
            last_complete = current_time.replace(hour=last_4h_start, minute=0, second=0, microsecond=0)
            if current_time.hour % 4 == 0 and current_time.minute == 0:
                last_complete = last_complete - timedelta(hours=4)
            periods_to_analyze = 1

        else:
            # Para otros timeframes
            last_complete = current_time
            periods_to_analyze = 1

        return {
            'timeframe': timeframe,
            'last_complete_period': last_complete,
            'periods_to_analyze': periods_to_analyze,
            'current_time': current_time,
            'is_production': is_production(),
            'analysis_type': 'scheduled' if is_production() else 'on_demand'
        }

    def analyze_recent_periods(self, df, pair: str, timeframe: str, period_info: Dict) -> Dict[str, Any]:
        """Analiza qué habría pasado en períodos recientes"""
        try:
            recent_analysis = {
                'pair': pair,
                'timeframe': timeframe,
                'recent_signals': [],
                'recent_performance': {},
                'last_signals': []
            }

            # Obtener secuencia de velas
            sequence = self.pattern_detector._get_candle_sequence(df)
            if not sequence or len(sequence) < 10:
                return recent_analysis

            # Analizar últimas señales (últimas 10 velas)
            recent_sequence = sequence[-20:]  # Últimas 20 velas para contexto

            # Buscar patrones en las últimas velas
            patterns_to_check = ['R', 'RR', 'RRR', 'V', 'VV', 'VVV']

            for i in range(len(recent_sequence) - 5, len(recent_sequence)):
                if i < 3:  # Necesitamos al menos contexto de 3 velas
                    continue

                for pattern in patterns_to_check:
                    pattern_len = len(pattern)
                    if i >= pattern_len:
                        # Verificar si hay patrón
                        check_sequence = ''.join(recent_sequence[i - pattern_len:i])
                        if check_sequence == pattern:
                            # Ver qué pasó después
                            if i < len(recent_sequence):
                                next_candle = recent_sequence[i]

                                signal = {
                                    'position_from_end': len(recent_sequence) - i,
                                    'pattern': pattern,
                                    'predicted': 'R' if 'R' in pattern else 'V',  # Simplificado
                                    'actual': next_candle,
                                    'success': (pattern[-1] == next_candle),
                                    'candle_index': i
                                }
                                recent_analysis['recent_signals'].append(signal)

            # Resumir rendimiento reciente
            if recent_analysis['recent_signals']:
                total_signals = len(recent_analysis['recent_signals'])
                successful_signals = sum(1 for s in recent_analysis['recent_signals'] if s['success'])

                recent_analysis['recent_performance'] = {
                    'total_signals': total_signals,
                    'successful': successful_signals,
                    'accuracy': (successful_signals / total_signals) * 100 if total_signals > 0 else 0,
                    'last_pattern': recent_analysis['recent_signals'][-1]['pattern'] if recent_analysis[
                        'recent_signals'] else None
                }

            return recent_analysis

        except Exception as e:
            logger.error(f"❌ Error analizando períodos recientes para {pair}: {e}")
            return {'error': str(e)}

    def analyze_timeframe_enhanced(self, timeframe: str) -> Dict[str, Any]:
        """Análisis mejorado que considera períodos recientes"""
        logger.info(f"🔍 Iniciando análisis mejorado para timeframe {timeframe}")

        # Obtener información del período
        period_info = self.get_analysis_period_info(timeframe)

        analysis_start = time.time()

        results = {
            'timeframe': timeframe,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'analysis_type': period_info['analysis_type'],
            'last_complete_period': period_info['last_complete_period'].isoformat(),
            'strategies': [],
            'total_strategies': 0,
            'avg_effectiveness': 0.0,
            'pairs_analyzed': [],
            'pairs_with_patterns': [],
            'historical_analysis': {},
            'errors': []
        }

        try:
            logger.info(f"📊 Tipo de análisis: {period_info['analysis_type']}")
            logger.info(f"📅 Último período completo: {period_info['last_complete_period']}")

            # Obtener más datos históricos para análisis bajo demanda
            data_limit = 1000 if period_info['analysis_type'] == 'on_demand' else 500

            logger.info(f"📊 Obteniendo {data_limit} registros para {len(CURRENCY_PAIRS)} pares...")

            all_strategies = []
            pairs_processed = 0

            for pair in CURRENCY_PAIRS:
                try:
                    logger.info(f"  📈 Procesando {pair}...")

                    # Obtener datos históricos
                    df = self.data_collector.get_forex_data(pair, timeframe, limit=data_limit)

                    if df is None or len(df) < 50:
                        logger.warning(f"  ⚠️ Datos insuficientes para {pair}")
                        results['errors'].append(f"Datos insuficientes para {pair}")
                        continue

                    results['pairs_analyzed'].append(pair)
                    pairs_processed += 1

                    # Análisis principal
                    patterns = self.pattern_detector.find_patterns(df, pair, timeframe)

                    if patterns:
                        all_strategies.extend(patterns)
                        results['pairs_with_patterns'].append(pair)
                        logger.info(f"  ✅ {pair}: {len(patterns)} patrones encontrados")

                        # Para análisis bajo demanda, agregar contexto histórico
                        if period_info['analysis_type'] == 'on_demand':
                            recent_analysis = self.analyze_recent_periods(df, pair, timeframe, period_info)
                            results['historical_analysis'][pair] = recent_analysis
                    else:
                        logger.info(f"  ℹ️ {pair}: Sin patrones válidos")

                    # Pausa entre requests
                    time.sleep(0.5)

                except Exception as e:
                    logger.error(f"  ❌ Error procesando {pair}: {e}")
                    results['errors'].append(f"Error en {pair}: {str(e)}")
                    self.session_stats['errors'] += 1
                    continue

            # Procesar resultados
            if all_strategies:
                all_strategies.sort(key=lambda x: x['score'], reverse=True)
                results['strategies'] = all_strategies
                results['total_strategies'] = len(all_strategies)
                results['avg_effectiveness'] = sum(s['effectiveness'] for s in all_strategies) / len(all_strategies)

                logger.info(f"📈 Resumen {timeframe} ({period_info['analysis_type']}):")
                logger.info(f"  📊 {results['total_strategies']} estrategias encontradas")
                logger.info(f"  🎯 Efectividad promedio: {results['avg_effectiveness']:.2f}%")
                logger.info(f"  💱 Pares con patrones: {len(results['pairs_with_patterns'])}/{pairs_processed}")

            # Actualizar estadísticas
            self.session_stats['pairs_processed'] += pairs_processed
            self.session_stats['strategies_found'] += len(all_strategies)

            # Calcular duración
            analysis_duration = time.time() - analysis_start
            results['analysis_duration'] = int(analysis_duration)

            logger.info(f"⏱️ Análisis de {timeframe} completado en {analysis_duration:.1f} segundos")
            return results

        except Exception as e:
            logger.error(f"❌ Error crítico analizando {timeframe}: {str(e)}")
            results['errors'].append(f"Error crítico: {str(e)}")
            self.session_stats['errors'] += 1
            return results

    def print_historical_analysis(self, results: Dict[str, Any]) -> None:
        """Muestra análisis histórico de manera legible"""
        if 'historical_analysis' not in results or not results['historical_analysis']:
            return

        print(f"\n📈 ANÁLISIS DE SEÑALES RECIENTES - {results['timeframe'].upper()}")
        print("=" * 60)

        for pair, analysis in results['historical_analysis'].items():
            if 'recent_performance' in analysis and analysis['recent_performance']:
                perf = analysis['recent_performance']
                print(f"\n💱 {pair}:")
                print(f"   Señales recientes: {perf['total_signals']}")
                print(f"   Precisión: {perf['accuracy']:.1f}%")
                print(f"   Último patrón: {perf.get('last_pattern', 'N/A')}")

                # Mostrar últimas señales
                if 'recent_signals' in analysis:
                    signals = analysis['recent_signals'][-3:]  # Últimas 3
                    if signals:
                        print("   Últimas señales:")
                        for signal in signals:
                            status = "✅" if signal['success'] else "❌"
                            print(f"     {status} {signal['pattern']} → {signal['actual']} "
                                  f"(hace {signal['position_from_end']} velas)")

    def save_results(self, timeframe: str, results: Dict[str, Any]) -> bool:
        """Guarda resultados en Supabase"""
        try:
            logger.info(f"💾 Guardando resultados de {timeframe}")

            saved_strategies = 0

            # Guardar estrategias individuales
            if results['strategies']:
                if len(results['strategies']) > 50:
                    # Usar inserción por lotes para muchas estrategias
                    saved_strategies = self.db_client.insert_strategies_batch(results['strategies'])
                else:
                    # Inserción individual para pocas estrategias
                    for strategy in results['strategies']:
                        if self.db_client.insert_strategy(strategy):
                            saved_strategies += 1

            # Guardar resumen de análisis
            summary = {
                'timeframe': timeframe,
                'timestamp': results['timestamp'],
                'total_strategies': results['total_strategies'],
                'avg_effectiveness': results['avg_effectiveness'],
                'analysis_duration': results.get('analysis_duration'),
                'pairs_analyzed': results['pairs_analyzed']
            }

            summary_saved = self.db_client.insert_analysis_summary(summary)

            if saved_strategies > 0 or summary_saved:
                logger.info(f"✅ Guardado: {saved_strategies} estrategias + resumen para {timeframe}")
                return True
            else:
                logger.warning(f"⚠️ No se pudo guardar información de {timeframe}")
                return False

        except Exception as e:
            logger.error(f"❌ Error guardando {timeframe}: {e}")
            self.session_stats['errors'] += 1
            return False

    def check_and_send_alerts(self, timeframe: str, results: Dict[str, Any]) -> None:
        """Verifica y envía alertas si es necesario"""
        try:
            strategies = results.get('strategies', [])

            if not strategies:
                return

            # Verificar estrategias con baja efectividad
            low_effectiveness_threshold = 75.0
            low_effectiveness_strategies = [
                s for s in strategies
                if s['effectiveness'] < low_effectiveness_threshold
            ]

            if low_effectiveness_strategies:
                alert_sent = self.alert_system.send_effectiveness_alert(
                    timeframe, low_effectiveness_strategies
                )
                if alert_sent:
                    self.session_stats['alerts_sent'] += 1

            # Verificar nuevas estrategias muy efectivas
            high_effectiveness_threshold = 95.0
            new_high_performers = [
                s for s in strategies
                if s['effectiveness'] > high_effectiveness_threshold and s['occurrences'] > 20
            ]

            if new_high_performers:
                alert_sent = self.alert_system.send_new_strategy_alert(
                    timeframe, new_high_performers
                )
                if alert_sent:
                    self.session_stats['alerts_sent'] += 1

            # Alerta si hay muchos errores
            if len(results.get('errors', [])) > 3:
                error_details = "\n".join(results['errors'][:5])  # Primeros 5 errores
                alert_sent = self.alert_system.send_system_status_alert(
                    'warning',
                    f"Múltiples errores en análisis de {timeframe}:\n{error_details}"
                )
                if alert_sent:
                    self.session_stats['alerts_sent'] += 1

        except Exception as e:
            logger.error(f"❌ Error verificando alertas para {timeframe}: {e}")
            self.session_stats['errors'] += 1

    def send_session_summary(self) -> None:
        """Envía resumen de la sesión"""
        try:
            duration = datetime.now(timezone.utc) - self.session_stats['start_time']
            duration_minutes = duration.total_seconds() / 60

            # Preparar datos del resumen
            summary_data = {
                'total_strategies': self.session_stats['strategies_found'],
                'pairs_analyzed': self.session_stats['pairs_processed'],
                'active_timeframes': get_active_timeframes(),
                'alerts_sent': self.session_stats['alerts_sent'],
                'errors': self.session_stats['errors'],
                'duration_minutes': round(duration_minutes, 1),
                'environment': 'production' if is_production() else 'development'
            }

            # Enviar resumen solo si es significativo
            if (self.session_stats['strategies_found'] > 0 or
                    self.session_stats['errors'] > 0 or
                    is_production()):
                self.alert_system.send_system_status_alert(
                    'info',
                    f"Análisis completado:\n"
                    f"• Estrategias encontradas: {summary_data['total_strategies']}\n"
                    f"• Pares procesados: {summary_data['pairs_analyzed']}\n"
                    f"• Timeframes: {', '.join(summary_data['active_timeframes'])}\n"
                    f"• Duración: {summary_data['duration_minutes']} min\n"
                    f"• Errores: {summary_data['errors']}"
                )

        except Exception as e:
            logger.error(f"❌ Error enviando resumen: {e}")

    def run_analysis(self) -> None:
        """Ejecuta el análisis completo"""
        logger.info("🚀 Iniciando análisis automático de Forex")
        logger.info(f"⏰ Hora UTC: {datetime.now(timezone.utc)}")
        logger.info(f"🌍 Entorno: {'Producción' if is_production() else 'Desarrollo'}")

        processed_timeframes = []
        results_by_timeframe = {}

        try:
            # Validar configuración
            validate_config()

            # Verificar conexión con base de datos
            if not self.db_client.test_connection():
                raise Exception("No se puede conectar con la base de datos")

            # Procesar cada timeframe configurado
            active_timeframes = get_active_timeframes()
            logger.info(f"📊 Timeframes activos: {active_timeframes}")

            for timeframe in active_timeframes:
                if self.should_process_timeframe(timeframe):
                    logger.info(f"✅ Procesando {timeframe}")

                    # Realizar análisis mejorado
                    results = self.analyze_timeframe_enhanced(timeframe)
                    results_by_timeframe[timeframe] = results

                    # Guardar resultados
                    if self.save_results(timeframe, results):
                        logger.info(f"💾 Resultados de {timeframe} guardados")

                    # Verificar y enviar alertas
                    self.check_and_send_alerts(timeframe, results)

                    processed_timeframes.append(timeframe)

                else:
                    logger.info(f"⏭️ Saltando {timeframe} (no es momento)")

            # Mostrar resumen final
            if processed_timeframes:
                logger.info(f"🎉 Análisis completado para: {', '.join(processed_timeframes)}")
                logger.info(f"📊 Estadísticas de sesión:")
                logger.info(f"  • Pares procesados: {self.session_stats['pairs_processed']}")
                logger.info(f"  • Estrategias encontradas: {self.session_stats['strategies_found']}")
                logger.info(f"  • Alertas enviadas: {self.session_stats['alerts_sent']}")
                logger.info(f"  • Errores: {self.session_stats['errors']}")

                # Mostrar análisis histórico solo en desarrollo
                if not is_production() and processed_timeframes:
                    for timeframe in processed_timeframes:
                        if timeframe in results_by_timeframe:
                            self.print_historical_analysis(results_by_timeframe[timeframe])
            else:
                logger.info("😴 No hay timeframes para procesar en este momento")

            # Enviar resumen si es apropiado
            if is_production() and processed_timeframes:
                self.send_session_summary()

            logger.info("✅ Proceso finalizado exitosamente")

        except Exception as e:
            logger.error(f"💥 Error crítico en análisis: {str(e)}")

            # Enviar alerta de error crítico
            try:
                self.alert_system.send_system_status_alert(
                    'error',
                    f"Error crítico en análisis automático: {str(e)}"
                )
            except:
                pass  # No fallar si las alertas tampoco funcionan

            # Terminar con código de error
            sys.exit(1)


def main():
    """Función principal"""
    try:
        # Mostrar información del entorno
        logger.info("=" * 50)
        logger.info("🤖 FOREX TRADING SYSTEM - ANÁLISIS AUTOMÁTICO")
        logger.info("=" * 50)

        # Crear y ejecutar analizador
        analyzer = ForexAnalyzer()
        analyzer.run_analysis()

        # Salir exitosamente
        sys.exit(0)

    except KeyboardInterrupt:
        logger.info("⚠️ Análisis interrumpido por usuario")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Error fatal: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()