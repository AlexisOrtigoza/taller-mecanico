from flask import Blueprint, render_template, request, redirect, url_for, abort, flash
from db import obtener_conexion

clientes_bp = Blueprint('clientes', __name__)

@clientes_bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo_cliente():
    cedula_inicial = request.args.get('cedula', '')
    volver_a_orden = request.args.get('volver_a_orden') == '1'
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
        if any(len(campo.strip()) == 0 for campo in (cedula, nombre, apellido, celular)):
            abort(400, 'Los datos obligatorios no pueden estar vacios')
            
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
            flash('Cliente registrado correctamente.', 'success')
            if request.args.get('volver_a_orden') == '1':
                return redirect(url_for('ordenes.nueva_orden'))
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            return render_template('nuevo_cliente.html', error=f"Error al registrar: {e}")
            
    return render_template(
        'nuevo_cliente.html',
        cedula_inicial=cedula_inicial,
        volver_a_orden=volver_a_orden
    )
