from flask import Blueprint, render_template, request, redirect, url_for
from db import obtener_conexion

clientes_bp = Blueprint('clientes', __name__)

@clientes_bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo_cliente():
    if request.method == 'POST':
        cedula = request.form.get('cedula')
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        celular = request.form.get('celular')
        direccion = request.form.get('direccion') or None
        ciudad = request.form.get('ciudad') or None
        barrio = request.form.get('barrio') or None
        fecha_nacimiento = request.form.get('fecha_nacimiento') or None
        
        if not cedula or not nombre or not apellido or not celular:
            return render_template('nuevo_cliente.html', error="Por favor completa todos los campos obligatorios (*).")
            
        try:
            conn = obtener_conexion()
            cursor = conn.cursor()
            query = """
                INSERT INTO clientes (cedula, nombre, apellido, telefono, direccion, ciudad, barrio, fecha_nacimiento)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (cedula, nombre, apellido, celular, direccion, ciudad, barrio, fecha_nacimiento))
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            return render_template('nuevo_cliente.html', error=f"Error al registrar: {e}")
            
    return render_template('nuevo_cliente.html')
