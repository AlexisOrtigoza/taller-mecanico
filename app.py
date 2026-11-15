from flask import Flask, render_template, request, redirect, url_for
import psycopg2  # <-- ¡Esta línea es la que falta o no se está leyendo!

app = Flask(__name__)
# Configuración de tu base de datos
DB_HOST = "localhost"
DB_NAME = "taller-mecanico"
DB_USER = "postgres"
DB_PASS = "931223"  # Cambia esto por tu contraseña real de PostgreSQL
DB_PORT = "5432"

def obtener_conexion():
    conexion = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT
    )
    return conexion

@app.route('/')
def dashboard():
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Consulta SQL uniendo la orden de trabajo con el vehículo correspondiente
        query = """
            SELECT ot.id, v.marca || ' ' || v.modelo || ' (' || v.chapa || ')', ot.sintoma, ot.estado, ot.fecha_ingreso 
            FROM ordenes_trabajo ot
            JOIN vehiculos v ON ot.vehiculo_id = v.id
            ORDER BY ot.id DESC;
        """
        cursor.execute(query)
        ordenes = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Enviamos los datos a la plantilla HTML index.html
        return render_template('index.html', ordenes=ordenes)
        
    except Exception as e:
        return f"Error al cargar el dashboard: {e}"
    
@app.route('/clientes/nuevo', methods=['GET', 'POST'])
    
def nuevo_cliente():
    if request.method == 'POST':
        # Capturamos los datos enviados por el formulario HTML
        cedula = request.form.get('cedula')
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        celular = request.form.get('celular')
        
        # Datos opcionales (si vienen vacíos, asignamos None para que se guarden como NULL en la BD)
        direccion = request.form.get('direccion') or None
        ciudad = request.form.get('ciudad') or None
        barrio = request.form.get('barrio') or None
        fecha_nacimiento = request.form.get('fecha_nacimiento') or None
        
        # Doble validación de seguridad por si intentan enviar campos obligatorios vacíos
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
            
            # Si se guarda con éxito, redirigimos al dashboard principal
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            return render_template('nuevo_cliente.html', error=f"Error al registrar (¿Es posible que la cédula ya esté registrada?): {e}")
            
    # Si entran mediante GET, solo mostramos el formulario vacío
    return render_template('nuevo_cliente.html')

@app.route('/vehiculos/nuevo', methods=['GET', 'POST'])
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
            
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            # Si falla, volvemos a cargar la lista de clientes para que el formulario no se rompa
            conn = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("SELECT id, cedula, nombre, apellido FROM clientes ORDER BY nombre;")
            clientes = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template('nuevo_vehiculo.html', clientes=clientes, error=f"Error al registrar vehículo (¿La chapa ya está registrada?): {e}")
            
    # Si entramos por GET, cargamos los clientes para el selector desplegable
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
@app.route('/ordenes/nueva', methods=['GET', 'POST'])
def nueva_orden():
    if request.method == 'POST':
        vehiculo_id = request.form.get('vehiculo_id')
        sintoma = request.form.get('sintoma')
        
        # Capturamos las listas enviadas desde la tabla dinámica de HTML
        lista_repuestos = request.form.getlist('repuesto_id[]')
        lista_cantidades = request.form.getlist('cantidad[]')
        lista_precios = request.form.getlist('precio_unitario[]')
        
        try:
            conn = obtener_conexion()
            cursor = conn.cursor()
            
            # 1. Insertar la Orden de Trabajo principal (Cabecera)
            query_ot = """
                INSERT INTO ordenes_trabajo (vehiculo_id, sintoma, estado)
                VALUES (%s, %s, 'Pendiente')
                RETURNING id;
            """
            cursor.execute(query_ot, (vehiculo_id, sintoma))
            orden_id = cursor.fetchone()[0] # Obtenemos el ID de la orden recién creada
            
            # 2. Recorrer los repuestos de la planilla y guardarlos en el detalle
            costo_acumulado = 0
            for i in range(len(lista_repuestos)):
                repuesto_id = lista_repuestos[i]
                cantidad = int(lista_cantidades[i])
                precio_unitario = float(lista_precios[i])
                
                subtotal = cantidad * precio_unitario
                costo_acumulado += subtotal
                
                query_detalle = """
                    INSERT INTO detalle_orden (orden_id, repuesto_id, cantidad, precio_unitario)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(query_detalle, (orden_id, repuesto_id, cantidad, precio_unitario))
            
            # 3. Actualizar el costo total calculado en la orden de trabajo
            cursor.execute("UPDATE ordenes_trabajo SET costo_total = %s WHERE id = %s", (costo_acumulado, orden_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            # En caso de error, recargamos vehículos y repuestos para renderizar de nuevo
            conn = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("SELECT v.id, v.marca, v.modelo, v.chapa, c.nombre || ' ' || c.apellido FROM vehiculos v JOIN clientes c ON v.cliente_id = c.id;")
            vehiculos = cursor.fetchall()
            cursor.execute("SELECT id, nombre, stock_actual, precio_unitario FROM repuestos;")
            repuestos = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template('nueva_orden.html', vehiculos=vehiculos, repuestos=repuestos, error=f"Error al registrar la orden: {e}")
            
    # Si entramos por GET, cargamos tanto los vehículos como el inventario de repuestos
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT v.id, v.marca, v.modelo, v.chapa, c.nombre || ' ' || c.apellido 
            FROM vehiculos v
            JOIN clientes c ON v.cliente_id = c.id
            ORDER BY v.id DESC;
        """)
        vehiculos = cursor.fetchall()
        
        cursor.execute("SELECT id, nombre, stock_actual, precio_unitario FROM repuestos ORDER BY nombre;")
        repuestos = cursor.fetchall()
        
        cursor.close()
        conn.close()
    except Exception as e:
        vehiculos = []
        repuestos = []
        
    return render_template('nueva_orden.html', vehiculos=vehiculos, repuestos=repuestos)

@app.route('/repuestos', methods=['GET', 'POST'])
def gestionar_repuestos():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        precio_unitario = request.form.get('precio_unitario')
        stock_actual = request.form.get('stock_actual')
        
        try:
            conn = obtener_conexion()
            cursor = conn.cursor()
            
            query = """
                INSERT INTO repuestos (nombre, precio_unitario, stock_actual)
                VALUES (%s, %s, %s)
            """
            cursor.execute(query, (nombre, precio_unitario, stock_actual))
            conn.commit()
            
            cursor.close()
            conn.close()
            
            return redirect(url_for('gestionar_repuestos'))
            
        except Exception as e:
            # Si ocurre un error, recargamos la lista con el mensaje de error
            conn = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("SELECT id, nombre, stock_actual, precio_unitario FROM repuestos ORDER BY id DESC;")
            repuestos = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template('repuestos.html', repuestos=repuestos, error=f"Error al guardar repuesto: {e}")
            
    # Si entramos por GET, simplemente consultamos y mostramos todos los repuestos
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, stock_actual, precio_unitario FROM repuestos ORDER BY id DESC;")
        repuestos = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        repuestos = []
        
    return render_template('repuestos.html', repuestos=repuestos)

@app.route('/ordenes/estado/<int:orden_id>/<string:nuevo_estado>')
def cambiar_estado_orden(orden_id, nuevo_estado):
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        query = "UPDATE ordenes_trabajo SET estado = %s WHERE id = %s"
        cursor.execute(query, (nuevo_estado, orden_id))
        conn.commit()
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error al cambiar el estado: {e}")
        
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)