from datetime import datetime
from supabase import create_client

# Configuración Supabase
SUPABASE_URL = 'https://cxtresumeeybaksjtaqs.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN4dHJlc3VtZWV5YmFrc2p0YXFzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTMwMzE5ODgsImV4cCI6MjA2ODYwNzk4OH0.oo1l7GeAJQOGzM9nMgzFYrxwKNIU9x0B0RJlx7ShSOM'
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class ForexStrategiesCleaner:
    def __init__(self):
        self.table = 'forex_strategies'
        
    def analyze_current_data(self):
        """Analizar datos actuales en forex_strategies"""
        print("📊 ANÁLISIS DE DATOS ACTUALES EN FOREX_STRATEGIES")
        print("=" * 60)
        
        try:
            # Verificar columnas disponibles
            sample = supabase.table(self.table).select("*").limit(1).execute()
            if sample.data:
                columns = list(sample.data[0].keys())
                print(f"📋 Columnas disponibles: {', '.join(columns)}")
                
                if 'source' in columns:
                    print("✅ Columna 'source' detectada correctamente")
                else:
                    print("❌ Columna 'source' no encontrada")
                    return False
            
            # Contar total de registros
            total_response = supabase.table(self.table).select("*", count='exact').execute()
            total_count = total_response.count
            print(f"📈 Total de estrategias: {total_count}")
            
            if total_count > 0:
                # Agrupar por fuente
                all_data = supabase.table(self.table).select("source").execute()
                sources = {}
                for row in all_data.data:
                    source = row.get('source', 'sin_source') or 'null'
                    sources[source] = sources.get(source, 0) + 1
                
                print(f"\n📊 Estrategias por fuente:")
                for source, count in sources.items():
                    if source == 'obplus_authentic_analyzer':
                        print(f"  🎯 {source}: {count} estrategias (CONSERVAR)")
                    else:
                        print(f"  🗑️ {source}: {count} estrategias (ELIMINAR)")
                
                # Contar específicamente OBPlus
                obplus_response = supabase.table(self.table).select("*", count='exact').eq("source", "obplus_authentic_analyzer").execute()
                obplus_count = obplus_response.count
                
                non_obplus_count = total_count - obplus_count
                
                print(f"\n📋 Resumen:")
                print(f"  ✅ Estrategias OBPlus a conservar: {obplus_count}")
                print(f"  ❌ Estrategias a eliminar: {non_obplus_count}")
                
                return True
            else:
                print("ℹ️ La tabla está vacía")
                return True
                
        except Exception as e:
            print(f"❌ Error analizando datos: {e}")
            return False
    
    def backup_obplus_strategies(self):
        """Hacer backup de las estrategias OBPlus"""
        print("\n💾 CREANDO BACKUP DE ESTRATEGIAS OBPLUS")
        print("=" * 50)
        
        try:
            response = supabase.table(self.table).select("*").eq("source", "obplus_authentic_analyzer").execute()
            
            if response.data:
                print(f"✅ {len(response.data)} estrategias OBPlus respaldadas en memoria")
                
                # Mostrar algunas estrategias como ejemplo
                print(f"\n📋 Ejemplo de estrategias OBPlus a conservar:")
                for i, strategy in enumerate(response.data[:3]):  # Mostrar las primeras 3
                    print(f"  {i+1}. {strategy.get('pattern', 'N/A')} - {strategy.get('pair', 'N/A')} {strategy.get('timeframe', 'N/A')} - {strategy.get('effectiveness', 'N/A')}%")
                
                if len(response.data) > 3:
                    print(f"  ... y {len(response.data) - 3} estrategias más")
                
                return response.data
            else:
                print("⚠️ No se encontraron estrategias OBPlus para respaldar")
                return []
                
        except Exception as e:
            print(f"❌ Error haciendo backup: {e}")
            return []
    
    def clean_non_obplus_strategies(self):
        """Eliminar todas las estrategias que NO son OBPlus"""
        print(f"\n🧹 ELIMINANDO ESTRATEGIAS NO-OBPLUS")
        print("=" * 50)
        
        try:
            # Eliminar todo lo que NO sea OBPlus
            response = supabase.table(self.table).delete().neq("source", "obplus_authentic_analyzer").execute()
            
            print("✅ Estrategias no-OBPlus eliminadas")
            
            # Verificar cuántas quedaron
            remaining_response = supabase.table(self.table).select("*", count='exact').execute()
            remaining_count = remaining_response.count
            
            print(f"📊 Estrategias restantes: {remaining_count}")
            
            return remaining_count
            
        except Exception as e:
            print(f"❌ Error eliminando estrategias: {e}")
            return -1
    
    def verify_cleanup_result(self):
        """Verificar el resultado final"""
        print(f"\n✅ VERIFICACIÓN FINAL")
        print("=" * 50)
        
        try:
            # Contar total
            total_response = supabase.table(self.table).select("*", count='exact').execute()
            total_count = total_response.count
            
            # Contar OBPlus
            obplus_response = supabase.table(self.table).select("*", count='exact').eq("source", "obplus_authentic_analyzer").execute()
            obplus_count = obplus_response.count
            
            # Contar otros
            non_obplus_count = total_count - obplus_count
            
            print(f"📊 Resultado en {self.table}:")
            print(f"  📈 Total estrategias: {total_count}")
            print(f"  🎯 Estrategias OBPlus: {obplus_count}")
            print(f"  🗑️ Estrategias no-OBPlus: {non_obplus_count}")
            
            if total_count == obplus_count and obplus_count > 0:
                print(f"  ✅ PERFECTO: Solo estrategias OBPlus auténticas")
            elif total_count == 0:
                print(f"  ⚠️ TABLA VACÍA: No hay estrategias")
            elif non_obplus_count == 0:
                print(f"  ✅ LIMPIO: Solo estrategias OBPlus")
            else:
                print(f"  ❌ AÚN HAY {non_obplus_count} estrategias no-OBPlus")
            
            # Mostrar algunas estrategias finales
            if obplus_count > 0:
                final_strategies = supabase.table(self.table).select("pattern, pair, timeframe, effectiveness").eq("source", "obplus_authentic_analyzer").limit(5).execute()
                print(f"\n📋 Estrategias OBPlus conservadas (primeras 5):")
                for i, strategy in enumerate(final_strategies.data):
                    print(f"  {i+1}. {strategy.get('pattern', 'N/A')} - {strategy.get('pair', 'N/A')} {strategy.get('timeframe', 'N/A')} - {strategy.get('effectiveness', 'N/A')}%")
            
            return total_count == obplus_count and obplus_count > 0
            
        except Exception as e:
            print(f"❌ Error verificando resultado: {e}")
            return False

def main():
    cleaner = ForexStrategiesCleaner()
    
    print("🧹 LIMPIEZA DE FOREX_STRATEGIES - SOLO OBPLUS")
    print("Este script limpiará la tabla forex_strategies conservando")
    print("únicamente las estrategias OBPlus auténticas")
    print("=" * 60)
    
    # Paso 1: Analizar datos actuales
    if not cleaner.analyze_current_data():
        print("❌ No se puede proceder con el análisis")
        return
    
    # Confirmación del usuario
    print("\n" + "=" * 60)
    print("⚠️ ADVERTENCIA: Esta operación eliminará TODAS las estrategias")
    print("de forex_strategies EXCEPTO las que tengan:")
    print("source = 'obplus_authentic_analyzer'")
    print("=" * 60)
    
    confirm = input("\n¿Proceder con la limpieza? (escriba 'CONFIRMO' para continuar): ")
    
    if confirm != 'CONFIRMO':
        print("❌ Operación cancelada por el usuario")
        return
    
    # Paso 2: Hacer backup de estrategias OBPlus
    backup_data = cleaner.backup_obplus_strategies()
    
    if not backup_data:
        print("\n⚠️ No hay estrategias OBPlus para conservar")
        proceed = input("¿Continuar con limpieza completa? (s/n): ")
        if proceed.lower() not in ['s', 'si', 'y', 'yes']:
            print("❌ Operación cancelada")
            return
    
    # Paso 3: Limpiar estrategias no-OBPlus
    print("\n⏳ Iniciando limpieza...")
    remaining_count = cleaner.clean_non_obplus_strategies()
    
    if remaining_count >= 0:
        # Paso 4: Verificar resultado
        success = cleaner.verify_cleanup_result()
        
        if success:
            print("\n🎉 LIMPIEZA COMPLETADA EXITOSAMENTE")
            print("=" * 50)
            print("✅ forex_strategies ahora contiene únicamente estrategias OBPlus")
            print("🔍 Todas las estrategias tienen: source='obplus_authentic_analyzer'")
            print("🎯 Estrategias basadas en análisis real de 1.2M+ velas")
        else:
            print("\n⚠️ Limpieza completada con advertencias")
    else:
        print("\n❌ Error durante la limpieza")

if __name__ == "__main__":
    main()