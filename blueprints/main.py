from flask import Blueprint, render_template, request
from db import obtener_conexion
from psycopg2.extras import RealDictCursor

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def dashboard():
    mostrar_ocultos = request.args.get('ver_ocultos', '0') == '1'
    try:
        conn = obtener_conexion()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        condicion_oculto = "TRUE" if mostrar_ocultos else "FALSE"
        query = f"""
            SELECT o.*, v.marca, v.modelo, v.chapa 
            FROM ordenes_trabajo o
            JOIN vehiculos v ON o.vehiculo_id = v.id
            WHERE o.oculto = {condicion_oculto}
            ORDER BY o.id DESC
        """
        cursor.execute(query)
        ordenes = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('index.html', ordenes=ordenes, mostrar_ocultos=mostrar_ocultos)
    except Exception as e:
        return f"Error al cargar el dashboard: {e}"
