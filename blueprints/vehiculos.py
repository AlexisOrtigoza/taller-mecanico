from flask import Blueprint, render_template, request, redirect, url_for, abort, flash
from db import obtener_conexion
from psycopg2.extras import RealDictCursor

vehiculos_bp = Blueprint('vehiculos', __name__)

@vehiculos_bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo_vehiculo():
    chapa_inicial = request.args.get('chapa', '')
    volver_a_orden = request.args.get('volver_a_orden') == '1'
    cliente_id_inicial = request.args.get('cliente_id', '')
    datos_iniciales = {
        'marca': request.args.get('marca', ''),
        'modelo': request.args.get('modelo', ''),
        'anio': request.args.get('anio', ''),
        'kilometraje': request.args.get('kilometraje', '')
    }

    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id') or None
        vehiculo_id = request.form.get('vehiculo_id') or None
        marca = request.form.get('marca', '').strip()
        modelo = request.form.get('modelo', '').strip()
        anio = request.form.get('anio') or None
        chapa = request.form.get('chapa', '').strip()
        kilometraje = request.form.get('kilometraje') or None

        if vehiculo_id:
            if not cliente_id:
                abort(400, 'Selecciona un cliente para asociarlo al vehículo existente')
            try:
                conn = obtener_conexion()
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM vehiculos WHERE id = %s", (vehiculo_id,))
                if not cursor.fetchone():
                    conn.rollback()
                    abort(404, 'El vehículo seleccionado ya no existe')
                cursor.execute("""
                    INSERT INTO vehiculo_clientes (vehiculo_id, cliente_id)
                    VALUES (%s, %s)
                    ON CONFLICT (vehiculo_id, cliente_id) DO NOTHING
                """, (vehiculo_id, cliente_id))
                conn.commit()
                cursor.close()
                conn.close()
                flash('Vehículo asociado al cliente correctamente.', 'success')
                if volver_a_orden:
                    return redirect(url_for(
                        'ordenes.nueva_orden',
                        modo_busqueda='chapa',
                        chapa=chapa,
                        cliente_id=cliente_id,
                        vehiculo_id=vehiculo_id
                    ))
                return redirect(url_for('main.dashboard'))
            except Exception as e:
                return render_template(
                    'nuevo_vehiculo.html',
                    error=f"Error al asociar el vehículo: {e}",
                    chapa_inicial=chapa,
                    volver_a_orden=volver_a_orden,
                    datos_iniciales=datos_iniciales,
                    cliente_id_inicial=cliente_id,
                    cliente_inicial=None
                ), 400

        if not marca or not modelo or not chapa:
            abort(400, 'Marca, modelo y chapa son obligatorios')
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
            cursor.execute("""
                SELECT id FROM vehiculos
                WHERE UPPER(REPLACE(REPLACE(chapa, ' ', ''), '-', '')) =
                      UPPER(REPLACE(REPLACE(%s, ' ', ''), '-', ''))
                LIMIT 1
            """, (chapa,))
            if cursor.fetchone():
                cursor.close()
                conn.close()
                return render_template(
                    'nuevo_vehiculo.html',
                    error=f'La chapa {chapa} ya está registrada. Busca el vehículo existente antes de continuar.',
                    chapa_inicial=chapa,
                    volver_a_orden=volver_a_orden,
                    datos_iniciales={'marca': marca, 'modelo': modelo, 'anio': anio or '', 'kilometraje': kilometraje or ''},
                    cliente_id_inicial=cliente_id or ''
                ), 409

            query = """
                INSERT INTO vehiculos (cliente_id, marca, modelo, anio, chapa, kilometraje)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            cursor.execute(query, (cliente_id, marca, modelo, anio, chapa, kilometraje))
            vehiculo_id = cursor.fetchone()[0]
            if cliente_id:
                cursor.execute("""
                    INSERT INTO vehiculo_clientes (vehiculo_id, cliente_id)
                    VALUES (%s, %s)
                    ON CONFLICT (vehiculo_id, cliente_id) DO NOTHING
                """, (vehiculo_id, cliente_id))
            conn.commit()
            cursor.close()
            conn.close()
            flash('Vehiculo registrado correctamente.', 'success')
            if request.args.get('volver_a_orden') == '1':
                return redirect(url_for(
                    'ordenes.nueva_orden',
                    modo_busqueda='chapa',
                    chapa=chapa,
                    cliente_id=cliente_id,
                    vehiculo_id=vehiculo_id
                ))
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            return render_template(
                'nuevo_vehiculo.html',
                error=f"Error al registrar vehículo: {e}",
                chapa_inicial=chapa,
                volver_a_orden=volver_a_orden,
                datos_iniciales={'marca': marca, 'modelo': modelo, 'anio': anio or '', 'kilometraje': kilometraje or ''},
                cliente_id_inicial=cliente_id or ''
            ), 400

    cliente_inicial = None
    if cliente_id_inicial:
        try:
            conn = obtener_conexion()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT id, cedula, nombre, apellido FROM clientes WHERE id = %s", (cliente_id_inicial,))
            cliente_inicial = cursor.fetchone()
            cursor.close()
            conn.close()
        except Exception as e:
            return f"Error al cargar el cliente: {e}", 500

    return render_template(
        'nuevo_vehiculo.html',
        chapa_inicial=chapa_inicial,
        volver_a_orden=volver_a_orden,
        datos_iniciales=datos_iniciales,
        cliente_id_inicial=cliente_id_inicial,
        cliente_inicial=cliente_inicial
    )


@vehiculos_bp.route('/')
def lista_vehiculos():
    busqueda = request.args.get('buscar', '').strip()
    try:
        conn = obtener_conexion()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        query = """
            SELECT v.id, v.marca, v.modelo, v.anio, v.chapa, v.kilometraje,
                   COUNT(DISTINCT o.id) AS ordenes_count,
                   string_agg(DISTINCT c.nombre || ' ' || c.apellido, ', ') AS clientes
            FROM vehiculos v
            LEFT JOIN vehiculo_clientes vc ON vc.vehiculo_id = v.id
            LEFT JOIN clientes c ON c.id = vc.cliente_id
            LEFT JOIN ordenes_trabajo o ON o.vehiculo_id = v.id
        """
        parametros = []
        if busqueda:
            query += """
                WHERE v.chapa ILIKE %s OR v.marca ILIKE %s OR v.modelo ILIKE %s
            """
            patron = f"%{busqueda}%"
            parametros = [patron, patron, patron]
        query += """
            GROUP BY v.id
            ORDER BY v.chapa
        """
        cursor.execute(query, parametros)
        vehiculos = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('vehiculos.html', vehiculos=vehiculos, busqueda=busqueda)
    except Exception as e:
        return f"Error al cargar los vehículos: {e}", 500


@vehiculos_bp.route('/<int:vehiculo_id>/editar', methods=['GET', 'POST'])
def editar_vehiculo(vehiculo_id):
    try:
        conn = obtener_conexion()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        if request.method == 'POST':
            marca = request.form.get('marca', '').strip()
            modelo = request.form.get('modelo', '').strip()
            anio = request.form.get('anio') or None
            chapa = request.form.get('chapa', '').strip()
            if not marca or not modelo or not chapa:
                cursor.close()
                conn.close()
                flash('Marca, modelo y chapa son obligatorios.', 'error')
                return redirect(url_for('vehiculos.editar_vehiculo', vehiculo_id=vehiculo_id))
            if anio is not None:
                try:
                    anio_numero = int(anio)
                    if anio_numero < 1900 or anio_numero > 2100:
                        raise ValueError
                except ValueError:
                    cursor.close()
                    conn.close()
                    flash('El año del vehículo debe estar entre 1900 y 2100.', 'error')
                    return redirect(url_for('vehiculos.editar_vehiculo', vehiculo_id=vehiculo_id))

            cursor.execute("""
                SELECT id FROM vehiculos
                WHERE UPPER(REPLACE(REPLACE(chapa, ' ', ''), '-', '')) =
                      UPPER(REPLACE(REPLACE(%s, ' ', ''), '-', ''))
                  AND id <> %s
                LIMIT 1
            """, (chapa, vehiculo_id))
            if cursor.fetchone():
                cursor.close()
                conn.close()
                flash('Ya existe otro vehículo registrado con esa chapa.', 'error')
                return redirect(url_for('vehiculos.editar_vehiculo', vehiculo_id=vehiculo_id))

            cursor.execute("""
                UPDATE vehiculos
                SET marca = %s, modelo = %s, anio = %s, chapa = %s
                WHERE id = %s
                RETURNING id
            """, (marca, modelo, anio, chapa, vehiculo_id))
            if not cursor.fetchone():
                conn.rollback()
                cursor.close()
                conn.close()
                return "Vehículo no encontrado", 404
            conn.commit()
            cursor.close()
            conn.close()
            flash('Vehículo actualizado correctamente.', 'success')
            return redirect(url_for('vehiculos.lista_vehiculos'))

        cursor.execute("""
            SELECT id, marca, modelo, anio, chapa, kilometraje
            FROM vehiculos WHERE id = %s
        """, (vehiculo_id,))
        vehiculo = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as e:
        return f"Error al editar el vehículo: {e}", 500
    if not vehiculo:
        abort(404)
    return render_template('editar_vehiculo.html', vehiculo=vehiculo)


@vehiculos_bp.route('/<int:vehiculo_id>/eliminar', methods=['POST'])
def eliminar_vehiculo(vehiculo_id):
    conn = None
    cursor = None
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM vehiculos WHERE id = %s FOR UPDATE", (vehiculo_id,))
        if not cursor.fetchone():
            conn.rollback()
            flash('No se encontró el vehículo.', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('vehiculos.lista_vehiculos'))
        cursor.execute(
            "SELECT COUNT(*) FROM ordenes_trabajo WHERE vehiculo_id = %s",
            (vehiculo_id,)
        )
        if cursor.fetchone()[0]:
            conn.rollback()
            flash('No se puede eliminar este vehículo porque tiene órdenes registradas.', 'error')
        else:
            cursor.execute("DELETE FROM vehiculos WHERE id = %s RETURNING id", (vehiculo_id,))
            if cursor.fetchone():
                conn.commit()
                flash('Vehículo eliminado correctamente.', 'success')
            else:
                conn.rollback()
                flash('No se encontró el vehículo.', 'error')
        cursor.close()
        conn.close()
    except Exception as e:
        if conn:
            conn.rollback()
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        return f"Error al eliminar el vehículo: {e}", 500
    return redirect(url_for('vehiculos.lista_vehiculos'))


@vehiculos_bp.route('/buscar-chapa')
def buscar_vehiculo_por_chapa():
    termino = request.args.get('q', '').strip()
    if len(termino) < 2:
        return {'vehiculos': [], 'coincidencia_exacta': False}
    try:
        conn = obtener_conexion()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        normalizada = termino.replace(' ', '').replace('-', '')
        cursor.execute("""
            SELECT v.id, v.marca, v.modelo, v.chapa, v.anio, v.kilometraje,
                   string_agg(DISTINCT c.nombre || ' ' || c.apellido, ', ') AS clientes
            FROM vehiculos v
            LEFT JOIN vehiculo_clientes vc ON vc.vehiculo_id = v.id
            LEFT JOIN clientes c ON c.id = vc.cliente_id
            WHERE UPPER(REPLACE(REPLACE(v.chapa, ' ', ''), '-', '')) LIKE UPPER(%s)
            GROUP BY v.id
            ORDER BY
                UPPER(REPLACE(REPLACE(v.chapa, ' ', ''), '-', '')) =
                UPPER(REPLACE(REPLACE(%s, ' ', ''), '-', '')) DESC,
                v.chapa
            LIMIT 10
        """, (f"%{normalizada}%", normalizada))
        vehiculos = cursor.fetchall()
        coincidencia_exacta = any(
            v['chapa'].replace(' ', '').replace('-', '').upper() == normalizada.upper()
            for v in vehiculos
        )
        cursor.close()
        conn.close()
        return {'vehiculos': vehiculos, 'coincidencia_exacta': coincidencia_exacta}
    except Exception as e:
        return {'error': str(e), 'vehiculos': [], 'coincidencia_exacta': False}, 500
