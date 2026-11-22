from flask import Blueprint, render_template, request, redirect, url_for, abort, flash
from db import obtener_conexion

vehiculos_bp = Blueprint('vehiculos', __name__)

@vehiculos_bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo_vehiculo():
    chapa_inicial = request.args.get('chapa', '')
    volver_a_orden = request.args.get('volver_a_orden') == '1'
    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id')
        marca = request.form.get('marca')
        modelo = request.form.get('modelo')
        anio = request.form.get('anio') or None
        chapa = request.form.get('chapa')
        kilometraje = request.form.get('kilometraje') or None

        if not cliente_id or not marca or not modelo or not chapa:
            abort(400, 'Faltan datos obligatorios del vehiculo')
        if any(len(campo.strip()) == 0 for campo in (marca, modelo, chapa)):
            abort(400, 'Los datos del vehiculo no pueden estar vacios')
        if anio is not None:
            try:
                anio_numero = int(anio)
                if anio_numero < 1900 or anio_numero > 2100:
                    abort(400, 'El ano del vehiculo no es valido')
            except (TypeError, ValueError):
                abort(400, 'El ano del vehiculo no es valido')
        if kilometraje is not None:
            try:
                if int(kilometraje) < 0:
                    abort(400, 'El kilometraje no puede ser negativo')
            except (TypeError, ValueError):
                abort(400, 'El kilometraje no es valido')
        
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
            flash('Vehiculo registrado correctamente.', 'success')
            if request.args.get('volver_a_orden') == '1':
                return redirect(url_for('ordenes.nueva_orden'))
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
    return render_template(
        'nuevo_vehiculo.html',
        clientes=clientes,
        chapa_inicial=chapa_inicial,
        volver_a_orden=volver_a_orden
    )
