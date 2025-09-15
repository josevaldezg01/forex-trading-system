# backend/strategy_audit.py
import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict, Counter

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

class StrategyAuditor:
    """Auditor completo de estrategias para diagnóstico"""
    
    def __init__(self):
        self.db_client = create_supabase_client()
    
    def get_all_strategies(self) -> List[Dict[str, Any]]:
        """Obtener todas las estrategias"""
        try:
            strategies = self.db_client.get_recent_strategies(limit=2000)
            logger.info(f"📊 Total estrategias obtenidas: {len(strategies)}")
            return strategies
        except Exception as e:
            logger.error(f"❌ Error obteniendo estrategias: {e}")
            return []
    
    def analyze_distribution(self, strategies: List[Dict[str, Any]]):
        """Analizar distribución completa de estrategias"""
        
        print("\n🔍 ANÁLISIS COMPLETO DE ESTRATEGIAS")
        print("=" * 60)
        
        # Contar por timeframe
        timeframe_counts = Counter(s.get('timeframe', 'unknown') for s in strategies)
        
        print(f"\n📊 DISTRIBUCIÓN POR TEMPORALIDAD:")
        total = 0
        for tf, count in sorted(timeframe_counts.items()):
            print(f"   {tf}: {count} estrategias")
            total += count
        print(f"   TOTAL: {total} estrategias")
        
        # Solo estrategias de 1d para análisis detallado
        day_strategies = [s for s in strategies if s.get('timeframe') == '1d']
        
        if not day_strategies:
            print("\n❌ No se encontraron estrategias de 1d")
            return
        
        print(f"\n📈 ANÁLISIS DETALLADO DE ESTRATEGIAS 1d ({len(day_strategies)} total):")
        print("-" * 50)
        
        # Análisis por dirección
        direction_counts = Counter(s.get('direction', 'unknown') for s in day_strategies)
        print(f"\n🎯 POR DIRECCIÓN:")
        for direction, count in direction_counts.items():
            print(f"   {direction}: {count} estrategias")
        
        # Análisis por patrón
        pattern_counts = Counter(s.get('pattern', 'unknown') for s in day_strategies)
        print(f"\n🔢 POR PATRÓN:")
        for pattern, count in sorted(pattern_counts.items()):
            print(f"   {pattern}: {count} estrategias")
        
        # Análisis por tipo
        type_counts = Counter(s.get('type', 'unknown') for s in day_strategies)
        print(f"\n🏷️ POR TIPO:")
        for type_name, count in type_counts.items():
            print(f"   {type_name}: {count} estrategias")
        
        # Análisis por par
        pair_counts = Counter(s.get('pair', 'unknown') for s in day_strategies)
        print(f"\n💱 POR PAR DE DIVISAS:")
        for pair, count in sorted(pair_counts.items()):
            print(f"   {pair}: {count} estrategias")
        
        # Estrategias espejo
        mirror_strategies = [s for s in day_strategies if s.get('type') == 'mirror_strategy']
        original_strategies = [s for s in day_strategies if s.get('type') != 'mirror_strategy']
        
        print(f"\n🪞 ESTRATEGIAS ESPEJO:")
        print(f"   Originales: {len(original_strategies)}")
        print(f"   Espejos: {len(mirror_strategies)}")
        print(f"   Total: {len(original_strategies) + len(mirror_strategies)}")
        
        return {
            'total': len(day_strategies),
            'by_direction': dict(direction_counts),
            'by_pattern': dict(pattern_counts),
            'by_type': dict(type_counts),
            'by_pair': dict(pair_counts),
            'originals': len(original_strategies),
            'mirrors': len(mirror_strategies)
        }
    
    def find_missing_strategies(self, strategies: List[Dict[str, Any]]):
        """Encontrar estrategias que deberían existir pero no están"""
        
        day_strategies = [s for s in strategies if s.get('timeframe') == '1d']
        
        print(f"\n🔍 BÚSQUEDA DE ESTRATEGIAS FALTANTES:")
        print("-" * 50)
        
        # Agrupar por patrón y dirección
        strategy_map = defaultdict(list)
        for strategy in day_strategies:
            key = f"{strategy['pattern']}_{strategy['direction']}"
            strategy_map[key].append(strategy)
        
        # Patrones esperados
        green_patterns = ['V', 'VV', 'VVV', 'VVVV']
        red_patterns = ['R', 'RR', 'RRR', 'RRRR']
        
        missing_count = 0
        
        print(f"\n📋 MATRIZ DE PATRONES ESPERADOS:")
        print(f"{'Patrón':<8} {'CALL':<6} {'PUT':<6} {'Estado'}")
        print("-" * 30)
        
        # Verificar cada combinación esperada
        all_patterns = green_patterns + red_patterns
        for pattern in all_patterns:
            call_key = f"{pattern}_CALL"
            put_key = f"{pattern}_PUT"
            
            call_exists = len(strategy_map[call_key]) > 0
            put_exists = len(strategy_map[put_key]) > 0
            
            call_status = "✓" if call_exists else "❌"
            put_status = "✓" if put_exists else "❌"
            
            if pattern in green_patterns:
                expected_call = "✓"
                expected_put = "❌" if pattern in ['V', 'VV', 'VVV', 'VVVV'] else "✓"
            else:  # red patterns
                expected_call = "❌" if pattern in ['R', 'RR', 'RRR', 'RRRR'] else "✓"
                expected_put = "✓"
            
            status = "OK"
            if (expected_call == "✓" and not call_exists) or (expected_put == "✓" and not put_exists):
                status = "FALTA"
                missing_count += 1
            
            print(f"{pattern:<8} {call_status:<6} {put_status:<6} {status}")
        
        print(f"\n📊 RESUMEN DE FALTANTES:")
        print(f"   Estrategias faltantes detectadas: {missing_count}")
        
        # Mostrar detalles de estrategias existentes
        print(f"\n📝 DETALLES DE ESTRATEGIAS EXISTENTES:")
        for key, strategies in sorted(strategy_map.items()):
            if strategies:
                pattern, direction = key.split('_')
                pairs = [s['pair'] for s in strategies]
                print(f"   {pattern} {direction}: {len(strategies)} estrategias - Pares: {', '.join(sorted(set(pairs)))}")
    
    def suggest_missing_strategies(self, strategies: List[Dict[str, Any]]):
        """Sugerir qué estrategias crear para completar el set"""
        
        day_strategies = [s for s in strategies if s.get('timeframe') == '1d']
        
        # Obtener estrategias originales (no espejos)
        original_strategies = [s for s in day_strategies if s.get('type') != 'mirror_strategy']
        
        print(f"\n💡 SUGERENCIAS PARA COMPLETAR ESTRATEGIAS:")
        print("-" * 50)
        
        if len(original_strategies) < 17:
            missing_originals = 17 - len(original_strategies)
            print(f"   Faltan {missing_originals} estrategias originales")
            print(f"   Recomendación: Re-ejecutar el analizador de patrones con criterios más flexibles")
        
        # Verificar espejos
        mirror_strategies = [s for s in day_strategies if s.get('type') == 'mirror_strategy']
        
        if len(mirror_strategies) < len(original_strategies):
            missing_mirrors = len(original_strategies) - len(mirror_strategies)
            print(f"   Faltan {missing_mirrors} estrategias espejo")
            print(f"   Recomendación: Re-ejecutar create_mirror_strategies.py")
        
        total_expected = len(original_strategies) * 2  # originales + espejos
        total_actual = len(day_strategies)
        
        print(f"\n📊 RESUMEN:")
        print(f"   Esperadas: {total_expected} (17 originales + 17 espejos)")
        print(f"   Actuales: {total_actual}")
        print(f"   Faltantes: {total_expected - total_actual}")
    
    def run_complete_audit(self):
        """Ejecutar auditoría completa"""
        try:
            strategies = self.get_all_strategies()
            if not strategies:
                print("❌ No se pudieron obtener estrategias")
                return
            
            # Análisis completo
            analysis = self.analyze_distribution(strategies)
            
            # Buscar faltantes
            self.find_missing_strategies(strategies)
            
            # Sugerencias
            self.suggest_missing_strategies(strategies)
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error en auditoría: {e}")
            return None

def main():
    """Función principal"""
    try:
        auditor = StrategyAuditor()
        
        print("🔍 AUDITORÍA COMPLETA DE ESTRATEGIAS")
        print("=" * 40)
        
        analysis = auditor.run_complete_audit()
        
        if analysis:
            print("\n✅ Auditoría completada")
        else:
            print("\n❌ Error en auditoría")
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()