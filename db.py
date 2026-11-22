import psycopg2
import os
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

def obtener_conexion():
    conexion = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "taller-mecanico"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASS"),
        port=os.getenv("DB_PORT", "5432")
    )
    return conexion


def permitir_vehiculos_sin_cliente():
    """Prepara vehículos para no registrados y para relaciones con varios clientes."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("ALTER TABLE vehiculos ALTER COLUMN cliente_id DROP NOT NULL")
        cursor.execute("""
            ALTER TABLE ordenes_trabajo
            ADD COLUMN IF NOT EXISTS kilometraje_ingreso INTEGER
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vehiculo_clientes (
                vehiculo_id INTEGER NOT NULL REFERENCES vehiculos(id) ON DELETE CASCADE,
                cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
                PRIMARY KEY (vehiculo_id, cliente_id)
            )
        """)
        cursor.execute("""
            INSERT INTO vehiculo_clientes (vehiculo_id, cliente_id)
            SELECT id, cliente_id
            FROM vehiculos
            WHERE cliente_id IS NOT NULL
            ON CONFLICT (vehiculo_id, cliente_id) DO NOTHING
        """)
        conexion.commit()
    finally:
        cursor.close()
        conexion.close()
