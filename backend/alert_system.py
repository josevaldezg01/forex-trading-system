# backend/alert_system.py
import os
import logging
import smtplib
import requests
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    from dotenv import load_dotenv

    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass

from config import ALERT_CONFIG

# Configurar logging
logger = logging.getLogger(__name__)


class AlertSystem:
    """Sistema de alertas y notificaciones"""

    def __init__(self):
        self.config = ALERT_CONFIG
        self.email_config = self.config.get('email', {})
        self.thresholds = self.config.get('thresholds', {})
        self.frequency_config = self.config.get('frequency', {})

        # Cache para evitar spam de alertas
        self.recent_alerts = {}

    def _should_send_alert(self, alert_type: str, content_hash: str) -> bool:
        """Verificar si debe enviar alerta (evitar spam)"""
        try:
            cooldown_minutes = self.frequency_config.get('cooldown_minutes', 30)
            max_alerts_per_hour = self.frequency_config.get('max_alerts_per_hour', 5)

            current_time = datetime.now(timezone.utc)

            # Verificar cooldown
            if content_hash in self.recent_alerts:
                last_sent = self.recent_alerts[content_hash]
                time_diff = (current_time - last_sent).total_seconds() / 60

                if time_diff < cooldown_minutes:
                    logger.debug(f"⏰ Alerta en cooldown: {alert_type}")
                    return False

            # Contar alertas en la última hora
            hour_ago = current_time.replace(minute=0, second=0, microsecond=0)
            recent_count = sum(
                1 for timestamp in self.recent_alerts.values()
                if timestamp >= hour_ago
            )

            if recent_count >= max_alerts_per_hour:
                logger.warning(f"📧 Límite de alertas por hora alcanzado: {recent_count}")
                return False

            return True

        except Exception as e:
            logger.error(f"❌ Error verificando alerta: {e}")
            return True  # En caso de error, permitir alerta

    def _record_alert_sent(self, content_hash: str) -> None:
        """Registrar que se envió una alerta"""
        self.recent_alerts[content_hash] = datetime.now(timezone.utc)

        # Limpiar alertas antiguas (más de 24 horas)
        day_ago = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        self.recent_alerts = {
            h: timestamp for h, timestamp in self.recent_alerts.items()
            if timestamp >= day_ago
        }

    def send_email_simple(self, subject: str, message: str, recipients: List[str] = None) -> bool:
        """Enviar email simple usando servicios gratuitos"""
        try:
            if not self.email_config.get('enabled', False):
                logger.info("📧 Emails deshabilitados en configuración")
                return False

            recipients = recipients or self.email_config.get('to_emails', [])
            if not recipients:
                logger.warning("⚠️ No hay destinatarios configurados")
                return False

            # Para desarrollo, solo loggear
            if os.getenv('GITHUB_ACTIONS') != 'true':
                logger.info(f"📧 EMAIL SIMULADO:")
                logger.info(f"   Para: {', '.join(recipients)}")
                logger.info(f"   Asunto: {subject}")
                logger.info(f"   Mensaje: {message[:100]}...")
                return True

            # En producción (GitHub Actions), enviar email real
            return self._send_email_production(subject, message, recipients)

        except Exception as e:
            logger.error(f"❌ Error enviando email: {e}")
            return False

    def _send_email_production(self, subject: str, message: str, recipients: List[str]) -> bool:
        """Enviar email real en producción"""
        try:
            # Configuración para Gmail SMTP (requiere App Password)
            smtp_server = "smtp.gmail.com"
            smtp_port = 587

            # Estas credenciales deberían estar en GitHub Secrets
            sender_email = os.getenv('GMAIL_USER')
            sender_password = os.getenv('GMAIL_APP_PASSWORD')

            if not sender_email or not sender_password:
                logger.warning("⚠️ Credenciales de email no configuradas")
                return False

            # Crear mensaje
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"{self.email_config.get('subject_prefix', '[FOREX]')} {subject}"

            # Agregar cuerpo del mensaje
            msg.attach(MIMEText(message, 'plain'))

            # Enviar email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)

            logger.info(f"✅ Email enviado a {len(recipients)} destinatarios")
            return True

        except Exception as e:
            logger.error(f"❌ Error enviando email en producción: {e}")
            return False

    def send_webhook_notification(self, message: str, webhook_url: str = None) -> bool:
        """Enviar notificación via webhook (Discord, Slack, etc.)"""
        try:
            webhook_url = webhook_url or os.getenv('WEBHOOK_URL')
            if not webhook_url:
                logger.debug("🔗 No hay webhook configurado")
                return False

            payload = {
                'content': f"🔔 **Forex Alert**\n{message}",
                'username': 'Forex Trading System'
            }

            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()

            logger.info("✅ Webhook enviado exitosamente")
            return True

        except Exception as e:
            logger.error(f"❌ Error enviando webhook: {e}")
            return False

    def send_effectiveness_alert(self, timeframe: str, strategies: List[Dict[str, Any]]) -> bool:
        """Enviar alerta por caída de efectividad"""
        try:
            if not strategies:
                return False

            threshold = self.thresholds.get('low_effectiveness', 75.0)

            # Crear hash para evitar spam
            content_hash = f"effectiveness_{timeframe}_{len(strategies)}"

            if not self._should_send_alert('effectiveness', content_hash):
                return False

            # Crear mensaje
            subject = f"Alerta: Caída de Efectividad en {timeframe.upper()}"

            message_lines = [
                f"⚠️ ALERTA DE EFECTIVIDAD - {timeframe.upper()}",
                f"Fecha: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                "",
                f"Se detectaron {len(strategies)} estrategias con efectividad por debajo de {threshold}%:",
                ""
            ]

            for i, strategy in enumerate(strategies[:5], 1):  # Mostrar máximo 5
                message_lines.append(
                    f"{i}. {strategy['pair']} {strategy['pattern']}: "
                    f"{strategy['effectiveness']:.1f}% (era {strategy.get('historical_effectiveness', 'N/A')}%)"
                )

            if len(strategies) > 5:
                message_lines.append(f"... y {len(strategies) - 5} más")

            message_lines.extend([
                "",
                "🔍 Recomendación: Revisar condiciones del mercado y ajustar estrategias",
                "",
                "Sistema: Forex Trading Bot"
            ])

            message = "\n".join(message_lines)

            # Enviar alertas
            email_sent = self.send_email_simple(subject, message)
            webhook_sent = self.send_webhook_notification(message)

            if email_sent or webhook_sent:
                self._record_alert_sent(content_hash)
                logger.info(f"✅ Alerta de efectividad enviada para {timeframe}")
                return True

            return False

        except Exception as e:
            logger.error(f"❌ Error enviando alerta de efectividad: {e}")
            return False

    def send_new_strategy_alert(self, timeframe: str, strategies: List[Dict[str, Any]]) -> bool:
        """Enviar alerta por nuevas estrategias muy efectivas"""
        try:
            if not strategies:
                return False

            threshold = self.thresholds.get('high_effectiveness', 95.0)

            # Crear hash para evitar spam
            strategy_signatures = [f"{s['pair']}_{s['pattern']}" for s in strategies]
            content_hash = f"new_strategy_{timeframe}_{'_'.join(strategy_signatures)}"

            if not self._should_send_alert('new_strategy', content_hash):
                return False

            # Crear mensaje
            subject = f"¡Nueva Estrategia Prometedora en {timeframe.upper()}!"

            message_lines = [
                f"🎯 NUEVA ESTRATEGIA DETECTADA - {timeframe.upper()}",
                f"Fecha: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                "",
                f"Se encontraron {len(strategies)} nuevas estrategias con efectividad superior a {threshold}%:",
                ""
            ]

            for i, strategy in enumerate(strategies, 1):
                message_lines.append(
                    f"{i}. {strategy['pair']} {strategy['pattern']} → {strategy['direction']}"
                )
                message_lines.append(
                    f"   Efectividad: {strategy['effectiveness']:.1f}% "
                    f"({strategy['occurrences']} ocurrencias, score: {strategy['score']:.1f})"
                )
                message_lines.append("")

            message_lines.extend([
                "💡 Considera incorporar estas estrategias en tu plan de trading",
                "",
                "Sistema: Forex Trading Bot"
            ])

            message = "\n".join(message_lines)

            # Enviar alertas
            email_sent = self.send_email_simple(subject, message)
            webhook_sent = self.send_webhook_notification(message)

            if email_sent or webhook_sent:
                self._record_alert_sent(content_hash)
                logger.info(f"✅ Alerta de nueva estrategia enviada para {timeframe}")
                return True

            return False

        except Exception as e:
            logger.error(f"❌ Error enviando alerta de nueva estrategia: {e}")
            return False

    def send_system_status_alert(self, status: str, details: str = "") -> bool:
        """Enviar alerta de estado del sistema"""
        try:
            content_hash = f"system_status_{status}_{hash(details) % 1000}"

            if not self._should_send_alert('system_status', content_hash):
                return False

            status_emoji = {
                'success': '✅',
                'warning': '⚠️',
                'error': '❌',
                'info': 'ℹ️'
            }.get(status.lower(), '📊')

            subject = f"Sistema Forex - {status.title()}"

            message_lines = [
                f"{status_emoji} ESTADO DEL SISTEMA",
                f"Fecha: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                f"Estado: {status.upper()}",
                ""
            ]

            if details:
                message_lines.extend([
                    "Detalles:",
                    details,
                    ""
                ])

            message_lines.append("Sistema: Forex Trading Bot")
            message = "\n".join(message_lines)

            # Enviar alertas
            email_sent = self.send_email_simple(subject, message)
            webhook_sent = self.send_webhook_notification(message)

            if email_sent or webhook_sent:
                self._record_alert_sent(content_hash)
                logger.info(f"✅ Alerta de sistema enviada: {status}")
                return True

            return False

        except Exception as e:
            logger.error(f"❌ Error enviando alerta de sistema: {e}")
            return False

    def send_daily_summary(self, summary_data: Dict[str, Any]) -> bool:
        """Enviar resumen diario"""
        try:
            content_hash = f"daily_summary_{datetime.now(timezone.utc).date()}"

            if not self._should_send_alert('daily_summary', content_hash):
                return False

            subject = f"Resumen Diario Forex - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"

            message_lines = [
                "📊 RESUMEN DIARIO DE TRADING",
                f"Fecha: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
                "",
                f"🎯 Estrategias activas: {summary_data.get('total_strategies', 0)}",
                f"📈 Efectividad promedio: {summary_data.get('avg_effectiveness', 0):.1f}%",
                f"🔍 Pares analizados: {summary_data.get('pairs_analyzed', 0)}",
                f"⚡ Timeframes activos: {', '.join(summary_data.get('active_timeframes', []))}",
                ""
            ]

            # Top estrategias
            top_strategies = summary_data.get('top_strategies', [])
            if top_strategies:
                message_lines.append("🏆 TOP ESTRATEGIAS:")
                for i, strategy in enumerate(top_strategies[:3], 1):
                    message_lines.append(
                        f"  {i}. {strategy['pair']} {strategy['pattern']}: "
                        f"{strategy['effectiveness']:.1f}%"
                    )
                message_lines.append("")

            # Alertas del día
            daily_alerts = summary_data.get('alerts_sent', 0)
            if daily_alerts > 0:
                message_lines.append(f"🔔 Alertas enviadas hoy: {daily_alerts}")
                message_lines.append("")

            message_lines.extend([
                "📱 Accede al dashboard para más detalles",
                "",
                "Sistema: Forex Trading Bot"
            ])

            message = "\n".join(message_lines)

            # Enviar resumen
            email_sent = self.send_email_simple(subject, message)
            webhook_sent = self.send_webhook_notification(message)

            if email_sent or webhook_sent:
                self._record_alert_sent(content_hash)
                logger.info("✅ Resumen diario enviado")
                return True

            return False

        except Exception as e:
            logger.error(f"❌ Error enviando resumen diario: {e}")
            return False

    def test_alerts(self) -> Dict[str, bool]:
        """Probar sistema de alertas"""
        try:
            logger.info("🧪 Probando sistema de alertas...")

            results = {}

            # Test email simple
            results['email'] = self.send_email_simple(
                "Test Alert System",
                "Este es un mensaje de prueba del sistema de alertas Forex.\n\nSi recibes esto, el sistema funciona correctamente!"
            )

            # Test webhook
            results['webhook'] = self.send_webhook_notification(
                "🧪 Test del sistema de alertas Forex - Todo funcionando correctamente!"
            )

            # Test alerta de sistema
            results['system_status'] = self.send_system_status_alert(
                'success',
                'Sistema de alertas probado exitosamente'
            )

            return results

        except Exception as e:
            logger.error(f"❌ Error probando alertas: {e}")
            return {'error': str(e)}


# Función de utilidad
def create_alert_system() -> AlertSystem:
    """Crear instancia del sistema de alertas"""
    return AlertSystem()


# Test del sistema de alertas
if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)

    try:
        print("🔔 Probando sistema de alertas...")

        alert_system = create_alert_system()

        # Ejecutar tests
        test_results = alert_system.test_alerts()

        print("\n📊 Resultados de pruebas:")
        for test_name, result in test_results.items():
            status = "✅" if result else "❌"
            print(f"   {status} {test_name.title()}: {'Exitoso' if result else 'Falló'}")

        # Ejemplo de alertas específicas
        print("\n🎯 Probando alertas específicas...")

        # Alerta de efectividad
        mock_strategies = [
            {
                'pair': 'EURUSD',
                'pattern': 'RR',
                'effectiveness': 65.0,
                'historical_effectiveness': 85.0
            }
        ]

        effectiveness_sent = alert_system.send_effectiveness_alert('1d', mock_strategies)
        print(
            f"   {'✅' if effectiveness_sent else '❌'} Alerta de efectividad: {'Enviada' if effectiveness_sent else 'No enviada'}")

        # Alerta de nueva estrategia
        new_strategies = [
            {
                'pair': 'GBPUSD',
                'pattern': 'VVV',
                'direction': 'CALL',
                'effectiveness': 96.5,
                'occurrences': 45,
                'score': 78.2
            }
        ]

        new_strategy_sent = alert_system.send_new_strategy_alert('1h', new_strategies)
        print(
            f"   {'✅' if new_strategy_sent else '❌'} Alerta nueva estrategia: {'Enviada' if new_strategy_sent else 'No enviada'}")

        print("\n✅ Pruebas de alertas completadas")

    except Exception as e:
        print(f"❌ Error: {e}")