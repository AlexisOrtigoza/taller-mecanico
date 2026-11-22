from flask import Blueprint, render_template, request, redirect, url_for
from db import obtener_conexion
from psycopg2.extras import RealDictCursor

ordenes_bp = Blueprint('ordenes', __name__)

@ordenes_bp.route('/nueva', methods=['GET', 'POST'])
def nueva_orden():
    if request.method == 'POST':
        vehiculo_id = request.form.get('vehiculo_id')
        sintoma = request.form.get('sintoma')
        lista_repuestos = request.form.getlist('repuesto_id[]')
        lista_cantidades = request.form.getlist('cantidad[]')
        lista_precios = request.form.getlist('precio_unitario[]')
        
        try:
            conn = obtener_conexion()
            cursor = conn.cursor()
            query_ot = "INSERT INTO ordenes_trabajo (vehiculo_id, sintoma, estado) VALUES (%s, %s, 'Pendiente') RETURNING id;"
            cursor.execute(query_ot, (vehiculo_id, sintoma))
            orden_id = cursor.fetchone()[0]
            
            costo_acumulado = 0
            for i in range(len(lista_repuestos)):
                repuesto_id = lista_repuestos[i]
                cantidad = int(lista_cantidades[i])
                precio_unitario = float(lista_precios[i])
                subtotal = cantidad * precio_unitario
                costo_acumulado += subtotal
                cursor.execute("INSERT INTO detalle_orden (orden_id, repuesto_id, cantidad, precio_unitario) VALUES (%s, %s, %s, %s)", (orden_id, repuesto_id, cantidad, precio_unitario))
            
            cursor.execute("UPDATE ordenes_trabajo SET costo_total = %s WHERE id = %s", (costo_acumulado, orden_id))
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            conn = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("SELECT v.id, v.marca, v.modelo, v.chapa, c.nombre || ' ' || c.apellido FROM vehiculos v JOIN clientes c ON v.cliente_id = c.id;")
            vehiculos = cursor.fetchall()
            cursor.execute("SELECT id, nombre, stock_actual, precio_unitario FROM repuestos;")
            repuestos = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template('nueva_orden.html', vehiculos=vehiculos, repuestos=repuestos, error=f"Error al registrar la orden: {e}")
            
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT v.id, v.marca, v.modelo, v.chapa, c.nombre || ' ' || c.apellido FROM vehiculos v JOIN clientes c ON v.cliente_id = c.id ORDER BY v.id DESC;")
        vehiculos = cursor.fetchall()
        cursor.execute("SELECT id, nombre, stock_actual, precio_unitario FROM repuestos ORDER BY nombre;")
        repuestos = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        vehiculos, repuestos = [], []
    return render_template('nueva_orden.html', vehiculos=vehiculos, repuestos=repuestos)

@ordenes_bp.route('/estado/<int:orden_id>/<string:nuevo_estado>')
def cambiar_estado_orden(orden_id, nuevo_estado):
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
                   c.nombre as cliente_nombre, c.apellido as cliente_apellido, c.telefono as cliente_tel
            FROM ordenes_trabajo o
            JOIN vehiculos v ON o.vehiculo_id = v.id
            JOIN clientes c ON v.cliente_id = c.id
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
