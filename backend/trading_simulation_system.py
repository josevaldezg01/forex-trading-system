from datetime import datetime, timedelta
from collections import Counter
from supabase import create_client
import json
import warnings
warnings.filterwarnings('ignore')

# Configuración Supabase
SUPABASE_URL = 'https://cxtresumeeybaksjtaqs.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN4dHJlc3VtZWV5YmFrc2p0YXFzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTMwMzE5ODgsImV4cCI6MjA2ODYwNzk4OH0.oo1l7GeAJQOGzM9nMgzFYrxwKNIU9x0B0RJlx7ShSOM'
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class OBPlusSimulator:
    def __init__(self, initial_capital=1000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        # Configuración de riesgo conservadora para $1000
        self.base_trade_amount = 10  # $10 por operación base
        self.payout_rate = 0.80  # 80% payout típico en binarias
        self.max_daily_loss = 0.10  # Máximo 10% pérdida diaria
        self.max_trade_risk = 0.08  # Máximo 8% del capital por secuencia MG
        
        # Límites de Martingala
        self.mg_levels = {
            'MG0': 1,   # Sin martingala
            'MG1': 2,   # Hasta 2 intentos
            'MG2': 3    # Hasta 3 intentos
        }
        
        self.simulation_results = []
        
    def load_obplus_strategies(self):
        """Cargar estrategias OBPlus de forex_strategies_master (excluyendo momentum_continuacion)"""
        try:
            result = supabase.table("forex_strategies_master") \
                .select("*") \
                .eq("source", "obplus_authentic_analyzer") \
                .neq("pattern", "momentum_continuacion") \
                .gte("effectiveness", 60.0) \
                .order("effectiveness", desc=True) \
                .execute()
            
            if result.data:
                print(f"✅ Cargadas {len(result.data)} estrategias OBPlus para simulación")
                print(f"📊 Fuente: forex_strategies_master (excluyendo momentum_continuacion)")
                
                # Mostrar algunas estrategias cargadas
                print("📈 Top 5 estrategias cargadas:")
                for i, strategy in enumerate(result.data[:5]):
                    print(f"  {i+1}. {strategy['pattern']} - {strategy['pair']} {strategy['timeframe']} - {strategy['effectiveness']}%")
                
                # Mostrar distribución por timeframe
                timeframes = {}
                patterns = {}
                for strategy in result.data:
                    tf = strategy['timeframe']
                    pattern = strategy['pattern']
                    timeframes[tf] = timeframes.get(tf, 0) + 1
                    patterns[pattern] = patterns.get(pattern, 0) + 1
                
                print(f"📊 Distribución por timeframe:")
                for tf, count in sorted(timeframes.items()):
                    print(f"  - {tf}: {count} estrategias")
                
                print(f"📋 Distribución por patrón OBPlus:")
                for pattern, count in sorted(patterns.items()):
                    print(f"  - {pattern}: {count} estrategias")
                
                return result.data
            else:
                print("❌ No se encontraron estrategias OBPlus en forex_strategies_master")
                return None
                
        except Exception as e:
            print(f"❌ Error cargando estrategias: {e}")
            return None
    
    def load_historical_data(self, pair, timeframe, days_back=30):
        """Cargar datos históricos para simulación"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            result = supabase.table("forex_candles") \
                .select("*") \
                .eq("pair", pair) \
                .eq("timeframe", timeframe) \
                .gte("datetime", start_date.isoformat()) \
                .order("datetime") \
                .execute()
            
            if result.data:
                # Convertir a formato manejable y agregar color
                candles = []
                for row in result.data:
                    candle = {
                        'datetime': row['datetime'],
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'color': 'V' if float(row['close']) >= float(row['open']) else 'R'
                    }
                    candles.append(candle)
                
                candles.sort(key=lambda x: x['datetime'])
                print(f"📈 Cargadas {len(candles)} velas para {pair} {timeframe}")
                return candles
            else:
                print(f"❌ Sin datos para {pair} {timeframe}")
                return None
                
        except Exception as e:
            print(f"❌ Error cargando datos históricos para {pair} {timeframe}: {e}")
            return None
    
    def create_non_overlapping_fragments(self, candles):
        """Crear fragmentos de 5 velas NO solapados (como trading real)"""
        fragments = []
        
        # Dividir en grupos de exactamente 5 velas sin solapamiento
        for i in range(0, len(candles) - 4, 5):  # Incrementar de 5 en 5
            if i + 4 < len(candles):  # Asegurar que hay 5 velas completas
                fragment_candles = candles[i:i+5]
                colors = [candle['color'] for candle in fragment_candles]
                
                fragments.append({
                    'start_idx': i,
                    'candles': fragment_candles,
                    'colors': colors,
                    'start_time': fragment_candles[0]['datetime'],
                    'end_time': fragment_candles[4]['datetime'],
                    'fragment_number': len(fragments) + 1
                })
        
        print(f"📊 Fragmentos NO solapados creados: {len(fragments)} (cada 5 velas)")
        return fragments
    
    def check_obplus_pattern(self, strategy, fragments, current_idx):
        """Verificar si se cumple el patrón OBPlus específico en fragmentos no solapados"""
        if current_idx >= len(fragments):
            return False, None
        
        pattern = strategy['pattern']
        current_fragment = fragments[current_idx]
        
        try:
            if pattern == 'tres_mosqueteros':
                # Vela central → siguiente vela (mismo fragmento)
                if len(current_fragment['colors']) >= 4:
                    central_color = current_fragment['colors'][2]  # Vela central
                    predicted_color = central_color
                    return True, predicted_color
            
            elif pattern == 'mejor_de_3':
                # 3 velas centrales → vela central siguiente fragmento
                # Solo se puede operar si hay un fragmento siguiente
                if current_idx < len(fragments) - 1:
                    central_colors = current_fragment['colors'][1:4]  # Velas 1,2,3
                    majority_color = Counter(central_colors).most_common(1)[0][0]
                    return True, majority_color
            
            elif pattern == 'milhao_maioria':
                # 3 velas centrales → primera vela siguiente fragmento
                if current_idx < len(fragments) - 1:
                    central_colors = current_fragment['colors'][1:4]  # Velas 1,2,3
                    majority_color = Counter(central_colors).most_common(1)[0][0]
                    return True, majority_color
            
            elif pattern == 'mhi_3':
                # Color minoritario → entrada específica
                if current_idx < len(fragments) - 1:
                    central_colors = current_fragment['colors'][1:4]
                    color_count = Counter(central_colors)
                    if len(color_count) > 1:
                        minority_color = color_count.most_common()[-1][0]
                        return True, minority_color
            
            elif pattern == 'padrao_23':
                # Vela patrón (pos 2) → entrada en pos 3
                if len(current_fragment['colors']) >= 3:
                    pattern_color = current_fragment['colors'][1]  # Posición 2
                    return True, pattern_color
            
            elif pattern == 'padrao_impar':
                # Vela central → primera vela siguiente fragmento
                if current_idx < len(fragments) - 1:
                    central_color = current_fragment['colors'][2]  # Vela central
                    return True, central_color
            
            elif pattern == 'torres_gemeas':
                # Primera vela → última vela mismo fragmento
                if len(current_fragment['colors']) >= 5:
                    first_color = current_fragment['colors'][0]  # Primera vela
                    return True, first_color
            
            # Estrategias adicionales
            elif pattern == 'extremos_opuestos':
                if len(current_fragment['colors']) >= 5:
                    first_color = current_fragment['colors'][0]
                    predicted_opposite = 'R' if first_color == 'V' else 'V'
                    return True, predicted_opposite
            
            elif pattern == 'simetria_central':
                if len(current_fragment['colors']) >= 4:
                    second_color = current_fragment['colors'][1]  # Vela 2
                    return True, second_color
        
        except Exception as e:
            print(f"❌ Error verificando patrón {pattern}: {e}")
        
        return False, None
    
    def get_actual_outcome(self, strategy, fragments, current_idx):
        """Obtener el resultado real según la metodología de la estrategia"""
        pattern = strategy['pattern']
        current_fragment = fragments[current_idx]
        
        try:
            if pattern == 'tres_mosqueteros':
                # Resultado en vela 4 del mismo fragmento
                if len(current_fragment['colors']) >= 4:
                    return current_fragment['colors'][3]
            
            elif pattern in ['mejor_de_3', 'milhao_maioria', 'mhi_3']:
                # Resultado en siguiente fragmento
                if current_idx < len(fragments) - 1:
                    next_fragment = fragments[current_idx + 1]
                    if pattern == 'mejor_de_3':
                        return next_fragment['colors'][2]  # Vela central siguiente
                    elif pattern == 'milhao_maioria':
                        return next_fragment['colors'][0]  # Primera vela siguiente
                    elif pattern == 'mhi_3':
                        return next_fragment['colors'][2]  # Vela central siguiente
            
            elif pattern == 'padrao_23':
                # Resultado en vela 3 del mismo fragmento
                if len(current_fragment['colors']) >= 3:
                    return current_fragment['colors'][2]
            
            elif pattern == 'padrao_impar':
                # Resultado en primera vela siguiente fragmento
                if current_idx < len(fragments) - 1:
                    next_fragment = fragments[current_idx + 1]
                    return next_fragment['colors'][0]
            
            elif pattern == 'torres_gemeas':
                # Resultado en última vela mismo fragmento
                if len(current_fragment['colors']) >= 5:
                    return current_fragment['colors'][4]
            
            elif pattern == 'extremos_opuestos':
                # Resultado en última vela mismo fragmento
                if len(current_fragment['colors']) >= 5:
                    return current_fragment['colors'][4]
            
            elif pattern == 'simetria_central':
                # Resultado en vela 4 mismo fragmento
                if len(current_fragment['colors']) >= 4:
                    return current_fragment['colors'][3]
            
            elif pattern == 'momentum_continuacion':
                # Resultado en primera vela siguiente fragmento
                if current_idx < len(fragments) - 1:
                    next_fragment = fragments[current_idx + 1]
                    return next_fragment['colors'][0]
        
        except Exception as e:
            print(f"❌ Error obteniendo resultado para {pattern}: {e}")
        
        return None
    
    def execute_trade_sequence(self, predicted_direction, actual_outcome, mg_level='MG0'):
        """Simular secuencia de trading con Martingala"""
        sequence_cost = 0
        trades_in_sequence = []
        success = False
        
        # Convertir colores a direcciones
        predicted_call_put = 'CALL' if predicted_direction == 'V' else 'PUT'
        actual_call_put = 'CALL' if actual_outcome == 'V' else 'PUT'
        
        max_attempts = self.mg_levels[mg_level]
        
        for attempt in range(max_attempts):
            # Calcular monto de la operación
            if attempt == 0:
                trade_amount = self.base_trade_amount
            else:
                # Martingala: calcular monto para recuperar pérdidas + ganancia original
                previous_losses = sum(trade['amount'] for trade in trades_in_sequence)
                trade_amount = (previous_losses + self.base_trade_amount) / self.payout_rate
                trade_amount = round(trade_amount, 2)
            
            # Verificar límites de riesgo
            if sequence_cost + trade_amount > self.current_capital * self.max_trade_risk:
                print(f"⚠️ Operación cancelada: excede límite de riesgo por secuencia")
                break
            
            sequence_cost += trade_amount
            
            # Simular resultado de la operación
            trade_won = predicted_call_put == actual_call_put
            
            if trade_won:
                profit = trade_amount * self.payout_rate
                self.current_capital += profit
                success = True
                
                trades_in_sequence.append({
                    'attempt': attempt + 1,
                    'amount': trade_amount,
                    'result': 'WIN',
                    'profit': profit
                })
                break
            else:
                self.current_capital -= trade_amount
                
                trades_in_sequence.append({
                    'attempt': attempt + 1,
                    'amount': trade_amount,
                    'result': 'LOSS',
                    'profit': -trade_amount
                })
        
        return {
            'success': success,
            'total_cost': sequence_cost,
            'final_profit': sum(trade['profit'] for trade in trades_in_sequence),
            'trades': trades_in_sequence,
            'attempts_made': len(trades_in_sequence),
            'predicted': predicted_call_put,
            'actual': actual_call_put
        }
    
    def simulate_strategy(self, strategy, days_back=30, mg_level='MG0'):
        """Simular una estrategia OBPlus específica"""
        print(f"\n--- Simulando {strategy['pattern']} - {strategy['pair']} {strategy['timeframe']} ({mg_level}) ---")
        
        # Cargar datos históricos
        candles = self.load_historical_data(strategy['pair'], strategy['timeframe'], days_back)
        if candles is None or len(candles) < 20:
            print(f"❌ Datos insuficientes para {strategy['pair']} {strategy['timeframe']}")
            return None
        
        # Crear fragmentos de 5 velas
        fragments = self.create_5_candle_fragments(candles)
        if len(fragments) < 10:
            print(f"❌ Fragmentos insuficientes: {len(fragments)}")
            return None
        
        # Reset capital para esta simulación
        self.current_capital = self.initial_capital
        
        simulation_log = []
        daily_limit_hit = False
        
        for i in range(len(fragments) - 1):
            # Verificar límite diario
            daily_loss = self.initial_capital - self.current_capital
            if daily_loss > self.initial_capital * self.max_daily_loss:
                daily_limit_hit = True
                print(f"⚠️ Límite diario de pérdida alcanzado: ${daily_loss:.2f}")
                break
            
            # Verificar si se cumple el patrón OBPlus
            pattern_match, predicted_direction = self.check_obplus_pattern(strategy, fragments, i)
            
            if pattern_match and predicted_direction:
                # Obtener resultado real
                actual_outcome = self.get_actual_outcome(strategy, fragments, i)
                
                if actual_outcome:
                    # Ejecutar secuencia de trading
                    trade_result = self.execute_trade_sequence(predicted_direction, actual_outcome, mg_level)
                    
                    simulation_log.append({
                        'timestamp': fragments[i]['start_time'],
                        'pattern_detected': True,
                        'predicted': trade_result['predicted'],
                        'actual': trade_result['actual'],
                        'success': trade_result['success'],
                        'total_cost': trade_result['total_cost'],
                        'final_profit': trade_result['final_profit'],
                        'attempts': trade_result['attempts_made'],
                        'capital_after': self.current_capital,
                        'trade_details': trade_result['trades']
                    })
        
        # Calcular estadísticas de la simulación
        if simulation_log:
            total_operations = len(simulation_log)
            successful_operations = sum(1 for log in simulation_log if log['success'])
            win_rate = successful_operations / total_operations if total_operations > 0 else 0
            
            total_profit = self.current_capital - self.initial_capital
            roi = (total_profit / self.initial_capital) * 100
            
            # Calcular drawdown máximo
            capital_curve = [self.initial_capital]
            for log in simulation_log:
                capital_curve.append(log['capital_after'])
            
            peak = self.initial_capital
            max_drawdown = 0
            for capital in capital_curve:
                if capital > peak:
                    peak = capital
                current_drawdown = ((peak - capital) / peak) * 100
                if current_drawdown > max_drawdown:
                    max_drawdown = current_drawdown
            
            results = {
                'strategy_name': f"{strategy['pattern']} - {strategy['pair']} {strategy['timeframe']}",
                'pattern': strategy['pattern'],
                'pair': strategy['pair'],
                'timeframe': strategy['timeframe'],
                'effectiveness_db': strategy['effectiveness'],
                'mg_level': mg_level,
                'initial_capital': self.initial_capital,
                'final_capital': self.current_capital,
                'total_profit': total_profit,
                'roi_percentage': roi,
                'total_operations': total_operations,
                'successful_operations': successful_operations,
                'win_rate': win_rate,
                'max_drawdown': max_drawdown,
                'daily_limit_hit': daily_limit_hit,
                'avg_profit_per_operation': total_profit / total_operations if total_operations > 0 else 0,
                'simulation_log': simulation_log
            }
            
            return results
        else:
            print("❌ No se encontraron patrones en el período simulado")
            return None
    
    def compare_mg_levels(self, strategy, days_back=30):
        """Comparar resultados de una estrategia con diferentes niveles de MG"""
        print(f"\n{'='*60}")
        print(f"COMPARACIÓN MG PARA: {strategy['pattern']}")
        print(f"Par: {strategy['pair']} | Timeframe: {strategy['timeframe']}")
        print(f"Efectividad DB: {strategy['effectiveness']}%")
        print(f"{'='*60}")
        
        mg_results = {}
        
        for mg_level in ['MG0', 'MG1', 'MG2']:
            result = self.simulate_strategy(strategy, days_back, mg_level)
            if result:
                mg_results[mg_level] = result
                
                print(f"\n{mg_level} - Resumen:")
                print(f"  Capital final: ${result['final_capital']:.2f}")
                print(f"  Ganancia/Pérdida: ${result['total_profit']:.2f}")
                print(f"  ROI: {result['roi_percentage']:.2f}%")
                print(f"  Operaciones: {result['total_operations']}")
                print(f"  Tasa éxito simulación: {result['win_rate']:.2%}")
                print(f"  Efectividad DB: {result['effectiveness_db']:.1f}%")
                print(f"  Drawdown máximo: {result['max_drawdown']:.2f}%")
                
                if result['daily_limit_hit']:
                    print(f"  ⚠️ Límite diario alcanzado")
        
        return mg_results
    
    def generate_risk_report(self, mg_results):
        """Generar reporte de riesgo comparativo"""
        if not mg_results:
            return
        
        print(f"\n{'='*60}")
        print(f"REPORTE DE RIESGO - ANÁLISIS COMPARATIVO")
        print(f"{'='*60}")
        
        best_roi = max(mg_results.values(), key=lambda x: x['roi_percentage'])
        safest = min(mg_results.values(), key=lambda x: x['max_drawdown'])
        
        print(f"\n📊 MÉTRICAS COMPARATIVAS:")
        print(f"{'Nivel':<6} {'ROI%':<8} {'Operaciones':<12} {'Éxito%':<8} {'Drawdown%':<12} {'Límite hit':<12}")
        print("-" * 70)
        
        for mg_level, result in mg_results.items():
            limit_status = "SÍ" if result['daily_limit_hit'] else "NO"
            print(f"{mg_level:<6} {result['roi_percentage']:<8.2f} {result['total_operations']:<12} {result['win_rate']*100:<8.1f} {result['max_drawdown']:<12.2f} {limit_status:<12}")
        
        print(f"\n🏆 MEJOR ROI: {best_roi['mg_level']} ({best_roi['roi_percentage']:.2f}%)")
        print(f"🛡️ MÁS SEGURO: {safest['mg_level']} (Drawdown: {safest['max_drawdown']:.2f}%)")
        
        # Advertencias de riesgo
        print(f"\n⚠️ ADVERTENCIAS DE RIESGO:")
        for mg_level, result in mg_results.items():
            if result['max_drawdown'] > 20:
                print(f"  - {mg_level}: Drawdown peligroso ({result['max_drawdown']:.1f}%)")
            if result['daily_limit_hit']:
                print(f"  - {mg_level}: Alcanzó límite diario de pérdida")
            if result['total_operations'] < 5:
                print(f"  - {mg_level}: Muy pocas operaciones para conclusiones ({result['total_operations']})")
    
    def run_comprehensive_simulation(self, top_strategies=10, days_back=30):
        """Ejecutar simulación comprehensiva de las mejores estrategias OBPlus"""
        strategies = self.load_obplus_strategies()
        if not strategies:
            return
        
        # Seleccionar las mejores estrategias
        selected_strategies = strategies[:top_strategies]
        
        print(f"\n🎯 SIMULACIÓN COMPREHENSIVA - TOP {len(selected_strategies)} ESTRATEGIAS OBPLUS")
        print(f"💰 Capital inicial: ${self.initial_capital}")
        print(f"📅 Período de simulación: {days_back} días")
        print(f"💵 Monto base por operación: ${self.base_trade_amount}")
        print(f"📊 Total disponible en forex_strategies_master: {len(strategies)} estrategias")
        print(f"🎯 Estrategias basadas en análisis real de 1.2M+ velas")
        
        all_results = {}
        
        for strategy in selected_strategies:
            mg_comparison = self.compare_mg_levels(strategy, days_back)
            if mg_comparison:
                strategy_key = f"{strategy['pattern']}_{strategy['pair']}_{strategy['timeframe']}"
                all_results[strategy_key] = mg_comparison
                self.generate_risk_report(mg_comparison)
        
        # Resumen final
        print(f"\n{'='*60}")
        print(f"RESUMEN FINAL DE SIMULACIÓN OBPLUS")
        print(f"{'='*60}")
        print(f"Estrategias simuladas: {len(all_results)}")
        print(f"Estrategias disponibles totales: {len(strategies)}")
        print(f"Capital inicial total: ${self.initial_capital}")
        print(f"Metodologías analizadas: 7 OBPlus auténticas + adicionales")
        
        return all_results

def main():
    print("🎯 SISTEMA DE SIMULACIÓN OBPLUS")
    print("Análisis de riesgo y efectividad con Martingala")
    print("Basado en estrategias auténticas de 1.2M+ velas")
    print(f"💰 Capital inicial configurado: $1,000")
    
    simulator = OBPlusSimulator(initial_capital=1000)
    
    print("\nOpciones:")
    print("1. Simulación rápida (5 mejores estrategias, 15 días)")
    print("2. Simulación completa (10 mejores estrategias, 30 días)")
    print("3. Simular estrategia específica")
    print("4. Análisis intensivo (todas las estrategias, 45 días)")
    
    choice = input("\nElige una opción (1-4): ")
    
    if choice == "1":
        simulator.run_comprehensive_simulation(top_strategies=5, days_back=15)
    elif choice == "2":
        simulator.run_comprehensive_simulation(top_strategies=10, days_back=30)
    elif choice == "3":
        strategies = simulator.load_obplus_strategies()
        if strategies:
            print("\n🎯 Estrategias OBPlus disponibles:")
            for i, strategy in enumerate(strategies[:15], 1):
                print(f"{i:2d}. {strategy['pattern']} - {strategy['pair']} {strategy['timeframe']} - {strategy['effectiveness']}%")
            
            try:
                strategy_idx = int(input("\nElige número de estrategia: ")) - 1
                if 0 <= strategy_idx < len(strategies):
                    selected_strategy = strategies[strategy_idx]
                    simulator.compare_mg_levels(selected_strategy)
                else:
                    print("❌ Número inválido")
            except:
                print("❌ Selección inválida")
    elif choice == "4":
        simulator.run_comprehensive_simulation(top_strategies=20, days_back=45)
    else:
        print("❌ Opción inválida")

if __name__ == "__main__":
    main()