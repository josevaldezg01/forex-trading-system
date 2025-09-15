# backend/strategy_balance_audit.py
import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict

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

class StrategyBalanceAuditor:
    """Auditor específico para balance entre estrategias alcistas y bajistas"""
    
    def __init__(self):
        self.db_client = create_supabase_client()
    
    def get_strategies_1d(self) -> List[Dict[str, Any]]:
        """Obtener solo estrategias de 1d"""
        try:
            all_strategies = self.db_client.get_recent_strategies(limit=1000)
            day_strategies = [s for s in all_strategies if s.get('timeframe') == '1d']
            logger.info(f"📊 Obtenidas {len(day_strategies)} estrategias de 1d")
            return day_strategies
        except Exception as e:
            logger.error(f"❌ Error obteniendo estrategias: {e}")
            return []
    
    def analyze_call_put_balance(self, strategies: List[Dict[str, Any]]):
        """Analizar balance entre CALL y PUT por patrón y par"""
        
        print("\n⚖️ ANÁLISIS DE BALANCE CALL vs PUT")
        print("=" * 60)
        
        # Agrupar por patrón y dirección
        pattern_direction = defaultdict(lambda: defaultdict(list))
        
        for strategy in strategies:
            pattern = strategy['pattern']
            direction = strategy['direction']
            pattern_direction[pattern][direction].append(strategy)
        
        # Mostrar balance por patrón
        print(f"\n📊 BALANCE POR PATRÓN:")
        print(f"{'Patrón':<8} {'CALL':<6} {'PUT':<6} {'Balance':<10} {'Estado'}")
        print("-" * 50)
        
        total_call = 0
        total_put = 0
        imbalanced_patterns = []
        
        for pattern in sorted(pattern_direction.keys()):
            call_count = len(pattern_direction[pattern]['CALL'])
            put_count = len(pattern_direction[pattern]['PUT'])
            
            total_call += call_count
            total_put += put_count
            
            if call_count == put_count:
                balance = "✓ Igual"
                status = "OK"
            elif call_count > put_count:
                balance = f"+{call_count - put_count} CALL"
                status = "⚠️ DESBALANCE"
                imbalanced_patterns.append((pattern, 'CALL', call_count - put_count))
            else:
                balance = f"+{put_count - call_count} PUT"
                status = "⚠️ DESBALANCE"
                imbalanced_patterns.append((pattern, 'PUT', put_count - call_count))
            
            print(f"{pattern:<8} {call_count:<6} {put_count:<6} {balance:<10} {status}")
        
        print(f"\n📊 TOTALES:")
        print(f"   CALL: {total_call}")
        print(f"   PUT: {total_put}")
        print(f"   DIFERENCIA: {abs(total_call - total_put)}")
        
        if total_call == total_put:
            print("   ✅ SISTEMA BALANCEADO")
        else:
            print("   ⚠️ SISTEMA DESBALANCEADO")
        
        return {
            'total_call': total_call,
            'total_put': total_put,
            'imbalanced_patterns': imbalanced_patterns,
            'pattern_breakdown': dict(pattern_direction)
        }
    
    def analyze_pair_distribution(self, strategies: List[Dict[str, Any]]):
        """Analizar distribución por par de divisas"""
        
        print(f"\n💱 DISTRIBUCIÓN POR PAR DE DIVISAS:")
        print("-" * 50)
        
        pair_direction = defaultdict(lambda: defaultdict(int))
        
        for strategy in strategies:
            pair = strategy['pair']
            direction = strategy['direction']
            pair_direction[pair][direction] += 1
        
        print(f"{'Par':<8} {'CALL':<6} {'PUT':<6} {'Total':<6} {'Balance'}")
        print("-" * 40)
        
        for pair in sorted(pair_direction.keys()):
            call_count = pair_direction[pair]['CALL']
            put_count = pair_direction[pair]['PUT']
            total = call_count + put_count
            
            if call_count == put_count:
                balance = "✓"
            elif call_count > put_count:
                balance = f"+{call_count - put_count}C"
            else:
                balance = f"+{put_count - call_count}P"
            
            print(f"{pair:<8} {call_count:<6} {put_count:<6} {total:<6} {balance}")
    
    def show_strategy_details(self, strategies: List[Dict[str, Any]]):
        """Mostrar detalles de todas las estrategias"""
        
        print(f"\n📝 DETALLES COMPLETOS DE ESTRATEGIAS:")
        print("-" * 80)
        
        # Agrupar por patrón para mejor visualización
        by_pattern = defaultdict(list)
        for strategy in strategies:
            by_pattern[strategy['pattern']].append(strategy)
        
        for pattern in sorted(by_pattern.keys()):
            print(f"\n🔢 PATRÓN {pattern}:")
            
            # Separar por dirección
            call_strategies = [s for s in by_pattern[pattern] if s['direction'] == 'CALL']
            put_strategies = [s for s in by_pattern[pattern] if s['direction'] == 'PUT']
            
            if call_strategies:
                print(f"   📈 CALL ({len(call_strategies)}):")
                for strategy in call_strategies:
                    type_info = f" [{strategy.get('type', 'unknown')}]" if strategy.get('type') else ""
                    print(f"      {strategy['pair']}: {strategy['effectiveness']:.1f}%{type_info}")
            
            if put_strategies:
                print(f"   📉 PUT ({len(put_strategies)}):")
                for strategy in put_strategies:
                    type_info = f" [{strategy.get('type', 'unknown')}]" if strategy.get('type') else ""
                    print(f"      {strategy['pair']}: {strategy['effectiveness']:.1f}%{type_info}")
            
            if not call_strategies:
                print(f"   📈 CALL: ❌ NINGUNA")
            if not put_strategies:
                print(f"   📉 PUT: ❌ NINGUNA")
    
    def identify_missing_strategies(self, strategies: List[Dict[str, Any]]):
        """Identificar exactamente qué estrategias faltan para balance perfecto"""
        
        print(f"\n🔍 ESTRATEGIAS FALTANTES PARA BALANCE PERFECTO:")
        print("-" * 60)
        
        # Agrupar por patrón y dirección
        pattern_pairs = defaultdict(lambda: defaultdict(set))
        
        for strategy in strategies:
            pattern = strategy['pattern']
            direction = strategy['direction']
            pair = strategy['pair']
            pattern_pairs[pattern][direction].add(pair)
        
        missing_strategies = []
        
        # Verificar cada patrón
        for pattern in ['V', 'VV', 'VVV', 'VVVV', 'R', 'RR', 'RRR', 'RRRR']:
            call_pairs = pattern_pairs[pattern]['CALL']
            put_pairs = pattern_pairs[pattern]['PUT']
            
            print(f"\n🔢 PATRÓN {pattern}:")
            print(f"   CALL: {sorted(call_pairs)} ({len(call_pairs)})")
            print(f"   PUT:  {sorted(put_pairs)} ({len(put_pairs)})")
            
            # Para patrones verdes, debería haber CALL
            if pattern.startswith('V'):
                expected_direction = 'CALL'
                existing_pairs = call_pairs
                
                # Si hay PUT para patrón verde, algo está mal
                if put_pairs:
                    print(f"   ⚠️ WARNING: Patrón verde {pattern} tiene PUT (no debería)")
            
            # Para patrones rojos, debería haber PUT
            else:  # pattern.startswith('R')
                expected_direction = 'PUT'
                existing_pairs = put_pairs
                
                # Si hay CALL para patrón rojo, algo está mal
                if call_pairs:
                    print(f"   ⚠️ WARNING: Patrón rojo {pattern} tiene CALL (no debería)")
            
            # Verificar si faltan pares
            all_pairs = {'EURUSD', 'USDJPY', 'USDCAD', 'USDCHF', 'AUDUSD', 'NZDUSD'}
            missing_pairs = all_pairs - existing_pairs
            
            if missing_pairs:
                print(f"   ❌ FALTAN {expected_direction}: {sorted(missing_pairs)}")
                for pair in missing_pairs:
                    missing_strategies.append((pattern, expected_direction, pair))
            else:
                print(f"   ✅ COMPLETO")
        
        if missing_strategies:
            print(f"\n📋 RESUMEN DE ESTRATEGIAS FALTANTES:")
            for pattern, direction, pair in missing_strategies:
                print(f"   {pattern} {direction} {pair}")
            print(f"\n   TOTAL FALTANTES: {len(missing_strategies)}")
        else:
            print(f"\n✅ NO FALTAN ESTRATEGIAS")
        
        return missing_strategies
    
    def run_balance_audit(self):
        """Ejecutar auditoría completa de balance"""
        try:
            print("⚖️ AUDITORÍA DE BALANCE CALL/PUT")
            print("=" * 40)
            
            strategies = self.get_strategies_1d()
            if not strategies:
                print("❌ No se pudieron obtener estrategias")
                return
            
            # Análisis de balance
            balance_analysis = self.analyze_call_put_balance(strategies)
            
            # Distribución por par
            self.analyze_pair_distribution(strategies)
            
            # Detalles completos
            self.show_strategy_details(strategies)
            
            # Identificar faltantes
            missing = self.identify_missing_strategies(strategies)
            
            return {
                'balance_analysis': balance_analysis,
                'missing_strategies': missing
            }
            
        except Exception as e:
            logger.error(f"❌ Error en auditoría de balance: {e}")
            return None

def main():
    """Función principal"""
    try:
        auditor = StrategyBalanceAuditor()
        
        analysis = auditor.run_balance_audit()
        
        if analysis:
            print("\n✅ Auditoría de balance completada")
        else:
            print("\n❌ Error en auditoría")
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()