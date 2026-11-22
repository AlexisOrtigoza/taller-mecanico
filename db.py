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
