from flask import Flask
from blueprints.main import main_bp
from blueprints.clientes import clientes_bp
from blueprints.vehiculos import vehiculos_bp
from blueprints.ordenes import ordenes_bp
from blueprints.repuestos import repuestos_bp

app = Flask(__name__)

# Registro de Blueprints con sus prefijos correspondientes
app.register_blueprint(main_bp)
app.register_blueprint(clientes_bp, url_prefix='/clientes')
app.register_blueprint(vehiculos_bp, url_prefix='/vehiculos')
app.register_blueprint(ordenes_bp, url_prefix='/ordenes')
app.register_blueprint(repuestos_bp, url_prefix='/repuestos')

if __name__ == '__main__':
    app.run(debug=True)
