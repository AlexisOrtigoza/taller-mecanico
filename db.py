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
    """Permite cargar órdenes para vehículos cuyo cliente aún no esté registrado."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("ALTER TABLE vehiculos ALTER COLUMN cliente_id DROP NOT NULL")
        conexion.commit()
    finally:
        cursor.close()
        conexion.close()
