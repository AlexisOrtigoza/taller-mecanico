from flask import Blueprint, render_template, request, redirect, url_for, abort, flash
from db import obtener_conexion

repuestos_bp = Blueprint('repuestos', __name__)

@repuestos_bp.route('', methods=['GET', 'POST'])
def gestionar_repuestos():
    busqueda = request.args.get('buscar', '').strip()
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        precio_unitario = request.form.get('precio_unitario')
        stock_actual = request.form.get('stock_actual')
        if not nombre or not precio_unitario or stock_actual is None:
            abort(400, 'Faltan datos obligatorios del repuesto')
        try:
            precio = float(precio_unitario)
            stock = int(stock_actual)
            if precio < 0 or stock < 0:
                abort(400, 'El precio y el stock no pueden ser negativos')
        except (TypeError, ValueError):
            abort(400, 'Precio o stock invalidos')
        try:
            conn = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO repuestos (nombre, precio_unitario, stock_actual) VALUES (%s, %s, %s)", (nombre, precio_unitario, stock_actual))
            conn.commit()
            cursor.close()
            conn.close()
            flash('Repuesto registrado correctamente.', 'success')
            return redirect(url_for('repuestos.gestionar_repuestos'))
        except Exception as e:
            conn = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("SELECT id, nombre, stock_actual, precio_unitario FROM repuestos ORDER BY id DESC;")
            repuestos = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template('repuestos.html', repuestos=repuestos, error=f"Error al guardar repuesto: {e}")
            
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        if busqueda:
            cursor.execute(
                "SELECT id, nombre, stock_actual, precio_unitario FROM repuestos "
                "WHERE nombre ILIKE %s ORDER BY id DESC",
                (f"%{busqueda}%",)
            )
        else:
            cursor.execute("SELECT id, nombre, stock_actual, precio_unitario FROM repuestos ORDER BY id DESC;")
        repuestos = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        repuestos = []
    return render_template('repuestos.html', repuestos=repuestos, busqueda=busqueda)
