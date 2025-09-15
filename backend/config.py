# backend/config.py
import os
from pathlib import Path
from typing import Dict, List, Any

try:
    from dotenv import load_dotenv
    # Buscar .env en la carpeta padre (raíz del proyecto)
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    print(f"📄 Cargando .env desde: {env_path}")
except ImportError:
    print("⚠️ python-dotenv no instalado, usando variables de sistema")

# Configuración de timeframes
TIMEFRAMES_CONFIG = {
    '1m': {
        'enabled': False,  # Muy intensivo, deshabilitado por defecto
        'frequency': 'every_minute',
        'min_occurrences': 50,
        'min_effectiveness': 80.0,
        'cron': '* * * * *'
    },
    '5m': {
        'enabled': False,
        'frequency': 'every_5_minutes',
        'min_occurrences': 30,
        'min_effectiveness': 75.0,
        'cron': '*/5 * * * *'
    },
    '15m': {
        'enabled': False,
        'frequency': 'every_15_minutes',
        'min_occurrences': 25,
        'min_effectiveness': 75.0,
        'cron': '*/15 * * * *'
    },
    '30m': {
        'enabled': False,
        'frequency': 'every_30_minutes',
        'min_occurrences': 20,
        'min_effectiveness': 75.0,
        'cron': '*/30 * * * *'
    },
    '1h': {
        'enabled': True,  # ✅ ACTIVO - Datos que tienes
        'frequency': 'hourly',
        'min_occurrences': 15,
        'min_effectiveness': 70.0,
        'cron': '0 * * * *'
    },
    '4h': {
        'enabled': False,  # Activar después si es necesario
        'frequency': 'every_4_hours',
        'min_occurrences': 10,
        'min_effectiveness': 70.0,
        'cron': '0 */4 * * *'
    },
    '1d': {
        'enabled': True,  # ✅ ACTIVO - Datos que tienes
        'frequency': 'daily',
        'min_occurrences': 5,
        'min_effectiveness': 70.0,
        'cron': '5 0 * * *'  # 00:05 UTC para evitar problemas de medianoche
    },
    '1w': {
        'enabled': False,
        'frequency': 'weekly',
        'min_occurrences': 3,
        'min_effectiveness': 70.0,
        'cron': '0 0 * * 1'  # Lunes medianoche
    },
    '1M': {
        'enabled': False,
        'frequency': 'monthly',
        'min_occurrences': 2,
        'min_effectiveness': 70.0,
        'cron': '0 0 1 * *'  # Primer día del mes
    }
}

# Pares de divisas principales para analizar
CURRENCY_PAIRS = [
    # Majors (más líquidos y confiables)
    'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',

    # Crosses (cruces principales)
    'EURGBP', 'EURJPY', 'GBPJPY', 'CHFJPY', 'EURCHF',

    # Commodity currencies
    'AUDJPY', 'CADJPY', 'NZDJPY',

    # Adicionales (pueden activarse después)
    # 'AUDCAD', 'AUDCHF', 'AUDNZD', 'CADCHF', 'EURAUD', 'EURCAD', 'EURNZD',
    # 'GBPAUD', 'GBPCAD', 'GBPCHF', 'GBPNZD', 'NZDCAD', 'NZDCHF'
]

# Configuración de APIs de datos
API_CONFIG = {
    'alpha_vantage': {
        'base_url': 'https://www.alphavantage.co/query',
        'key': os.getenv('ALPHA_VANTAGE_API_KEY'),
        'rate_limit': 5,  # calls per minute (free tier)
        'daily_limit': 500,  # calls per day (free tier)
        'timeout': 30,
        'retry_attempts': 3,
        'retry_delay': 2  # seconds between retries
    },
    'forex_api': {
        'base_url': 'https://api.fxapi.com/v1',
        'key': os.getenv('FOREX_API_KEY'),
        'rate_limit': 1000,  # calls per month (free tier)
        'timeout': 30,
        'retry_attempts': 3
    },
    'yahoo_finance': {
        'base_url': 'https://query1.finance.yahoo.com/v8/finance/chart',
        'rate_limit': None,  # No oficial limit but don't abuse
        'timeout': 30,
        'retry_attempts': 2,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
}

# Configuración de Supabase
SUPABASE_CONFIG = {
    'url': os.getenv('SUPABASE_URL'),
    'key': os.getenv('SUPABASE_KEY'),
    'timeout': 30,
    'max_retries': 3,
    'retry_delay': 1
}

# Configuración de alertas y notificaciones
ALERT_CONFIG = {
    'email': {
        'enabled': True,
        'provider': 'resend',  # o 'emailjs', 'sendgrid'
        'api_key': os.getenv('EMAIL_API_KEY'),
        'from_email': 'alerts@forex-system.com',
        'to_emails': ['josevaldezg@gmail.com'],  # Tu email
        'subject_prefix': '[FOREX ALERT]'
    },
    'thresholds': {
        'low_effectiveness': 75.0,  # Alerta si efectividad baja de 75%
        'high_effectiveness': 95.0,  # Alerta si nueva estrategia >95%
        'min_occurrences': 10,  # Mínimo para considerar válida
        'score_threshold': 75.0  # Score mínimo para alerta
    },
    'frequency': {
        'max_alerts_per_hour': 5,  # Evitar spam
        'cooldown_minutes': 30  # Espera entre alertas similares
    }
}

# Configuración de patrones a detectar
PATTERN_CONFIG = {
    'sequence_patterns': {
        'enabled': True,
        'max_length': 5,  # RRR, RRRR, RRRRR máximo
        'min_occurrences': 10,
        'patterns': ['R', 'RR', 'RRR', 'RRRR', 'V', 'VV', 'VVV']  # R=Red, V=Verde
    },
    'technical_indicators': {
        'enabled': False,  # Para futuro desarrollo
        'rsi_period': 14,
        'ma_periods': [20, 50, 200],
        'bollinger_period': 20
    },
    'price_action': {
        'enabled': False,  # Para futuro
        'min_body_size': 0.0001,  # Mínimo tamaño del cuerpo de vela
        'doji_threshold': 0.1  # % para considerar doji
    }
}

# Configuración de logging
LOGGING_CONFIG = {
    'level': 'INFO',  # DEBUG, INFO, WARNING, ERROR
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file_logging': False,  # Para desarrollo local
    'max_log_size': 10,  # MB
    'backup_count': 5
}

# Configuración de performance y límites
PERFORMANCE_CONFIG = {
    'max_concurrent_requests': 3,  # Requests simultáneos a APIs
    'request_delay': 1.0,  # Segundos entre requests
    'chunk_size': 100,  # Registros por lote en DB
    'memory_limit_mb': 500,  # Límite de memoria
    'execution_timeout': 900,  # 15 minutos máximo por análisis
    'cache_enabled': True,
    'cache_ttl': 3600  # 1 hora de cache
}

# Mapeo de símbolos para diferentes APIs
SYMBOL_MAPPING = {
    'alpha_vantage': {
        'EURUSD': 'EUR/USD',
        'GBPUSD': 'GBP/USD',
        'USDJPY': 'USD/JPY',
        'USDCHF': 'USD/CHF',
        'AUDUSD': 'AUD/USD',
        'USDCAD': 'USD/CAD',
        'NZDUSD': 'NZD/USD'
    },
    'yahoo_finance': {
        'EURUSD': 'EURUSD=X',
        'GBPUSD': 'GBPUSD=X',
        'USDJPY': 'USDJPY=X',
        'USDCHF': 'USDCHF=X',
        'AUDUSD': 'AUDUSD=X',
        'USDCAD': 'USDCAD=X',
        'NZDUSD': 'NZDUSD=X'
    }
}


# Funciones de utilidad para configuración
def validate_config() -> bool:
    """Valida que todas las variables de entorno estén configuradas"""
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_KEY'
    ]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        raise ValueError(f"Variables de entorno faltantes: {', '.join(missing_vars)}")

    # Validar formato de Supabase URL
    supabase_url = os.getenv('SUPABASE_URL', '')
    if not supabase_url.startswith('https://') or not '.supabase.co' in supabase_url:
        raise ValueError("SUPABASE_URL tiene formato incorrecto")

    return True


def get_active_timeframes() -> List[str]:
    """Retorna lista de timeframes activos"""
    return [tf for tf, config in TIMEFRAMES_CONFIG.items() if config['enabled']]


def get_timeframe_config(timeframe: str) -> Dict[str, Any]:
    """Retorna configuración específica de un timeframe"""
    return TIMEFRAMES_CONFIG.get(timeframe, {})


def get_api_symbol(pair: str, api_provider: str) -> str:
    """Convierte símbolo a formato específico de API"""
    mapping = SYMBOL_MAPPING.get(api_provider, {})
    return mapping.get(pair, pair)


def get_enabled_patterns() -> List[str]:
    """Retorna patrones habilitados para detección"""
    if PATTERN_CONFIG['sequence_patterns']['enabled']:
        return PATTERN_CONFIG['sequence_patterns']['patterns']
    return []


def is_production() -> bool:
    """Detecta si está ejecutándose en GitHub Actions (producción)"""
    return os.getenv('GITHUB_ACTIONS') == 'true'


def get_environment() -> str:
    """Retorna el entorno actual"""
    if is_production():
        return 'production'
    return 'development'


# Configuración específica por entorno
if is_production():
    # Configuración para GitHub Actions
    LOGGING_CONFIG['level'] = 'INFO'
    PERFORMANCE_CONFIG['request_delay'] = 2.0  # Más conservador
    ALERT_CONFIG['email']['enabled'] = True
else:
    # Configuración para desarrollo local
    LOGGING_CONFIG['level'] = 'DEBUG'
    PERFORMANCE_CONFIG['request_delay'] = 0.5
    ALERT_CONFIG['email']['enabled'] = False  # No enviar emails en desarrollo

# Validación al importar el módulo
if __name__ == "__main__":
    try:
        validate_config()
        print("✅ Configuración válida")
        print(f"🌍 Entorno: {get_environment()}")
        print(f"📊 Timeframes activos: {get_active_timeframes()}")
        print(f"💱 Pares configurados: {len(CURRENCY_PAIRS)}")
        print(f"🔍 Patrones habilitados: {get_enabled_patterns()}")
    except ValueError as e:
        print(f"❌ Error de configuración: {e}")
else:
    # Validación silenciosa al importar
    try:
        validate_config()
    except ValueError as e:
        print(f"⚠️ Advertencia de configuración: {e}")