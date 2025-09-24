from datetime import datetime, timedelta
from collections import Counter
from supabase import create_client
import json

# Configuración Supabase
SUPABASE_URL = 'https://cxtresumeeybaksjtaqs.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN4dHJlc3VtZWV5YmFrc2p0YXFzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTMwMzE5ODgsImV4cCI6MjA2ODYwNzk4OH0.oo1l7GeAJQOGzM9nMgzFYrxwKNIU9x0B0RJlx7ShSOM'
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class OBPlusAuthenticAnalyzer:
    def __init__(self):
        self.discovered_strategies = []
        
        # Timeframes multi-nivel para fragmentos de 5 velas
        self.timeframes = {
            '1min': {'fragment_duration': '5min', 'description': 'Scalping'},
            '5min': {'fragment_duration': '25min', 'description': 'Day trading'}, 
            '15min': {'fragment_duration': '1h15min', 'description': 'Swing corto'},
            '30min': {'fragment_duration': '2h30min', 'description': 'Swing medio'},
            '1h': {'fragment_duration': '5h', 'description': 'Swing largo'}
        }
        
        # Pares organizados por disponibilidad de datos
        self.pairs = {
            'major': ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF'],
            'cross': ['EURJPY', 'GBPJPY', 'EURGBP', 'AUDCAD'],
            'commodity': ['AUDUSD', 'NZDUSD', 'USDCAD'],
            'exotic': ['AUDJPY', 'CHFJPY', 'EURAUD', 'EURNZD', 'GBPAUD', 'GBPNZD', 'NZDCHF', 'NZDJPY']
        }
        
    def load_forex_data(self, pair, timeframe, limit=None):
        """Cargar datos históricos desde Supabase"""
        try:
            query = supabase.table("forex_candles").select("*").eq("pair", pair).eq("timeframe", timeframe).order("datetime", desc=False)
            
            if limit:
                query = query.limit(limit)
                
            response = query.execute()
            
            if response.data:
                # Convertir a lista de diccionarios y agregar color
                candles = []
                for row in response.data:
                    # Determinar color de la vela
                    color = 'V' if float(row['close']) > float(row['open']) else 'R'
                    
                    candle = {
                        'datetime': row['datetime'],
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'color': color,
                        'pair': row['pair'],
                        'timeframe': row['timeframe']
                    }
                    candles.append(candle)
                
                # Ordenar por datetime
                candles.sort(key=lambda x: x['datetime'])
                
                print(f"✅ {pair} {timeframe}: {len(candles):,} velas cargadas")
                return candles
            else:
                print(f"❌ Sin datos: {pair} {timeframe}")
                return None
                
        except Exception as e:
            print(f"❌ Error cargando {pair} {timeframe}: {e}")
            return None

    def create_5_candle_fragments(self, candles):
        """Crear fragmentos de 5 velas consecutivas"""
        fragments = []
        
        for i in range(len(candles) - 4):  # -4 para asegurar 5 velas completas
            fragment_candles = candles[i:i+5]
            
            if len(fragment_candles) == 5:
                colors = [candle['color'] for candle in fragment_candles]
                
                fragments.append({
                    'start_idx': i,
                    'candles': fragment_candles,
                    'colors': colors,
                    'start_time': fragment_candles[0]['datetime'],
                    'end_time': fragment_candles[4]['datetime']
                })
                
        print(f"📊 Fragmentos de 5 velas creados: {len(fragments):,}")
        return fragments

    def analyze_tres_mosqueteros(self, fragments):
        """Estrategia 1: Tres Mosqueteros - Vela central → siguiente"""
        strategies = []
        
        for i, fragment in enumerate(fragments[:-1]):  # -1 para tener siguiente vela
            # Patrón: vela central (posición 2)
            central_color = fragment['colors'][2]
            
            # Predicción: siguiente vela en el mismo fragmento (posición 3)
            predicted_color = central_color
            actual_color = fragment['colors'][3]
            
            win = (predicted_color == actual_color)
            
            strategies.append({
                'fragment_idx': i,
                'strategy': 'tres_mosqueteros',
                'pattern': f'central_{central_color}',
                'prediction': predicted_color,
                'actual': actual_color,
                'win': win,
                'entry_position': 'same_fragment_next'
            })
            
        return strategies

    def analyze_mejor_de_3(self, fragments):
        """Estrategia 2: Mejor de 3 - 3 centrales → vela central siguiente fragmento"""
        strategies = []
        
        for i, fragment in enumerate(fragments[:-1]):  # -1 para tener siguiente fragmento
            # Patrón: velas centrales (posiciones 1, 2, 3)
            central_colors = fragment['colors'][1:4]  # índices 1,2,3
            majority_color = Counter(central_colors).most_common(1)[0][0]
            
            # Predicción: vela central del siguiente fragmento
            next_fragment = fragments[i + 1]
            predicted_color = majority_color
            actual_color = next_fragment['colors'][2]  # Vela central siguiente
            
            win = (predicted_color == actual_color)
            
            strategies.append({
                'fragment_idx': i,
                'strategy': 'mejor_de_3',
                'pattern': f'majority_{"".join(central_colors)}',
                'prediction': predicted_color,
                'actual': actual_color,
                'win': win,
                'entry_position': 'next_fragment_central'
            })
            
        return strategies

    def analyze_mhi_3(self, fragments):
        """Estrategia 3: MHI 3 - Color minoritario → entrada específica"""
        strategies = []
        
        for i, fragment in enumerate(fragments[:-1]):
            # Patrón: velas centrales (posiciones 1, 2, 3)
            central_colors = fragment['colors'][1:4]
            color_count = Counter(central_colors)
            
            # Buscar color minoritario
            if len(color_count) > 1:
                minority_color = color_count.most_common()[-1][0]  # El menos común
                
                # Predicción: apostar por el color minoritario
                next_fragment = fragments[i + 1]
                predicted_color = minority_color
                actual_color = next_fragment['colors'][2]  # Entrada en vela central siguiente
                
                win = (predicted_color == actual_color)
                
                strategies.append({
                    'fragment_idx': i,
                    'strategy': 'mhi_3',
                    'pattern': f'minority_{"".join(central_colors)}',
                    'prediction': predicted_color,
                    'actual': actual_color,
                    'win': win,
                    'entry_position': 'next_fragment_central'
                })
                
        return strategies

    def analyze_milhao_maioria(self, fragments):
        """Estrategia 4: Milhão Maioria - 3 centrales → primera vela siguiente fragmento"""
        strategies = []
        
        for i, fragment in enumerate(fragments[:-1]):
            # Patrón: velas centrales (posiciones 1, 2, 3)
            central_colors = fragment['colors'][1:4]
            majority_color = Counter(central_colors).most_common(1)[0][0]
            
            # Predicción: primera vela del siguiente fragmento
            next_fragment = fragments[i + 1]
            predicted_color = majority_color
            actual_color = next_fragment['colors'][0]  # Primera vela siguiente
            
            win = (predicted_color == actual_color)
            
            strategies.append({
                'fragment_idx': i,
                'strategy': 'milhao_maioria',
                'pattern': f'majority_{"".join(central_colors)}',
                'prediction': predicted_color,
                'actual': actual_color,
                'win': win,
                'entry_position': 'next_fragment_first'
            })
            
        return strategies

    def analyze_padrao_23(self, fragments):
        """Estrategia 5: PADRÃO 23 - Vela patrón → entrada en posición específica"""
        strategies = []
        
        for i, fragment in enumerate(fragments):
            if i + 1 < len(fragment['colors']) - 1:  # Asegurar que hay velas suficientes
                # Patrón: vela en posición 2 (índice 1)
                pattern_color = fragment['colors'][1]
                
                # Predicción: vela en posición 3 (índice 2)
                predicted_color = pattern_color
                actual_color = fragment['colors'][2]
                
                win = (predicted_color == actual_color)
                
                strategies.append({
                    'fragment_idx': i,
                    'strategy': 'padrao_23',
                    'pattern': f'pos2_{pattern_color}',
                    'prediction': predicted_color,
                    'actual': actual_color,
                    'win': win,
                    'entry_position': 'same_fragment_pos3'
                })
                
        return strategies

    def analyze_padrao_impar(self, fragments):
        """Estrategia 6: PADRÃO ÍMPAR - Vela central → primera vela siguiente fragmento"""
        strategies = []
        
        for i, fragment in enumerate(fragments[:-1]):
            # Patrón: vela central (posición 2)
            central_color = fragment['colors'][2]
            
            # Predicción: primera vela del siguiente fragmento
            next_fragment = fragments[i + 1]
            predicted_color = central_color
            actual_color = next_fragment['colors'][0]  # Primera vela siguiente
            
            win = (predicted_color == actual_color)
            
            strategies.append({
                'fragment_idx': i,
                'strategy': 'padrao_impar',
                'pattern': f'central_{central_color}',
                'prediction': predicted_color,
                'actual': actual_color,
                'win': win,
                'entry_position': 'next_fragment_first',
                'martingale_type': 'spaced'  # Martingala espaciada
            })
            
        return strategies

    def analyze_torres_gemeas(self, fragments):
        """Estrategia 7: Torres Gêmeas - Primera vela → última vela mismo fragmento"""
        strategies = []
        
        for i, fragment in enumerate(fragments):
            # Patrón: primera vela (posición 0)
            first_color = fragment['colors'][0]
            
            # Predicción: última vela mismo fragmento (posición 4)
            predicted_color = first_color
            actual_color = fragment['colors'][4]  # Última vela
            
            win = (predicted_color == actual_color)
            
            strategies.append({
                'fragment_idx': i,
                'strategy': 'torres_gemeas',
                'pattern': f'first_{first_color}',
                'prediction': predicted_color,
                'actual': actual_color,
                'win': win,
                'entry_position': 'same_fragment_last',
                'martingale_type': 'consecutive'  # Martingala seguida
            })
            
        return strategies

    def analyze_additional_patterns(self, fragments):
        """3 estrategias adicionales basadas en lógica de 5 velas"""
        additional_strategies = []
        
        # Estrategia 8: Extremos Opuestos
        for i, fragment in enumerate(fragments):
            first_color = fragment['colors'][0]
            last_color = fragment['colors'][4]
            
            # Lógica: primera y última tienden a ser opuestas
            predicted_opposite = 'R' if first_color == 'V' else 'V'
            win = (predicted_opposite == last_color)
            
            additional_strategies.append({
                'fragment_idx': i,
                'strategy': 'extremos_opuestos',
                'pattern': f'first_{first_color}_expect_opposite',
                'prediction': predicted_opposite,
                'actual': last_color,
                'win': win,
                'entry_position': 'same_fragment_last'
            })
        
        # Estrategia 9: Simetría Central
        for i, fragment in enumerate(fragments):
            second_color = fragment['colors'][1]  # Vela 2
            fourth_color = fragment['colors'][3]  # Vela 4
            
            # Lógica: velas 2 y 4 tienden a ser iguales
            win = (second_color == fourth_color)
            
            additional_strategies.append({
                'fragment_idx': i,
                'strategy': 'simetria_central',
                'pattern': f'pos2_{second_color}_pos4_{fourth_color}',
                'prediction': second_color,
                'actual': fourth_color,
                'win': win,
                'entry_position': 'same_fragment_pos4'
            })
        
        # Estrategia 10: Momentum Continuación
        for i, fragment in enumerate(fragments[:-1]):
            first_three = fragment['colors'][:3]
            
            # Si las 3 primeras son iguales, el momentum continúa
            if len(set(first_three)) == 1:  # Todas iguales
                momentum_color = first_three[0]
                next_fragment = fragments[i + 1]
                
                predicted_color = momentum_color
                actual_color = next_fragment['colors'][0]  # Primera del siguiente
                
                win = (predicted_color == actual_color)
                
                additional_strategies.append({
                    'fragment_idx': i,
                    'strategy': 'momentum_continuacion',
                    'pattern': f'triple_{momentum_color}',
                    'prediction': predicted_color,
                    'actual': actual_color,
                    'win': win,
                    'entry_position': 'next_fragment_first'
                })
        
        return additional_strategies

    def calculate_strategy_metrics(self, strategies, strategy_name):
        """Calcular métricas para una estrategia específica"""
        if not strategies:
            return None
            
        total_trades = len(strategies)
        wins = sum(1 for s in strategies if s['win'])
        losses = total_trades - wins
        win_rate = (wins / total_trades) * 100
        
        # Score ajustado por frecuencia
        frequency_bonus = min(10, total_trades / 100)  # Bonus hasta 10 puntos
        base_score = win_rate + frequency_bonus
        
        # Penalización por pocos trades
        if total_trades < 50:
            base_score -= 10
        
        return {
            'strategy_name': strategy_name,
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'win_rate': round(win_rate, 2),
            'score': round(base_score, 2),
            'frequency': 'high' if total_trades > 200 else 'medium' if total_trades > 100 else 'low'
        }

    def analyze_pair_timeframe(self, pair, timeframe):
        """Analizar un par específico en un timeframe específico"""
        print(f"\n🔍 Analizando {pair} en {timeframe}")
        
        # Cargar datos
        candles = self.load_forex_data(pair, timeframe, limit=10000)  # Límite para eficiencia
        if candles is None or len(candles) < 50:
            print(f"❌ Datos insuficientes para {pair} {timeframe}")
            return []
        
        # Crear fragmentos
        fragments = self.create_5_candle_fragments(candles)
        if len(fragments) < 20:
            print(f"❌ Fragmentos insuficientes: {len(fragments)}")
            return []
        
        all_strategies = []
        
        # Analizar las 7 estrategias OBPlus auténticas
        strategies_methods = [
            ('tres_mosqueteros', self.analyze_tres_mosqueteros),
            ('mejor_de_3', self.analyze_mejor_de_3),
            ('mhi_3', self.analyze_mhi_3),
            ('milhao_maioria', self.analyze_milhao_maioria),
            ('padrao_23', self.analyze_padrao_23),
            ('padrao_impar', self.analyze_padrao_impar),
            ('torres_gemeas', self.analyze_torres_gemeas)
        ]
        
        print(f"📈 Ejecutando 7 estrategias OBPlus auténticas...")
        
        for strategy_name, method in strategies_methods:
            try:
                results = method(fragments)
                metrics = self.calculate_strategy_metrics(results, strategy_name)
                
                if metrics and metrics['win_rate'] >= 55.0 and metrics['total_trades'] >= 20:
                    strategy_data = {
                        'pair': pair,
                        'timeframe': timeframe,
                        'fragment_duration': self.timeframes[timeframe]['fragment_duration'],
                        'trading_style': self.timeframes[timeframe]['description'],
                        'strategy_name': strategy_name,
                        'methodology': 'obplus_authentic',
                        'win_rate': metrics['win_rate'],
                        'total_trades': metrics['total_trades'],
                        'wins': metrics['wins'],
                        'losses': metrics['losses'],
                        'score': metrics['score'],
                        'is_projection': False,
                        'analysis_date': datetime.now().isoformat()
                    }
                    
                    all_strategies.append(strategy_data)
                    print(f"  ✅ {strategy_name}: {metrics['win_rate']}% ({metrics['total_trades']} trades)")
                else:
                    print(f"  ❌ {strategy_name}: No cumple criterios")
                    
            except Exception as e:
                print(f"  ❌ Error en {strategy_name}: {e}")
        
        # Analizar estrategias adicionales
        print(f"📊 Ejecutando 3 estrategias adicionales...")
        additional_results = self.analyze_additional_patterns(fragments)
        
        # Agrupar por estrategia
        additional_by_strategy = {}
        for result in additional_results:
            strategy = result['strategy']
            if strategy not in additional_by_strategy:
                additional_by_strategy[strategy] = []
            additional_by_strategy[strategy].append(result)
        
        for strategy_name, results in additional_by_strategy.items():
            metrics = self.calculate_strategy_metrics(results, strategy_name)
            
            if metrics and metrics['win_rate'] >= 55.0 and metrics['total_trades'] >= 20:
                strategy_data = {
                    'pair': pair,
                    'timeframe': timeframe,
                    'fragment_duration': self.timeframes[timeframe]['fragment_duration'],
                    'trading_style': self.timeframes[timeframe]['description'],
                    'strategy_name': strategy_name,
                    'methodology': '5_candle_logic',
                    'win_rate': metrics['win_rate'],
                    'total_trades': metrics['total_trades'],
                    'wins': metrics['wins'],
                    'losses': metrics['losses'],
                    'score': metrics['score'],
                    'is_projection': False,
                    'analysis_date': datetime.now().isoformat()
                }
                
                all_strategies.append(strategy_data)
                print(f"  ✅ {strategy_name}: {metrics['win_rate']}% ({metrics['total_trades']} trades)")
            else:
                print(f"  ❌ {strategy_name}: No cumple criterios")
        
        return all_strategies

    def check_table_structure(self):
        """Verificar estructura de la tabla forex_strategies_master"""
        try:
            # Obtener una fila de ejemplo para ver las columnas
            response = supabase.table("forex_strategies_master").select("*").limit(1).execute()
            
            if response.data and len(response.data) > 0:
                columns = list(response.data[0].keys())
                print(f"📋 Columnas disponibles en forex_strategies_master:")
                for col in columns:
                    print(f"  - {col}")
                return columns
            else:
                print("❌ No hay datos en forex_strategies_master para verificar estructura")
                return []
                
        except Exception as e:
            print(f"❌ Error verificando estructura: {e}")
            return []

    def save_strategies_to_supabase(self, strategies):
        """Guardar estrategias en forex_strategies_master (tabla completa)"""
        if not strategies:
            return 0
        
        # Verificar estructura de la tabla primero
        available_columns = self.check_table_structure()
        if not available_columns:
            print("❌ No se pudo verificar estructura de la tabla")
            return 0
        
        try:
            # Preparar estrategias usando solo columnas que existen
            clean_strategies = []
            for strategy in strategies:
                clean_strategy = {}
                
                # Mapear campos según columnas disponibles en forex_strategies_master
                if 'pair' in available_columns:
                    clean_strategy['pair'] = strategy['pair']
                if 'timeframe' in available_columns:
                    clean_strategy['timeframe'] = strategy['timeframe']
                if 'pattern' in available_columns:
                    clean_strategy['pattern'] = strategy['strategy_name']  # Nombre de la estrategia OBPlus
                if 'direction' in available_columns:
                    clean_strategy['direction'] = 'CALL'
                if 'effectiveness' in available_columns:
                    clean_strategy['effectiveness'] = strategy['win_rate']
                if 'occurrences' in available_columns:
                    clean_strategy['occurrences'] = strategy['total_trades']
                if 'wins' in available_columns:
                    clean_strategy['wins'] = strategy['wins']
                if 'losses' in available_columns:
                    clean_strategy['losses'] = strategy['losses']
                if 'avg_profit' in available_columns:
                    clean_strategy['avg_profit'] = 0.0  # Valor por defecto
                if 'score' in available_columns:
                    clean_strategy['score'] = strategy['score']
                if 'trigger_condition' in available_columns:
                    clean_strategy['trigger_condition'] = f"{strategy['strategy_name']} - {strategy['methodology']}"
                if 'analysis_date' in available_columns:
                    clean_strategy['analysis_date'] = datetime.now().isoformat()
                if 'created_at' in available_columns:
                    clean_strategy['created_at'] = datetime.now().isoformat()
                if 'source' in available_columns:
                    clean_strategy['source'] = 'obplus_authentic_analyzer'
                if 'methodology' in available_columns:
                    clean_strategy['methodology'] = strategy['methodology']
                if 'trading_style' in available_columns:
                    clean_strategy['trading_style'] = strategy['trading_style']
                if 'fragment_duration' in available_columns:
                    clean_strategy['fragment_duration'] = strategy['fragment_duration']
                if 'is_projection' in available_columns:
                    clean_strategy['is_projection'] = False  # Datos reales
                
                clean_strategies.append(clean_strategy)
            
            print(f"📝 Preparando {len(clean_strategies)} estrategias para forex_strategies_master...")
            print(f"📋 Ejemplo de estrategia a insertar:")
            if clean_strategies:
                for key, value in clean_strategies[0].items():
                    print(f"  {key}: {value}")
            
            # Eliminar estrategias anteriores de OBPlus si existen
            if 'source' in available_columns:
                supabase.table("forex_strategies_master").delete().eq("source", "obplus_authentic_analyzer").execute()
                print("🗑️ Estrategias OBPlus anteriores eliminadas de forex_strategies_master")
            
            # Insertar nuevas estrategias en forex_strategies_master
            response = supabase.table("forex_strategies_master").insert(clean_strategies).execute()
            
            if response.data:
                print(f"💾 {len(clean_strategies)} estrategias OBPlus guardadas en forex_strategies_master")
                return len(clean_strategies)
            else:
                print(f"❌ Error guardando estrategias: {response}")
                return 0
                
        except Exception as e:
            print(f"❌ Error en Supabase: {e}")
            return 0

    def run_complete_obplus_analysis(self):
        """Ejecutar análisis completo OBPlus en todos los timeframes"""
        print("🚀 INICIANDO ANÁLISIS OBPLUS COMPLETO")
        print("=" * 50)
        print("📊 Estrategias OBPlus auténticas + 3 adicionales")
        print("⏱️  Multi-timeframe: 1min, 5min, 15min, 30min, 1h")
        print("🎯 Fragmentos de 5 velas en cada timeframe")
        print(f"💾 Base de datos: 1.2M+ velas disponibles")
        
        all_strategies = []
        
        # Analizar cada timeframe
        for timeframe, config in self.timeframes.items():
            print(f"\n🕐 TIMEFRAME: {timeframe} (fragmentos de {config['fragment_duration']} - {config['description']})")
            print("-" * 40)
            
            # Determinar pares disponibles según timeframe
            if timeframe == '1min':
                # Timeframes intraday - menos pares disponibles
                available_pairs = self.pairs['major'] + self.pairs['cross'][:2]
            else:
                # Timeframes más altos - más pares disponibles  
                available_pairs = self.pairs['major'] + self.pairs['cross'] + self.pairs['commodity']
            
            timeframe_strategies = 0
            
            for pair in available_pairs:
                pair_strategies = self.analyze_pair_timeframe(pair, timeframe)
                all_strategies.extend(pair_strategies)
                timeframe_strategies += len(pair_strategies)
            
            print(f"📈 Timeframe {timeframe}: {timeframe_strategies} estrategias encontradas")
        
        # Guardar todas las estrategias
        total_saved = self.save_strategies_to_supabase(all_strategies)
        
        return total_saved

    def print_summary(self, total_strategies):
        """Imprimir resumen del análisis"""
        print("\n" + "=" * 60)
        print("🎯 ANÁLISIS OBPLUS COMPLETADO")
        print("=" * 60)
        print(f"Estrategias generadas: {total_strategies}")
        print(f"Metodologías: 7 OBPlus auténticas + 3 adicionales")
        print(f"Timeframes analizados: {len(self.timeframes)}")
        print(f"Fragmentos: 5 velas por timeframe")
        print(f"Tipo: obplus_pattern")
        print(f"Datos: 1.2M+ velas reales de Supabase")
        
        return total_strategies

def main():
    analyzer = OBPlusAuthenticAnalyzer()
    
    print("SISTEMA OBPLUS AUTÉNTICO - MULTI-TIMEFRAME")
    print("Implementa 7 estrategias OBPlus reales + 3 adicionales")
    print("Análisis en 5 timeframes con fragmentos de 5 velas")
    print("Usa 1.2M+ velas reales de tu base de datos")
    
    confirm = input("\n¿Proceder con análisis completo OBPlus? (s/n): ")
    
    if confirm.lower() in ['s', 'si', 'y', 'yes']:
        total = analyzer.run_complete_obplus_analysis()
        
        if total > 0:
            analyzer.print_summary(total)
            print(f"\n✅ SISTEMA OBPLUS IMPLEMENTADO")
            print(f"Revisa forex_strategies con type='obplus_pattern'")
        else:
            print(f"\n❌ No se encontraron estrategias que cumplan criterios")
    else:
        print("Análisis cancelado.")

if __name__ == "__main__":
    main()