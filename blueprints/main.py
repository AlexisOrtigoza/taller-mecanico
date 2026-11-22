from flask import Blueprint, render_template, request
from db import obtener_conexion
from psycopg2.extras import RealDictCursor

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def dashboard():
    mostrar_ocultos = request.args.get('ver_ocultos', '0') == '1'
    busqueda = request.args.get('buscar', '').strip()
    estado = request.args.get('estado', '').strip()
    try:
        conn = obtener_conexion()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        condicion_oculto = "TRUE" if mostrar_ocultos else "FALSE"
        query = f"""
            SELECT o.*, v.marca, v.modelo, v.chapa 
            FROM ordenes_trabajo o
            JOIN vehiculos v ON o.vehiculo_id = v.id
            WHERE o.oculto = {condicion_oculto}
        """
        parametros = []
        if estado in ('Pendiente', 'En Proceso', 'Finalizado'):
            query += " AND o.estado = %s"
            parametros.append(estado)
        if busqueda:
            query += " AND (CAST(o.id AS TEXT) ILIKE %s OR v.chapa ILIKE %s OR v.marca ILIKE %s OR v.modelo ILIKE %s)"
            patron = f"%{busqueda}%"
            parametros.extend([patron, patron, patron, patron])
        query += " ORDER BY o.id DESC"

        cursor.execute(query, parametros)
        ordenes = cursor.fetchall()

        cursor.execute("""
            SELECT
                COUNT(*) FILTER (WHERE oculto = FALSE) AS activas,
                COUNT(*) FILTER (WHERE oculto = FALSE AND estado = 'Pendiente') AS pendientes,
                COUNT(*) FILTER (WHERE oculto = FALSE AND estado = 'En Proceso') AS en_proceso,
                COUNT(*) FILTER (WHERE oculto = FALSE AND estado = 'Finalizado') AS finalizadas
            FROM ordenes_trabajo
        """)
        metricas = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return render_template(
            'index.html',
            ordenes=ordenes,
            mostrar_ocultos=mostrar_ocultos,
            busqueda=busqueda,
            estado=estado,
            metricas=metricas
        )
    except Exception as e:
        return f"Error al cargar el dashboard: {e}"
