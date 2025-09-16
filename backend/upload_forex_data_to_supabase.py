# backend/upload_forex_data_to_supabase.py
import sqlite3
import pandas as pd
from pathlib import Path
import sys
import logging
from datetime import datetime
from typing import List, Dict, Any

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    print(f"📄 Cargando .env desde: {env_path}")
except ImportError:
    pass

# Importar Supabase directamente
from supabase import create_client
import os

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ForexDataUploader:
    """Subir datos históricos de forex desde SQLite a Supabase"""
    
    def __init__(self):
        # Intentar múltiples formas de obtener las variables
        url = (os.getenv('NEXT_PUBLIC_SUPABASE_URL') or 
               os.getenv('SUPABASE_URL') or 
               os.getenv('SUPABASE_PROJECT_URL'))
        
        key = (os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY') or 
               os.getenv('SUPABASE_ANON_KEY') or 
               os.getenv('SUPABASE_KEY'))
        
        print(f"Debug - URL: {url[:20] if url else 'None'}...")
        print(f"Debug - Key: {key[:20] if key else 'None'}...")
        
        if not url or not key:
            print("Variables disponibles:")
            for var in os.environ:
                if 'SUPABASE' in var.upper():
                    print(f"  {var}: {os.environ[var][:20]}...")
            raise ValueError("Variables de entorno de Supabase no encontradas")
        
        self.supabase = create_client(url, key)
        self.data_path = Path("D:/OneDrive/Personal/Programas Jose Valdez/Trading")
        print("✅ Conexión directa con Supabase establecida")
    
    def explore_sqlite_structure(self, db_path: str):
        """Explorar la estructura de la base de datos SQLite"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Obtener lista de tablas
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            print(f"\n📊 ESTRUCTURA DE {db_path}:")
            print("=" * 50)
            
            for table in tables:
                table_name = table[0]
                print(f"\n🗂️ TABLA: {table_name}")
                
                # Obtener estructura de la tabla
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                print("   COLUMNAS:")
                for col in columns:
                    print(f"     - {col[1]} ({col[2]})")
                
                # Obtener muestra de datos
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                sample_data = cursor.fetchall()
                
                print("   MUESTRA DE DATOS:")
                for i, row in enumerate(sample_data[:3]):
                    print(f"     {i+1}: {row}")
                
                # Contar registros
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"   TOTAL REGISTROS: {count:,}")
            
            conn.close()
            return tables
            
        except Exception as e:
            logger.error(f"❌ Error explorando {db_path}: {e}")
            return []
    
    def create_supabase_table(self):
        """Crear tabla en Supabase para datos de forex"""
        
        # SQL para crear tabla
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS forex_candles (
            id BIGSERIAL PRIMARY KEY,
            pair VARCHAR(10) NOT NULL,
            timeframe VARCHAR(5) NOT NULL,
            datetime TIMESTAMP WITH TIME ZONE NOT NULL,
            open DECIMAL(10,5) NOT NULL,
            high DECIMAL(10,5) NOT NULL,
            low DECIMAL(10,5) NOT NULL,
            close DECIMAL(10,5) NOT NULL,
            volume BIGINT DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(pair, timeframe, datetime)
        );
        
        CREATE INDEX IF NOT EXISTS idx_forex_candles_pair_timeframe 
        ON forex_candles(pair, timeframe);
        
        CREATE INDEX IF NOT EXISTS idx_forex_candles_datetime 
        ON forex_candles(datetime);
        """
        
        print("🏗️ Creando tabla forex_candles en Supabase...")
        print("💡 Nota: Debes ejecutar este SQL manualmente en Supabase SQL Editor:")
        print("-" * 60)
        print(create_table_sql)
        print("-" * 60)
        
        return create_table_sql
    
    def read_sqlite_data(self, db_path: str, table_name: str, limit: int = None) -> pd.DataFrame:
        """Leer datos de SQLite y convertir a DataFrame"""
        try:
            conn = sqlite3.connect(db_path)
            
            # Consulta con o sin límite
            if limit:
                query = f"SELECT * FROM {table_name} LIMIT {limit}"
            else:
                query = f"SELECT * FROM {table_name}"
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            logger.info(f"✅ Leídos {len(df)} registros de {table_name}")
            return df
            
        except Exception as e:
            logger.error(f"❌ Error leyendo datos: {e}")
            return pd.DataFrame()
    
    def convert_to_supabase_format(self, df: pd.DataFrame, pair: str, timeframe: str = '1h') -> List[Dict[str, Any]]:
        """Convertir DataFrame a formato para Supabase"""
        
        candles = []
        
        for _, row in df.iterrows():
            try:
                # Adaptación según las columnas que tengas
                # Ajustar nombres de columnas según tu estructura
                
                candle = {
                    'pair': pair,
                    'timeframe': timeframe,
                    'datetime': self.parse_datetime(row),
                    'open': float(row.get('open', row.get('Open', 0))),
                    'high': float(row.get('high', row.get('High', 0))),
                    'low': float(row.get('low', row.get('Low', 0))),
                    'close': float(row.get('close', row.get('Close', 0))),
                    'volume': int(row.get('volume', row.get('Volume', 0)))
                }
                
                candles.append(candle)
                
            except Exception as e:
                logger.warning(f"⚠️ Error procesando fila: {e}")
                continue
        
        logger.info(f"✅ Convertidos {len(candles)} registros para {pair}")
        return candles
    
    def parse_datetime(self, row) -> str:
        """Parsear fecha/hora de diferentes formatos"""
        
        # Intentar diferentes columnas de fecha
        date_columns = ['datetime', 'timestamp', 'date', 'Date', 'Datetime']
        
        for col in date_columns:
            if col in row.index and pd.notna(row[col]):
                try:
                    # Convertir a datetime si no lo es
                    dt = pd.to_datetime(row[col])
                    return dt.isoformat()
                except:
                    continue
        
        # Si no encuentra fecha, usar índice como aproximación
        logger.warning("⚠️ No se pudo parsear fecha, usando timestamp actual")
        return datetime.now().isoformat()
    
    def upload_to_supabase(self, candles: List[Dict[str, Any]], batch_size: int = 1000) -> bool:
        """Subir velas a Supabase en lotes, manejando duplicados"""
        
        try:
            total_uploaded = 0
            total_skipped = 0
            
            for i in range(0, len(candles), batch_size):
                batch = candles[i:i + batch_size]
                
                try:
                    # Insertar usando Supabase directamente
                    response = self.supabase.table('forex_candles').insert(batch).execute()
                    
                    if response.data:
                        total_uploaded += len(batch)
                        logger.info(f"✅ Subido lote {i//batch_size + 1}: {len(batch)} registros")
                    else:
                        logger.warning(f"⚠️ Lote {i//batch_size + 1} sin datos en respuesta")
                        
                except Exception as batch_error:
                    error_msg = str(batch_error)
                    
                    # Si es error de duplicados, intentar insertar uno por uno
                    if 'duplicate key' in error_msg or '23505' in error_msg:
                        logger.warning(f"⚠️ Duplicados en lote {i//batch_size + 1}, insertando individualmente...")
                        
                        batch_uploaded = 0
                        batch_skipped = 0
                        
                        for candle in batch:
                            try:
                                response = self.supabase.table('forex_candles').insert([candle]).execute()
                                if response.data:
                                    batch_uploaded += 1
                            except Exception as single_error:
                                if 'duplicate key' in str(single_error):
                                    batch_skipped += 1
                                else:
                                    logger.error(f"❌ Error insertando vela individual: {single_error}")
                        
                        total_uploaded += batch_uploaded
                        total_skipped += batch_skipped
                        
                        logger.info(f"✅ Lote {i//batch_size + 1}: {batch_uploaded} nuevos, {batch_skipped} duplicados")
                    else:
                        # Si es otro tipo de error, fallar
                        logger.error(f"❌ Error en lote {i//batch_size + 1}: {batch_error}")
                        return False
            
            logger.info(f"🎉 Total procesado: {total_uploaded} subidos, {total_skipped} duplicados saltados")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error general subiendo datos: {e}")
            return False
    
    def process_database(self, db_filename: str, dry_run: bool = True):
        """Procesar una base de datos completa"""
        
        db_path = self.data_path / db_filename
        
        if not db_path.exists():
            logger.error(f"❌ No se encontró: {db_path}")
            return
        
        print(f"\n📂 PROCESANDO: {db_filename}")
        print("=" * 60)
        
        # Explorar estructura
        tables = self.explore_sqlite_structure(str(db_path))
        
        if not tables:
            return
        
        # Procesar solo la tabla forex_data (ignorar sqlite_sequence y download_stats)
        forex_tables = [table for table in tables if table[0] == 'forex_data']
        
        for table in forex_tables:
            table_name = table[0]
            
            if dry_run:
                # Solo mostrar muestra
                df = self.read_sqlite_data(str(db_path), table_name, limit=10)
                print(f"\n🔍 MUESTRA DE {table_name}:")
                print(df.head())
            else:
                # Procesar y subir datos reales
                print(f"\n⬆️ SUBIENDO DATOS DE {table_name}...")
                
                # Leer datos
                df = self.read_sqlite_data(str(db_path), table_name)
                
                if df.empty:
                    continue
                
                # Convertir formato - usar columnas correctas
                candles = self.convert_forex_data(df)
                
                if candles:
                    # Subir a Supabase
                    success = self.upload_to_supabase(candles)
                    if success:
                        print(f"✅ {table_name} subida exitosamente")
                    else:
                        print(f"❌ Error subiendo {table_name}")
    
    def convert_forex_data(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Convertir datos de forex específicos"""
        
        candles = []
        
        for _, row in df.iterrows():
            try:
                # Usar las columnas exactas de tu base de datos
                candle = {
                    'pair': row['pair'].replace('/', ''),  # EUR/USD -> EURUSD
                    'timeframe': row['timeframe'],
                    'datetime': row['timestamp'],  # Ya está en formato correcto
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': int(row.get('volume', 0))
                }
                
                candles.append(candle)
                
            except Exception as e:
                logger.warning(f"⚠️ Error procesando fila: {e}")
                continue
        
        logger.info(f"✅ Convertidos {len(candles)} registros de forex")
        return candles
    
    def guess_pair_from_table(self, table_name: str) -> str:
        """Adivinar par de divisas del nombre de tabla"""
        
        # Pares comunes
        pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD']
        
        table_upper = table_name.upper()
        
        for pair in pairs:
            if pair in table_upper:
                return pair
        
        # Si no encuentra, usar el nombre de tabla
        return table_name.upper()[:6]

def main():
    """Función principal"""
    
    uploader = ForexDataUploader()
    
    # Verificar argumentos
    dry_run = '--execute' not in sys.argv
    
    print("🗄️ SUBIDOR DE DATOS FOREX A SUPABASE")
    print("=" * 50)
    
    if dry_run:
        print("🧪 MODO DRY RUN - Solo exploración")
        print("💡 Usa --execute para subir datos realmente")
    else:
        print("⚠️ MODO EJECUCIÓN - Se subirán datos a Supabase")
        
        # Crear tabla primero
        sql = uploader.create_supabase_table()
        
        print("❓ ¿Has ejecutado el SQL de creación de tabla en Supabase?")
        confirm = input("Continuar? (y/N): ")
        if confirm.lower() != 'y':
            print("❌ Operación cancelada")
            return
    
    # Procesar ambas bases de datos
    databases = ['forex_data.db', 'forex_data_2years.db']
    
    for db in databases:
        uploader.process_database(db, dry_run=dry_run)
    
    if dry_run:
        print("\n💡 Para subir datos realmente:")
        print("1. Ejecuta el SQL de creación de tabla en Supabase")
        print("2. Ejecuta: python upload_forex_data_to_supabase.py --execute")

if __name__ == "__main__":
    main()