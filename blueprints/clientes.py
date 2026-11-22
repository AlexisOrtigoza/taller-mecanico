from flask import Blueprint, render_template, request, redirect, url_for, abort, flash
from db import obtener_conexion
from psycopg2.extras import RealDictCursor

clientes_bp = Blueprint('clientes', __name__)

@clientes_bp.route('/')
def lista_clientes():
    busqueda = request.args.get('buscar', '').strip()
    try:
        conn = obtener_conexion()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        query = """
            SELECT c.id, c.cedula, c.nombre, c.apellido, c.telefono, c.ciudad, c.barrio,
                   (
                       SELECT COUNT(DISTINCT o.id)
                       FROM vehiculos v
                       JOIN ordenes_trabajo o ON o.vehiculo_id = v.id
                       WHERE v.cliente_id = c.id
                          OR EXISTS (
                              SELECT 1 FROM vehiculo_clientes vc
                              WHERE vc.vehiculo_id = v.id AND vc.cliente_id = c.id
                          )
                   ) AS ordenes_count
            FROM clientes c
        """
        parametros = []
        if busqueda:
            query += """
                WHERE c.cedula ILIKE %s OR c.nombre ILIKE %s OR c.apellido ILIKE %s
                   OR c.telefono ILIKE %s
            """
            patron = f"%{busqueda}%"
            parametros = [patron, patron, patron, patron]
        query += " ORDER BY c.apellido, c.nombre"
        cursor.execute(query, parametros)
        clientes = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('clientes.html', clientes=clientes, busqueda=busqueda)
    except Exception as e:
        return f"Error al cargar los clientes: {e}", 500


@clientes_bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo_cliente():
    cedula_inicial = request.args.get('cedula', '')
    volver_a_orden = request.args.get('volver_a_orden') == '1'
    volver_a_vehiculo = request.args.get('volver_a_vehiculo') == '1'
    retorno_chapa = request.args.get('retorno_chapa') == '1'
    vehiculo_id_regreso = request.args.get('vehiculo_id', '')
    datos_vehiculo = {
        'chapa': request.args.get('chapa', ''),
        'marca': request.args.get('marca', ''),
        'modelo': request.args.get('modelo', ''),
        'anio': request.args.get('anio', ''),
        'kilometraje': request.args.get('kilometraje', '')
    }
    contexto_formulario = {
        'cedula_inicial': cedula_inicial,
        'volver_a_orden': volver_a_orden,
        'volver_a_vehiculo': volver_a_vehiculo,
        'retorno_chapa': retorno_chapa,
        'vehiculo_id_regreso': vehiculo_id_regreso,
        'datos_vehiculo': datos_vehiculo
    }
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
            return render_template(
                'nuevo_cliente.html',
                **contexto_formulario,
                error="Por favor completa todos los campos obligatorios (*)."
            )
        if any(len(campo.strip()) == 0 for campo in (cedula, nombre, apellido, celular)):
            abort(400, 'Los datos obligatorios no pueden estar vacios')
            
        try:
            conn = obtener_conexion()
            cursor = conn.cursor()
            query = """
                INSERT INTO clientes (cedula, nombre, apellido, telefono, direccion, ciudad, barrio, fecha_nacimiento)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            cursor.execute(query, (cedula, nombre, apellido, celular, direccion, ciudad, barrio, fecha_nacimiento))
            cliente_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()
            flash('Cliente registrado correctamente.', 'success')
            if retorno_chapa:
                return redirect(url_for(
                    'ordenes.nueva_orden',
                    modo_busqueda='chapa',
                    chapa=datos_vehiculo['chapa'],
                    cliente_id=cliente_id,
                    vehiculo_id=vehiculo_id_regreso or None
                ))
            if request.args.get('volver_a_orden') == '1':
                return redirect(url_for('ordenes.nueva_orden'))
            if volver_a_vehiculo:
                return redirect(url_for(
                    'vehiculos.nuevo_vehiculo',
                    chapa=datos_vehiculo['chapa'],
                    marca=datos_vehiculo['marca'],
                    modelo=datos_vehiculo['modelo'],
                    anio=datos_vehiculo['anio'],
                    kilometraje=datos_vehiculo['kilometraje'],
                    cliente_id=cliente_id,
                    volver_a_orden='1' if volver_a_orden else None
                ))
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            return render_template(
                'nuevo_cliente.html',
                **contexto_formulario,
                error=f"Error al registrar: {e}"
            )
            
    return render_template('nuevo_cliente.html', **contexto_formulario)


@clientes_bp.route('/<int:cliente_id>/editar', methods=['GET', 'POST'])
def editar_cliente(cliente_id):
    try:
        conn = obtener_conexion()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        if request.method == 'POST':
            cedula = request.form.get('cedula', '').strip()
            nombre = request.form.get('nombre', '').strip()
            apellido = request.form.get('apellido', '').strip()
            telefono = request.form.get('telefono', '').strip()
            direccion = request.form.get('direccion', '').strip() or None
            ciudad = request.form.get('ciudad', '').strip() or None
            barrio = request.form.get('barrio', '').strip() or None
            fecha_nacimiento = request.form.get('fecha_nacimiento') or None

            if not all((cedula, nombre, apellido, telefono)):
                cursor.close()
                conn.close()
                flash('Cédula, nombre, apellido y teléfono son obligatorios.', 'error')
                return redirect(url_for('clientes.editar_cliente', cliente_id=cliente_id))

            cursor.execute(
                "SELECT id FROM clientes WHERE cedula = %s AND id <> %s LIMIT 1",
                (cedula, cliente_id)
            )
            if cursor.fetchone():
                cursor.close()
                conn.close()
                flash('Ya existe otro cliente con ese número de cédula.', 'error')
                return redirect(url_for('clientes.editar_cliente', cliente_id=cliente_id))

            cursor.execute("""
                UPDATE clientes
                SET cedula = %s, nombre = %s, apellido = %s, telefono = %s,
                    direccion = %s, ciudad = %s, barrio = %s, fecha_nacimiento = %s
                WHERE id = %s
                RETURNING id
            """, (cedula, nombre, apellido, telefono, direccion, ciudad, barrio, fecha_nacimiento, cliente_id))
            if not cursor.fetchone():
                conn.rollback()
                cursor.close()
                conn.close()
                return "Cliente no encontrado", 404
            conn.commit()
            cursor.close()
            conn.close()
            flash('Cliente actualizado correctamente.', 'success')
            return redirect(url_for('clientes.lista_clientes'))

        cursor.execute("""
            SELECT id, cedula, nombre, apellido, telefono, direccion, ciudad, barrio, fecha_nacimiento
            FROM clientes WHERE id = %s
        """, (cliente_id,))
        cliente = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as e:
        return f"Error al editar el cliente: {e}", 500
    if not cliente:
        abort(404)
    return render_template('editar_cliente.html', cliente=cliente)


@clientes_bp.route('/<int:cliente_id>/eliminar', methods=['POST'])
def eliminar_cliente(cliente_id):
    conn = None
    cursor = None
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT v.id
            FROM vehiculos v
            WHERE v.cliente_id = %s
               OR EXISTS (
                   SELECT 1 FROM vehiculo_clientes vc
                   WHERE vc.vehiculo_id = v.id AND vc.cliente_id = %s
               )
            ORDER BY v.id
            FOR UPDATE
        """, (cliente_id, cliente_id))
        cursor.fetchall()
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1
                FROM vehiculos v
                JOIN ordenes_trabajo o ON o.vehiculo_id = v.id
                WHERE v.cliente_id = %s
                   OR EXISTS (
                       SELECT 1 FROM vehiculo_clientes vc
                       WHERE vc.vehiculo_id = v.id AND vc.cliente_id = %s
                   )
            )
        """, (cliente_id, cliente_id))
        if cursor.fetchone()[0]:
            conn.rollback()
            flash('No se puede eliminar este cliente porque tiene vehículos con órdenes registradas.', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('clientes.lista_clientes'))
        cursor.execute("UPDATE vehiculos SET cliente_id = NULL WHERE cliente_id = %s", (cliente_id,))
        cursor.execute("DELETE FROM clientes WHERE id = %s RETURNING id", (cliente_id,))
        if not cursor.fetchone():
            conn.rollback()
            flash('No se encontró el cliente.', 'error')
        else:
            conn.commit()
            flash('Cliente eliminado. Los vehículos asociados se conservaron.', 'success')
        cursor.close()
        conn.close()
    except Exception as e:
        if conn:
            conn.rollback()
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        return f"Error al eliminar el cliente: {e}", 500
    return redirect(url_for('clientes.lista_clientes'))
