from flask import Blueprint, render_template, request, redirect, url_for
from db import obtener_conexion

vehiculos_bp = Blueprint('vehiculos', __name__)

@vehiculos_bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo_vehiculo():
    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id')
        marca = request.form.get('marca')
        modelo = request.form.get('modelo')
        anio = request.form.get('anio') or None
        chapa = request.form.get('chapa')
        kilometraje = request.form.get('kilometraje') or None
        
        try:
            conn = obtener_conexion()
            cursor = conn.cursor()
            query = """
                INSERT INTO vehiculos (cliente_id, marca, modelo, anio, chapa, kilometraje)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (cliente_id, marca, modelo, anio, chapa, kilometraje))
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            conn = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("SELECT id, cedula, nombre, apellido FROM clientes ORDER BY nombre;")
            clientes = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template('nuevo_vehiculo.html', clientes=clientes, error=f"Error al registrar vehículo: {e}")
            
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT id, cedula, nombre, apellido FROM clientes ORDER BY nombre;")
        clientes = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        clientes = []
    return render_template('nuevo_vehiculo.html', clientes=clientes)
