import psycopg2
from psycopg2.extras import RealDictCursor

# Configuración de tu base de datos
DB_HOST = "localhost"
DB_NAME = "taller-mecanico"
DB_USER = "postgres"
DB_PASS = "931223"
DB_PORT = "5432"

def obtener_conexion():
    conexion = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT
    )
    return conexion
