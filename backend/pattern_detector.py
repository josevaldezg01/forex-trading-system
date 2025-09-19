# backend/pattern_detector.py - Versión actualizada con lógica master
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass

from config import PATTERN_CONFIG, TIMEFRAMES_CONFIG

# Configurar logging
logger = logging.getLogger(__name__)

class PatternDetector:
    """Detector de patrones con lógica de acumulación histórica"""
    
    def __init__(self, supabase_client=None):
        self.config = PATTERN_CONFIG
        self.sequence_config = self.config.get('sequence_patterns', {})
        self.min_occurrences = self.sequence_config.get('min_occurrences', 10)
        self.max_pattern_length = self.sequence_config.get('max_length', 5)
        self.db_client = supabase_client
        
    def _classify_candle(self, open_price: float, close_price: float) -> str:
        """Clasificar vela como Roja (R) o Verde (V)"""
        if close_price >= open_price:
            return 'V'  # Verde (alcista)
        else:
            return 'R'  # Roja (bajista)
    
    def _get_candle_sequence(self, df: pd.DataFrame) -> List[str]:
        """Convertir DataFrame OHLC a secuencia de velas R/V"""
        try:
            if df.empty or len(df) == 0:
                return []
            
            sequence = []
            for _, row in df.iterrows():
                candle_type = self._classify_candle(row['open'], row['close'])
                sequence.append(candle_type)
            
            logger.debug(f"Secuencia generada: {len(sequence)} velas")
            return sequence
            
        except Exception as e:
            logger.error(f"Error generando secuencia: {e}")
            return []
    
    def detect_and_update_patterns(self, pair: str, timeframe: str, historical_data: pd.DataFrame = None) -> List[Dict[str, Any]]:
        """Detecta patrones y actualiza tanto forex_strategies como forex_strategies_master"""
        try:
            logger.info(f"Analizando patrones: {pair} {timeframe}")
            
            if historical_data is None or historical_data.empty:
                logger.warning(f"No hay datos históricos para {pair} {timeframe}")
                return []
            
            # Convertir a secuencia de velas
            sequence = self._get_candle_sequence(historical_data)
            
            if len(sequence) < self.min_occurrences + 5:
                logger.warning(f"Datos insuficientes: {len(sequence)} velas para {pair} {timeframe}")
                return []
            
            # Detectar patrones en los datos actuales
            current_patterns = self._find_sequence_patterns(sequence, pair, timeframe)
            
            # Actualizar base de datos con lógica de acumulación
            if self.db_client and current_patterns:
                self._update_strategies_with_accumulation(current_patterns)
            
            logger.info(f"Encontrados {len(current_patterns)} patrones para {pair} {timeframe}")
            return current_patterns
            
        except Exception as e:
            logger.error(f"Error detectando patrones: {e}")
            return []
    
    def _update_strategies_with_accumulation(self, current_patterns: List[Dict[str, Any]]):
        """Actualiza forex_strategies (actual) y acumula en forex_strategies_master (histórico)"""
        
        for pattern in current_patterns:
            try:
                # 1. Obtener datos históricos de master
                master_query = self.db_client.client.table('forex_strategies_master').select('*').eq('pair', pattern['pair']).eq('timeframe', pattern['timeframe']).eq('pattern', pattern['pattern']).eq('direction', pattern['direction']).execute()
                
                # 2. Calcular datos acumulados
                if master_query.data and len(master_query.data) > 0:
                    # Estrategia existe en master - acumular
                    master_record = master_query.data[0]
                    
                    new_total_occurrences = master_record['occurrences'] + pattern['occurrences']
                    new_total_wins = master_record['wins'] + pattern.get('wins', 0)
                    new_total_losses = master_record['losses'] + pattern.get('losses', 0)
                    new_effectiveness = (new_total_wins / new_total_occurrences * 100) if new_total_occurrences > 0 else 0
                    
                    # Actualizar master con datos acumulados
                    master_update = {
                        'occurrences': new_total_occurrences,
                        'wins': new_total_wins,
                        'losses': new_total_losses,
                        'effectiveness': new_effectiveness,
                        'score': self._calculate_strategy_score_improved(new_effectiveness, new_total_occurrences, pattern.get('avg_profit', 65), pattern['pair'], pattern['timeframe']),
                        'added_to_master': datetime.now(timezone.utc).isoformat()
                    }
                    
                    self.db_client.client.table('forex_strategies_master').update(master_update).eq('id', master_record['id']).execute()
                    logger.info(f"Actualizado master: {pattern['pair']} {pattern['pattern']} - Total ocurrencias: {new_total_occurrences}")
                    
                else:
                    # Nueva estrategia - insertar en master
                    master_record = {
                        'pair': pattern['pair'],
                        'timeframe': pattern['timeframe'],
                        'pattern': pattern['pattern'],
                        'direction': pattern['direction'],
                        'effectiveness': pattern['effectiveness'],
                        'occurrences': pattern['occurrences'],
                        'wins': pattern.get('wins', 0),
                        'losses': pattern.get('losses', 0),
                        'avg_profit': pattern.get('avg_profit', 65),
                        'score': pattern['score'],
                        'trigger_condition': f"After {len(pattern['pattern'])} consecutive {pattern['pattern']} candles",
                        'analysis_date': datetime.now(timezone.utc).date().isoformat(),
                        'created_at': datetime.now(timezone.utc).isoformat(),
                        'strategy_type': 'detected_real',
                        'source': 'live_pattern_detection',
                        'validation_method': 'historical_analysis',
                        'data_quality': 'high',
                        'is_active': True,
                        'added_to_master': datetime.now(timezone.utc).isoformat()
                    }
                    
                    self.db_client.client.table('forex_strategies_master').insert(master_record).execute()
                    logger.info(f"Nueva estrategia en master: {pattern['pair']} {pattern['pattern']}")
                
                # 3. Actualizar forex_strategies (datos actuales)
                current_query = self.db_client.client.table('forex_strategies').select('*').eq('pair', pattern['pair']).eq('timeframe', pattern['timeframe']).eq('pattern', pattern['pattern']).eq('direction', pattern['direction']).execute()
                
                strategy_data = {
                    'pair': pattern['pair'],
                    'timeframe': pattern['timeframe'],
                    'pattern': pattern['pattern'],
                    'direction': pattern['direction'],
                    'effectiveness': pattern['effectiveness'],
                    'occurrences': pattern['occurrences'],
                    'wins': pattern.get('wins', 0),
                    'losses': pattern.get('losses', 0),
                    'avg_profit': pattern.get('avg_profit', 65),
                    'score': pattern['score'],
                    'trigger_condition': f"After {len(pattern['pattern'])} consecutive {pattern['pattern']} candles",
                    'analysis_date': datetime.now(timezone.utc).date().isoformat(),
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                if current_query.data and len(current_query.data) > 0:
                    # Actualizar estrategia existente en forex_strategies
                    self.db_client.client.table('forex_strategies').update(strategy_data).eq('id', current_query.data[0]['id']).execute()
                    logger.info(f"Actualizada estrategia activa: {pattern['pair']} {pattern['pattern']}")
                else:
                    # Insertar nueva estrategia en forex_strategies
                    self.db_client.client.table('forex_strategies').insert(strategy_data).execute()
                    logger.info(f"Nueva estrategia activa: {pattern['pair']} {pattern['pattern']}")
                    
            except Exception as e:
                logger.error(f"Error actualizando estrategia {pattern.get('pair', '')} {pattern.get('pattern', '')}: {e}")
                continue
    
    def _find_sequence_patterns(self, sequence: List[str], pair: str, timeframe: str) -> List[Dict[str, Any]]:
        """Encontrar patrones de secuencia en los datos"""
        if len(sequence) < self.min_occurrences + 2:
            logger.warning(f"Secuencia muy corta para {pair} {timeframe}: {len(sequence)} velas")
            return []
        
        patterns = []
        
        # Patrones a buscar: R, RR, RRR, V, VV, VVV, etc.
        for length in range(1, min(self.max_pattern_length + 1, 6)):
            for candle_type in ['R', 'V']:
                pattern = candle_type * length
                result = self._analyze_pattern(sequence, pattern, pair, timeframe)
                if result:
                    patterns.append(result)
        
        # Patrones mixtos: RV, VR, RVR, VRV, etc.
        mixed_patterns = ['RV', 'VR', 'RVR', 'VRV', 'RVRV', 'VRVR']
        for pattern in mixed_patterns:
            if len(pattern) <= self.max_pattern_length:
                result = self._analyze_pattern(sequence, pattern, pair, timeframe)
                if result:
                    patterns.append(result)
        
        # Ordenar por score descendente
        patterns.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return patterns
    
    def _analyze_pattern(self, sequence: List[str], pattern: str, pair: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """Analiza un patrón específico en la secuencia"""
        if len(sequence) < len(pattern) + 1:
            return None
        
        pattern_len = len(pattern)
        
        # Encontrar todas las ocurrencias del patrón
        matches_r = {'count': 0, 'correct': 0}  # Predicción siguiente = R
        matches_v = {'count': 0, 'correct': 0}  # Predicción siguiente = V
        
        for i in range(len(sequence) - pattern_len):
            current_pattern = ''.join(sequence[i:i + pattern_len])
            
            if current_pattern == pattern and i + pattern_len < len(sequence):
                next_candle = sequence[i + pattern_len]
                
                # Contabilizar ambas direcciones
                matches_r['count'] += 1
                matches_v['count'] += 1
                
                if next_candle == 'R':
                    matches_r['correct'] += 1
                elif next_candle == 'V':
                    matches_v['correct'] += 1
        
        # Analizar ambas direcciones y seleccionar la mejor
        best_direction = None
        best_effectiveness = 0
        best_occurrences = 0
        
        for direction, data in [('R', matches_r), ('V', matches_v)]:
            if data['count'] >= self.min_occurrences:
                effectiveness = (data['correct'] / data['count']) * 100
                
                # Solo considerar si efectividad > 50%
                if effectiveness > 50 and effectiveness > best_effectiveness:
                    best_direction = direction
                    best_effectiveness = effectiveness
                    best_occurrences = data['count']
        
        if not best_direction or best_effectiveness <= 50:
            return None
        
        # Calcular datos para la estrategia
        wins = int(best_occurrences * best_effectiveness / 100)
        losses = best_occurrences - wins
        
        # Calcular ganancia basada en efectividad
        if best_effectiveness >= 80:
            avg_profit = 85.0
        elif best_effectiveness >= 70:
            avg_profit = 75.0
        elif best_effectiveness >= 60:
            avg_profit = 65.0
        else:
            avg_profit = 55.0
        
        # Calcular score usando método mejorado
        score = self._calculate_strategy_score_improved(
            best_effectiveness, best_occurrences, avg_profit, pair, timeframe
        )
        
        strategy = {
            'pair': pair,
            'timeframe': timeframe,
            'pattern': pattern,
            'predicted_candle': best_direction,  # R o V
            'direction': 'CALL' if best_direction == 'V' else 'PUT',
            'effectiveness': best_effectiveness,
            'occurrences': best_occurrences,
            'wins': wins,
            'losses': losses,
            'avg_profit': avg_profit,
            'score': score,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        logger.debug(f"Patrón encontrado: {pattern} → {best_direction}: {best_effectiveness:.1f}% ({best_occurrences} ocurrencias, score: {score:.1f})")
        
        return strategy
    
    def _calculate_strategy_score_improved(self, effectiveness: float, occurrences: int, avg_profit: float, pair: str, timeframe: str) -> float:
        """Calcula score más realista entre 40-85"""
        # Score base entre 40-85 (rango más realista)
        base_score = 40 + (effectiveness - 50) * 0.9  # 50% = score 40, 100% = score 85
        
        # Penalizar efectividades sospechosamente altas (overfitting)
        if effectiveness > 95:
            base_score *= 0.8  # Penalizar 20%
            logger.warning(f"Efectividad muy alta sospechosa: {effectiveness:.1f}% - aplicando penalización")
        
        # Bonus por número de ocurrencias (confiabilidad)
        if occurrences >= 100:
            base_score *= 1.1   # +10%
        elif occurrences >= 50:
            base_score *= 1.05  # +5%
        elif occurrences < 20:
            base_score *= 0.9   # -10%
        
        # Bonus por pares principales (más líquidos y confiables)
        major_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD']
        if pair in major_pairs:
            base_score *= 1.03  # +3%
        
        # Bonus por timeframes más confiables
        if timeframe == '1h':
            base_score *= 1.02  # +2%
        elif timeframe in ['4h', '1d']:
            base_score *= 1.05  # +5%
        
        # Asegurar que esté en el rango válido
        final_score = max(40, min(85, base_score))
        
        return round(final_score, 2)
    
    def get_master_strategy_history(self, pair: str, pattern: str, timeframe: str = None) -> Dict[str, Any]:
        """Obtiene el historial completo de una estrategia del master"""
        try:
            query = self.db_client.client.table('forex_strategies_master').select('*').eq('pair', pair).eq('pattern', pattern)
            
            if timeframe:
                query = query.eq('timeframe', timeframe)
                
            response = query.execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error obteniendo historial master: {e}")
            return {}

# Función de utilidad para crear instancia
def create_pattern_detector(supabase_client=None):
    """Crea una instancia del detector de patrones"""
    return PatternDetector(supabase_client)