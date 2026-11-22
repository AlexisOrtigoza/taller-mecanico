from flask import Blueprint, render_template, request, redirect, url_for, abort, flash
from db import obtener_conexion
from psycopg2.extras import RealDictCursor

ordenes_bp = Blueprint('ordenes', __name__)

@ordenes_bp.route('/nueva', methods=['GET', 'POST'])
def nueva_orden():
    if request.method == 'POST':
        vehiculo_id = request.form.get('vehiculo_id') or None
        cliente_id_registro = request.form.get('cliente_id') or None
        sintoma = request.form.get('sintoma')
        lista_repuestos = request.form.getlist('repuesto_id[]')
        lista_cantidades = request.form.getlist('cantidad[]')
        lista_precios = request.form.getlist('precio_unitario[]')

        if not sintoma or not sintoma.strip():
            abort(400, 'Debe indicar el sintoma')
        if len(lista_repuestos) != len(lista_cantidades) or len(lista_repuestos) != len(lista_precios):
            abort(400, 'Los datos de repuestos no son validos')
        if not lista_repuestos:
            abort(400, 'Debe agregar al menos un repuesto o servicio')

        kilometraje_formulario = request.form.get(
            'kilometraje_ingreso' if vehiculo_id else 'kilometraje'
        )
        try:
            kilometraje_ingreso = int(kilometraje_formulario)
        except (TypeError, ValueError):
            abort(400, 'Debe indicar el kilometraje actual del vehículo')
        if kilometraje_ingreso < 0:
            abort(400, 'El kilometraje no puede ser negativo')
        
        try:
            conn = obtener_conexion()
            cursor = conn.cursor()
            vehiculo_nuevo = False

            if not vehiculo_id:
                marca = request.form.get('marca', '').strip()
                modelo = request.form.get('modelo', '').strip()
                chapa = request.form.get('chapa', '').strip()
                anio = request.form.get('anio') or None
                if not marca or not modelo or not chapa:
                    conn.close()
                    abort(400, 'Debe indicar marca, modelo y chapa del vehiculo')

                cursor.execute("""
                    SELECT id FROM vehiculos
                    WHERE UPPER(REPLACE(REPLACE(chapa, ' ', ''), '-', '')) =
                          UPPER(REPLACE(REPLACE(%s, ' ', ''), '-', ''))
                    LIMIT 1
                """, (chapa,))
                existente = cursor.fetchone()
                if existente:
                    vehiculo_id = existente[0]
                else:
                    cursor.execute(
                        "INSERT INTO vehiculos (cliente_id, marca, modelo, anio, chapa, kilometraje) "
                        "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                        (cliente_id_registro, marca, modelo, anio, chapa, kilometraje_ingreso)
                    )
                    vehiculo_id = cursor.fetchone()[0]
                    vehiculo_nuevo = True

            if not vehiculo_nuevo:
                cursor.execute("SELECT kilometraje FROM vehiculos WHERE id = %s FOR UPDATE", (vehiculo_id,))
                lectura_anterior = cursor.fetchone()
                if not lectura_anterior:
                    conn.rollback()
                    cursor.close()
                    conn.close()
                    return "El vehículo seleccionado ya no existe", 400
                if lectura_anterior[0] is not None and kilometraje_ingreso < lectura_anterior[0]:
                    conn.rollback()
                    cursor.close()
                    conn.close()
                    return "El kilometraje nuevo no puede ser menor al último registrado", 400
                cursor.execute(
                    "UPDATE vehiculos SET kilometraje = %s WHERE id = %s",
                    (kilometraje_ingreso, vehiculo_id)
                )

            if cliente_id_registro:
                cursor.execute("""
                    INSERT INTO vehiculo_clientes (vehiculo_id, cliente_id)
                    VALUES (%s, %s)
                    ON CONFLICT (vehiculo_id, cliente_id) DO NOTHING
                """, (vehiculo_id, cliente_id_registro))

            query_ot = """
                INSERT INTO ordenes_trabajo
                    (vehiculo_id, sintoma, estado, kilometraje_ingreso)
                VALUES (%s, %s, 'Pendiente', %s)
                RETURNING id
            """
            cursor.execute(query_ot, (vehiculo_id, sintoma, kilometraje_ingreso))
            orden_id = cursor.fetchone()[0]
            
            costo_acumulado = 0
            for i in range(len(lista_repuestos)):
                repuesto_id = lista_repuestos[i]
                try:
                    cantidad = int(lista_cantidades[i])
                    precio_unitario = float(lista_precios[i])
                except (TypeError, ValueError):
                    abort(400, 'Cantidad o precio invalidos')
                if cantidad <= 0 or precio_unitario < 0:
                    abort(400, 'Cantidad o precio invalidos')

                cursor.execute("SELECT nombre, stock_actual FROM repuestos WHERE id = %s FOR UPDATE", (repuesto_id,))
                repuesto = cursor.fetchone()
                if not repuesto:
                    conn.rollback()
                    abort(400, 'El repuesto seleccionado ya no existe')
                es_servicio = 'servicio' in repuesto[0].lower() or 'mano de obra' in repuesto[0].lower()
                if not es_servicio and repuesto[1] < cantidad:
                    conn.rollback()
                    abort(400, f"Stock insuficiente para {repuesto[0]}: disponible {repuesto[1]}")

                subtotal = cantidad * precio_unitario
                costo_acumulado += subtotal
                cursor.execute("INSERT INTO detalle_orden (orden_id, repuesto_id, cantidad, precio_unitario) VALUES (%s, %s, %s, %s)", (orden_id, repuesto_id, cantidad, precio_unitario))
                if not es_servicio:
                    cursor.execute("UPDATE repuestos SET stock_actual = stock_actual - %s WHERE id = %s", (cantidad, repuesto_id))
            
            cursor.execute("UPDATE ordenes_trabajo SET costo_total = %s WHERE id = %s", (costo_acumulado, orden_id))
            conn.commit()
            cursor.close()
            conn.close()
            flash(f'Orden #{orden_id} creada correctamente.', 'success')
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            conn = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT v.id, v.marca, v.modelo, v.chapa,
                       COALESCE(
                           (SELECT string_agg(c.nombre || ' ' || c.apellido, ', ')
                            FROM vehiculo_clientes vc JOIN clientes c ON c.id = vc.cliente_id
                            WHERE vc.vehiculo_id = v.id),
                           'Sin cliente registrado'
                       )
                FROM vehiculos v
            """)
            vehiculos = cursor.fetchall()
            cursor.execute("SELECT id, nombre, stock_actual, precio_unitario FROM repuestos;")
            repuestos = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template(
                'nueva_orden.html',
                vehiculos=vehiculos,
                repuestos=repuestos,
                cliente_inicial=None,
                vehiculo_inicial=None,
                modo_busqueda_inicial='ci',
                chapa_inicial='',
                error=f"Error al registrar la orden: {e}"
            )
            
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT v.id, v.marca, v.modelo, v.chapa,
                   COALESCE(
                       (SELECT string_agg(c.nombre || ' ' || c.apellido, ', ')
                        FROM vehiculo_clientes vc JOIN clientes c ON c.id = vc.cliente_id
                        WHERE vc.vehiculo_id = v.id),
                       'Sin cliente registrado'
                   )
            FROM vehiculos v
            ORDER BY v.id DESC
        """)
        vehiculos = cursor.fetchall()
        cursor.execute("SELECT id, nombre, stock_actual, precio_unitario FROM repuestos ORDER BY nombre;")
        repuestos = cursor.fetchall()
        cliente_inicial = None
        vehiculo_inicial = None
        try:
            cliente_id_inicial = int(request.args.get('cliente_id', ''))
        except (TypeError, ValueError):
            cliente_id_inicial = None
        try:
            vehiculo_id_inicial = int(request.args.get('vehiculo_id', ''))
        except (TypeError, ValueError):
            vehiculo_id_inicial = None
        cursor_detalle = conn.cursor(cursor_factory=RealDictCursor)
        if cliente_id_inicial:
            cursor_detalle.execute(
                "SELECT id, cedula, nombre, apellido FROM clientes WHERE id = %s",
                (cliente_id_inicial,)
            )
            cliente_inicial = cursor_detalle.fetchone()
        if vehiculo_id_inicial:
            cursor_detalle.execute("""
                SELECT id, marca, modelo, chapa, kilometraje
                FROM vehiculos WHERE id = %s
            """, (vehiculo_id_inicial,))
            vehiculo_inicial = cursor_detalle.fetchone()
        cursor_detalle.close()
        cursor.close()
        conn.close()
    except Exception as e:
        vehiculos, repuestos = [], []
        cliente_inicial = None
        vehiculo_inicial = None
    return render_template(
        'nueva_orden.html',
        vehiculos=vehiculos,
        repuestos=repuestos,
        cliente_inicial=cliente_inicial,
        vehiculo_inicial=vehiculo_inicial,
        modo_busqueda_inicial=request.args.get('modo_busqueda', 'ci'),
        chapa_inicial=request.args.get('chapa', '')
    )


@ordenes_bp.route('/buscar-clientes')
def buscar_clientes():
    termino = request.args.get('q', '').strip()
    if len(termino) < 1:
        return {"clientes": []}
    try:
        conn = obtener_conexion()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, cedula, nombre, apellido, telefono
            FROM clientes
            WHERE cedula ILIKE %s OR nombre ILIKE %s OR apellido ILIKE %s
            ORDER BY apellido, nombre
            LIMIT 10
        """, (f"%{termino}%", f"%{termino}%", f"%{termino}%"))
        clientes = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"clientes": clientes}
    except Exception as e:
        return {"error": str(e), "clientes": []}, 500


@ordenes_bp.route('/buscar-vehiculos')
def buscar_vehiculos():
    termino = request.args.get('q', '').strip()
    if len(termino) < 1:
        return {"vehiculos": []}
    try:
        conn = obtener_conexion()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT v.id, v.marca, v.modelo, v.chapa, v.anio, v.kilometraje,
                   COALESCE(string_agg(DISTINCT c.nombre || ' ' || c.apellido, ', '), 'Sin cliente registrado') AS clientes
            FROM vehiculos v
            LEFT JOIN vehiculo_clientes vc ON vc.vehiculo_id = v.id
            LEFT JOIN clientes c ON c.id = vc.cliente_id
            WHERE v.chapa ILIKE %s OR v.marca ILIKE %s OR v.modelo ILIKE %s
            GROUP BY v.id
            ORDER BY v.id DESC
            LIMIT 10
        """, (f"%{termino}%", f"%{termino}%", f"%{termino}%"))
        vehiculos = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"vehiculos": vehiculos}
    except Exception as e:
        return {"error": str(e), "vehiculos": []}, 500


@ordenes_bp.route('/vehiculos-cliente/<int:cliente_id>')
def vehiculos_cliente(cliente_id):
    try:
        conn = obtener_conexion()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT v.id, v.marca, v.modelo, v.chapa, v.anio, v.kilometraje
            FROM vehiculos v
            JOIN vehiculo_clientes vc ON vc.vehiculo_id = v.id
            WHERE vc.cliente_id = %s
            ORDER BY v.id DESC
        """, (cliente_id,))
        vehiculos = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"vehiculos": vehiculos}
    except Exception as e:
        return {"error": str(e), "vehiculos": []}, 500

@ordenes_bp.route('/estado/<int:orden_id>', methods=['POST'])
def cambiar_estado_orden(orden_id):
    nuevo_estado = request.form.get('nuevo_estado')
    estados_validos = {'Pendiente', 'En Proceso', 'Finalizado'}
    if nuevo_estado not in estados_validos:
        abort(400, 'Estado invalido')
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT oculto FROM ordenes_trabajo WHERE id = %s", (orden_id,))
        orden = cursor.fetchone()
        if orden and orden[0]:
            cursor.close()
            conn.close()
            return "No se puede modificar una orden archivada", 403
        cursor.execute("UPDATE ordenes_trabajo SET estado = %s WHERE id = %s", (nuevo_estado, orden_id))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error al cambiar el estado: {e}")
    return redirect(url_for('main.dashboard'))

@ordenes_bp.route('/ocultar/<int:id>', methods=['POST'])
def ocultar_orden(id):
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT estado FROM ordenes_trabajo WHERE id = %s", (id,))
        orden = cursor.fetchone()
        if not orden or orden[0] != 'Finalizado':
            cursor.close()
            conn.close()
            return "Solo se pueden archivar órdenes finalizadas", 400
        cursor.execute("UPDATE ordenes_trabajo SET oculto = TRUE WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error al ocultar orden: {e}")
    return redirect(url_for('main.dashboard'))

@ordenes_bp.route('/detalle/<int:id>')
def obtener_detalle_orden(id):
    try:
        conn = obtener_conexion()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        query_cabecera = """
            SELECT o.*, v.marca, v.modelo, v.chapa, v.anio, v.kilometraje,
                   COALESCE(c.clientes, 'Sin cliente asociado') AS cliente_nombre,
                   '' AS cliente_apellido, c.telefonos AS cliente_tel
            FROM ordenes_trabajo o
            JOIN vehiculos v ON o.vehiculo_id = v.id
            LEFT JOIN LATERAL (
                SELECT string_agg(DISTINCT cl.nombre || ' ' || cl.apellido, ', ') AS clientes,
                       string_agg(DISTINCT cl.telefono, ', ') AS telefonos
                FROM vehiculo_clientes vc
                JOIN clientes cl ON cl.id = vc.cliente_id
                WHERE vc.vehiculo_id = v.id
            ) c ON TRUE
            WHERE o.id = %s
        """
        cursor.execute(query_cabecera, (id,))
        orden = cursor.fetchone()
        if not orden:
            return {"error": "Orden no encontrada"}, 404
        cursor.execute("SELECT d.*, r.nombre as repuesto_nombre FROM detalle_orden d JOIN repuestos r ON d.repuesto_id = r.id WHERE d.orden_id = %s", (id,))
        repuestos = cursor.fetchall()
        cursor.close()
        conn.close()
        if orden['fecha_ingreso']:
            orden['fecha_ingreso'] = orden['fecha_ingreso'].strftime('%d/%m/%Y %H:%M')
        return {"orden": orden, "repuestos": repuestos}
    except Exception as e:
        return {"error": str(e)}, 500


@ordenes_bp.route('/seguimiento/<int:id>')
def seguimiento_orden(id):
    try:
        conn = obtener_conexion()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT o.*, v.marca, v.modelo, v.chapa
            FROM ordenes_trabajo o
            JOIN vehiculos v ON o.vehiculo_id = v.id
            WHERE o.id = %s AND o.oculto = FALSE
        """, (id,))
        orden = cursor.fetchone()
        cursor.close()
        conn.close()
        if not orden:
            return render_template('seguimiento.html', orden=None), 404
        return render_template('seguimiento.html', orden=orden)
    except Exception as e:
        return render_template('seguimiento.html', orden=None, error=str(e)), 500
