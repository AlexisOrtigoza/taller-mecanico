import hmac
import os
import secrets

from flask import Flask, abort, request, session
from blueprints.main import main_bp
from blueprints.clientes import clientes_bp
from blueprints.vehiculos import vehiculos_bp
from blueprints.ordenes import ordenes_bp
from blueprints.repuestos import repuestos_bp
from db import permitir_vehiculos_sin_cliente

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or secrets.token_hex(32)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', '0') == '1'

try:
    permitir_vehiculos_sin_cliente()
except Exception as error:
    print(f"No se pudo ajustar la tabla vehiculos: {error}")


@app.before_request
def proteger_post_con_csrf():
    if request.method != 'POST':
        return None

    token_sesion = session.get('csrf_token')
    token_formulario = request.form.get('csrf_token')
    if not token_sesion or not token_formulario:
        abort(400, 'Token CSRF faltante')
    if not hmac.compare_digest(token_sesion, token_formulario):
        abort(400, 'Token CSRF invalido')


@app.context_processor
def agregar_token_csrf():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return {'csrf_token': session['csrf_token']}

# Registro de Blueprints con sus prefijos correspondientes
app.register_blueprint(main_bp)
app.register_blueprint(clientes_bp, url_prefix='/clientes')
app.register_blueprint(vehiculos_bp, url_prefix='/vehiculos')
app.register_blueprint(ordenes_bp, url_prefix='/ordenes')
app.register_blueprint(repuestos_bp, url_prefix='/repuestos')

if __name__ == '__main__':
    app.run(debug=True)
