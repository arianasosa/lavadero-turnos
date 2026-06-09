from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_sesiones_lavadero'

ADMIN_PASSWORD = "admin123"

def init_db():
    conn = sqlite3.connect('turnos.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS turnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT,
            sucursal TEXT,
            servicios TEXT,
            tipo_vehiculo TEXT,
            fecha TEXT,
            hora TEXT,
            total INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS servicios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE,
            precio INTEGER
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM servicios")
    if cursor.fetchone()[0] == 0:
        servicios_iniciales = [
            ("Lavado Premium", 50000),
            ("Lavado con Maquina de espuma", 60000),
            ("Limpieza de Tapizados", 120000),
            ("Limpieza y pulido de ópticas", 50000),
            ("Lavado motor", 50000),
            ("Tratamiento acrílico y cerámico", 40000)
        ]
        cursor.executemany("INSERT INTO servicios (nombre, precio) VALUES (?, ?)", servicios_iniciales)
        
    conn.commit()
    conn.close()

HORARIOS_TOTALES = ["09:00am", "10:00am", "13:30pm", "16:30pm", "17:30pm", "18:30pm"]

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_servicios', methods=['GET'])
def get_servicios():
    conn = sqlite3.connect('turnos.db')
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, precio FROM servicios")
    lista = [{"nombre": row[0], "precio": row[1]} for row in cursor.fetchall()]
    conn.close()
    return jsonify(lista)

@app.route('/get_horarios', methods=['GET'])
def get_horarios():
    fecha = request.args.get('fecha')
    if not fecha:
        return jsonify([])
    
    conn = sqlite3.connect('turnos.db')
    cursor = conn.cursor()
    cursor.execute("SELECT hora FROM turnos WHERE fecha = ?", (fecha,))
    ocupados = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    disponibles = [h for h in HORARIOS_TOTALES if h not in ocupados]
    return jsonify(disponibles)

@app.route('/confirmar_turno', methods=['POST'])
def confirmar_turno():
    data = request.json
    conn = sqlite3.connect('turnos.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO turnos (cliente, sucursal, servicios, tipo_vehiculo, fecha, hora, total)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (data['cliente'], data['sucursal'], ", ".join(data['servicios']), data['tipo_vehiculo'], data['fecha'], data['hora'], data['total']))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

# ================= RUTA DEL PANEL DE ADMINISTRACIÓN =================

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['admin_logeado'] = True
            return redirect(url_for('admin_panel'))
        else:
            return render_template('admin_login.html', error="Contraseña incorrecta")
    
    if session.get('admin_logeado'):
        return redirect(url_for('admin_panel'))
    return render_template('admin_login.html', error=None)

@app.route('/admin/panel')
def admin_panel():
    if not session.get('admin_logeado'):
        return redirect(url_for('admin'))
        
    conn = sqlite3.connect('turnos.db')
    cursor = conn.cursor()
    
    # Traemos el ID de los turnos para poder eliminarlos despues
    cursor.execute("SELECT id, cliente, sucursal, servicios, tipo_vehiculo, fecha, hora, total FROM turnos ORDER BY fecha DESC, hora DESC")
    turnos = cursor.fetchall()
    
    cursor.execute("SELECT id, nombre, precio FROM servicios")
    servicios = cursor.fetchall()
    
    conn.close()
    return render_template('admin_panel.html', turnos=turnos, servicios=servicios)

@app.route('/admin/actualizar_precio', methods=['POST'])
def actualizar_precio():
    if not session.get('admin_logeado'):
        return jsonify({"status": "error"}), 403
        
    id_servicio = request.form.get('id')
    nuevo_precio = request.form.get('precio')
    
    conn = sqlite3.connect('turnos.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE servicios SET precio = ? WHERE id = ?", (nuevo_precio, id_servicio))
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin_panel'))

# ACCIÓN NUEVA: Eliminar un servicio del catalogo
@app.route('/admin/eliminar_servicio', methods=['POST'])
def eliminar_servicio():
    if not session.get('admin_logeado'):
        return jsonify({"status": "error"}), 403
        
    id_servicio = request.form.get('id')
    conn = sqlite3.connect('turnos.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM servicios WHERE id = ?", (id_servicio,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

# ACCIÓN NUEVA: Eliminar un turno de la agenda
@app.route('/admin/eliminar_turno', methods=['POST'])
def eliminar_turno():
    if not session.get('admin_logeado'):
        return jsonify({"status": "error"}), 403
        
    id_turno = request.form.get('id')
    conn = sqlite3.connect('turnos.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM turnos WHERE id = ?", (id_turno,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logeado', None)
    return redirect(url_for('admin'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)