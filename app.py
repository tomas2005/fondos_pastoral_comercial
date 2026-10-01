"""
Pastoral Ingeniería Comercial UC
Sistema de Metas de Recaudación
Backend: Flask + SQLite (persistente en Railway con volumen /data)
"""

import os
import sqlite3
from datetime import date, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "pastoral-comercial-2026-secret-key")

# En Railway: montar volumen en /data y setear DATA_DIR=/data
# En local:   usa la carpeta del proyecto
DATA_DIR = os.environ.get("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
DB_FILE  = os.path.join(DATA_DIR, "pastoral.db")

# ──────────────────────────────────────────────────────────────────────
# BASE DE DATOS SQLite
# ──────────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row   # resultados como dicts
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Crea las tablas y datos iniciales si no existen."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS usuarios (
                usuario       TEXT PRIMARY KEY,
                nombre        TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                rol           TEXT NOT NULL DEFAULT 'usuario',
                activo        INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS semanas (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo      TEXT NOT NULL,
                descripcion TEXT,
                meta        REAL NOT NULL DEFAULT 0,
                fecha_inicio TEXT,
                fecha_fin    TEXT,
                activa      INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS aportes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario     TEXT NOT NULL,
                semana_id   INTEGER NOT NULL,
                monto       REAL NOT NULL,
                descripcion TEXT,
                fecha       TEXT NOT NULL,
                FOREIGN KEY(usuario)   REFERENCES usuarios(usuario),
                FOREIGN KEY(semana_id) REFERENCES semanas(id)
            );
        """)

        # Admin por defecto (solo si no existe)
        exists = conn.execute(
            "SELECT 1 FROM usuarios WHERE usuario='admin'"
        ).fetchone()
        if not exists:
            today = date.today()
            monday = today - timedelta(days=today.weekday())
            sunday = monday + timedelta(days=6)

            conn.execute("""
                INSERT INTO usuarios VALUES (?,?,?,?,?)
            """, ("admin", "Administrador",
                  generate_password_hash("admin123"), "admin", 1))
            conn.execute("""
                INSERT INTO usuarios VALUES (?,?,?,?,?)
            """, ("juan", "Juan Pérez",
                  generate_password_hash("juan123"), "usuario", 1))
            conn.execute("""
                INSERT INTO usuarios VALUES (?,?,?,?,?)
            """, ("maria", "María García",
                  generate_password_hash("maria123"), "usuario", 1))

            conn.execute("""
                INSERT INTO semanas (titulo,descripcion,meta,fecha_inicio,fecha_fin,activa)
                VALUES (?,?,?,?,?,?)
            """, ("Semana 1 - Pastoral", "Primera semana de recaudación",
                  500000, monday.isoformat(), sunday.isoformat(), 1))

            conn.execute("""
                INSERT INTO aportes (usuario,semana_id,monto,descripcion,fecha)
                VALUES (?,?,?,?,?)
            """, ("juan", 1, 50000, "Donación inicial", today.isoformat()))
            conn.execute("""
                INSERT INTO aportes (usuario,semana_id,monto,descripcion,fecha)
                VALUES (?,?,?,?,?)
            """, ("maria", 1, 75000, "Aporte personal", today.isoformat()))

            conn.commit()


# ──────────────────────────────────────────────────────────────────────
# FUNCIONES DE DATOS
# ──────────────────────────────────────────────────────────────────────

def get_users():
    with get_db() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM usuarios").fetchall()]


def get_semanas():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM semanas ORDER BY id"
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["activa"] = bool(d["activa"])
            result.append(d)
        return result


def get_active_semana():
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM semanas WHERE activa=1 ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not row:
            row = conn.execute(
                "SELECT * FROM semanas ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if row:
            d = dict(row)
            d["activa"] = bool(d["activa"])
            return d
        return None


def get_aportes():
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM aportes ORDER BY id"
        ).fetchall()]


def get_ranking(semana_id=None):
    with get_db() as conn:
        if semana_id:
            rows = conn.execute("""
                SELECT u.usuario, u.nombre,
                       COALESCE(SUM(a.monto),0) AS total
                FROM   usuarios u
                LEFT JOIN aportes a
                       ON a.usuario=u.usuario AND a.semana_id=?
                WHERE  u.rol='usuario' AND u.activo=1
                GROUP  BY u.usuario
                ORDER  BY total DESC
            """, (semana_id,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT u.usuario, u.nombre,
                       COALESCE(SUM(a.monto),0) AS total
                FROM   usuarios u
                LEFT JOIN aportes a ON a.usuario=u.usuario
                WHERE  u.rol='usuario' AND u.activo=1
                GROUP  BY u.usuario
                ORDER  BY total DESC
            """).fetchall()

        ranking = []
        for i, r in enumerate(rows):
            d = dict(r)
            d["posicion"] = i + 1
            ranking.append(d)
        return ranking


def get_user_aportes(username, semana_id=None):
    with get_db() as conn:
        if semana_id:
            rows = conn.execute("""
                SELECT * FROM aportes
                WHERE usuario=? AND semana_id=?
                ORDER BY fecha DESC
            """, (username, semana_id)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM aportes
                WHERE usuario=?
                ORDER BY fecha DESC
            """, (username,)).fetchall()
        return [dict(r) for r in rows]


# ──────────────────────────────────────────────────────────────────────
# AUTENTICACIÓN
# ──────────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "usuario" not in session:
            flash("Debés iniciar sesión primero.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "usuario" not in session:
            return redirect(url_for("login"))
        if session.get("rol") != "admin":
            flash("Acceso restringido a administradores.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated


# ──────────────────────────────────────────────────────────────────────
# RUTAS - AUTH
# ──────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
def login():
    if "usuario" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("usuario", "").strip()
        password = request.form.get("password", "")

        with get_db() as conn:
            user = conn.execute(
                "SELECT * FROM usuarios WHERE usuario=?", (username,)
            ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            if not user["activo"]:
                flash("Tu cuenta está desactivada.", "danger")
                return redirect(url_for("login"))
            session["usuario"] = user["usuario"]
            session["nombre"]  = user["nombre"]
            session["rol"]     = user["rol"]
            return redirect(url_for("dashboard"))
        else:
            flash("Usuario o contraseña incorrectos.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ──────────────────────────────────────────────────────────────────────
# RUTAS - DASHBOARD
# ──────────────────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    semana = get_active_semana()
    semana_id = semana["id"] if semana else None
    ranking = get_ranking(semana_id)
    user_aportes = get_user_aportes(session["usuario"], semana_id)
    user_total = sum(a["monto"] for a in user_aportes)
    user_pos   = next((r["posicion"] for r in ranking
                       if r["usuario"] == session["usuario"]), None)
    meta = float(semana["meta"]) if semana else 0
    progreso        = min(user_total / meta * 100, 100) if meta else 0
    total_global    = sum(r["total"] for r in ranking)
    progreso_global = min(total_global / meta * 100, 100) if meta else 0

    return render_template(
        "dashboard.html",
        semana=semana, ranking=ranking,
        user_aportes=user_aportes, user_total=user_total,
        user_pos=user_pos, meta=meta,
        progreso=round(progreso, 1),
        total_global=total_global,
        progreso_global=round(progreso_global, 1),
    )


@app.route("/ranking")
@login_required
def ranking_page():
    semanas = get_semanas()
    semana_id_sel = request.args.get("semana_id")
    if semana_id_sel:
        try:
            semana_id_sel = int(semana_id_sel)
        except ValueError:
            semana_id_sel = None
    if semana_id_sel is None:
        active = get_active_semana()
        semana_id_sel = active["id"] if active else None

    semana_actual = next((s for s in semanas if s["id"] == semana_id_sel), None)
    ranking = get_ranking(semana_id_sel)
    meta = float(semana_actual["meta"]) if semana_actual else 0
    total_global = sum(r["total"] for r in ranking)

    return render_template(
        "ranking.html",
        ranking=ranking, semanas=semanas,
        semana_actual=semana_actual, semana_id_sel=semana_id_sel,
        meta=meta, total_global=total_global,
    )


@app.route("/mis-aportes")
@login_required
def mis_aportes():
    semanas = {s["id"]: s for s in get_semanas()}
    all_aportes = get_user_aportes(session["usuario"])
    totales = {}
    for a in all_aportes:
        sid = a["semana_id"]
        totales[sid] = totales.get(sid, 0) + a["monto"]
    return render_template(
        "mis_aportes.html",
        aportes=all_aportes, semanas=semanas, totales=totales,
    )


# ──────────────────────────────────────────────────────────────────────
# RUTAS - ADMIN
# ──────────────────────────────────────────────────────────────────────

@app.route("/admin")
@admin_required
def admin_panel():
    users = [u for u in get_users() if u["rol"] != "admin"]
    semanas = get_semanas()
    aportes = get_aportes()
    semana_activa = get_active_semana()
    ranking = get_ranking(semana_activa["id"] if semana_activa else None)
    total_recaudado = sum(r["total"] for r in ranking)
    return render_template(
        "admin.html",
        users=users, semanas=semanas, aportes=aportes,
        semana_activa=semana_activa, ranking=ranking,
        total_recaudado=total_recaudado,
    )


# ── Usuarios ──

@app.route("/admin/usuarios/crear", methods=["POST"])
@admin_required
def crear_usuario():
    username = request.form.get("usuario", "").strip().lower()
    nombre   = request.form.get("nombre", "").strip()
    password = request.form.get("password", "")
    rol      = request.form.get("rol", "usuario")

    if not username or not nombre or not password:
        flash("Todos los campos son obligatorios.", "danger")
        return redirect(url_for("admin_panel"))

    with get_db() as conn:
        exists = conn.execute(
            "SELECT 1 FROM usuarios WHERE usuario=?", (username,)
        ).fetchone()
        if exists:
            flash(f"El usuario '{username}' ya existe.", "danger")
            return redirect(url_for("admin_panel"))
        conn.execute(
            "INSERT INTO usuarios VALUES (?,?,?,?,?)",
            (username, nombre, generate_password_hash(password), rol, 1)
        )
        conn.commit()

    flash(f"Usuario '{nombre}' creado exitosamente.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/usuarios/toggle/<username>")
@admin_required
def toggle_usuario(username):
    with get_db() as conn:
        conn.execute(
            "UPDATE usuarios SET activo = 1 - activo WHERE usuario=?",
            (username,)
        )
        conn.commit()
    flash("Estado del usuario actualizado.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/usuarios/eliminar/<username>")
@admin_required
def eliminar_usuario(username):
    with get_db() as conn:
        conn.execute("DELETE FROM usuarios WHERE usuario=?", (username,))
        conn.commit()
    flash("Usuario eliminado.", "success")
    return redirect(url_for("admin_panel"))


# ── Semanas ──

@app.route("/admin/semanas/crear", methods=["POST"])
@admin_required
def crear_semana():
    titulo      = request.form.get("titulo", "").strip()
    descripcion = request.form.get("descripcion", "").strip()
    meta        = request.form.get("meta", "0")
    fecha_inicio= request.form.get("fecha_inicio", "")
    fecha_fin   = request.form.get("fecha_fin", "")
    activar     = request.form.get("activar") == "on"

    if not titulo or not meta:
        flash("Título y meta son obligatorios.", "danger")
        return redirect(url_for("admin_panel"))

    with get_db() as conn:
        if activar:
            conn.execute("UPDATE semanas SET activa=0")
        conn.execute("""
            INSERT INTO semanas (titulo,descripcion,meta,fecha_inicio,fecha_fin,activa)
            VALUES (?,?,?,?,?,?)
        """, (titulo, descripcion, float(meta.replace(",",".")),
              fecha_inicio, fecha_fin, int(activar)))
        conn.commit()

    flash(f"Semana '{titulo}' creada.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/semanas/activar/<int:semana_id>")
@admin_required
def activar_semana(semana_id):
    with get_db() as conn:
        conn.execute("UPDATE semanas SET activa=0")
        conn.execute("UPDATE semanas SET activa=1 WHERE id=?", (semana_id,))
        conn.commit()
    flash("Semana activada.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/semanas/eliminar/<int:semana_id>")
@admin_required
def eliminar_semana(semana_id):
    with get_db() as conn:
        conn.execute("DELETE FROM semanas WHERE id=?", (semana_id,))
        conn.commit()
    flash("Semana eliminada.", "success")
    return redirect(url_for("admin_panel"))


# ── Aportes ──

@app.route("/admin/aportes/registrar", methods=["POST"])
@admin_required
def registrar_aporte():
    usuario     = request.form.get("usuario", "").strip()
    semana_id   = request.form.get("semana_id", "")
    monto       = request.form.get("monto", "0")
    descripcion = request.form.get("descripcion", "").strip()
    fecha       = request.form.get("fecha") or date.today().isoformat()

    if not usuario or not semana_id or not monto:
        flash("Usuario, semana y monto son obligatorios.", "danger")
        return redirect(url_for("admin_panel"))

    with get_db() as conn:
        conn.execute("""
            INSERT INTO aportes (usuario,semana_id,monto,descripcion,fecha)
            VALUES (?,?,?,?,?)
        """, (usuario, int(semana_id),
              float(monto.replace(",",".")), descripcion, fecha))
        conn.commit()

    flash("Aporte registrado exitosamente.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/aportes/eliminar/<int:aporte_id>")
@admin_required
def eliminar_aporte(aporte_id):
    with get_db() as conn:
        conn.execute("DELETE FROM aportes WHERE id=?", (aporte_id,))
        conn.commit()
    flash("Aporte eliminado.", "success")
    return redirect(url_for("admin_panel"))


# ── API JSON ──

@app.route("/api/ranking")
@login_required
def api_ranking():
    semana_id = request.args.get("semana_id")
    if semana_id:
        try:
            semana_id = int(semana_id)
        except ValueError:
            semana_id = None
    return jsonify(get_ranking(semana_id))


# ──────────────────────────────────────────────────────────────────────
# INICIALIZACIÓN (corre siempre: python app.py Y gunicorn)
# ──────────────────────────────────────────────────────────────────────

init_db()

# ──────────────────────────────────────────────────────────────────────
# MAIN (solo cuando se corre directamente con python)
# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import socket
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        local_ip = "localhost"

    print("\n" + "="*60)
    print("  PASTORAL INGENIERIA COMERCIAL UC")
    print("="*60)
    print(f"  Red local: http://{local_ip}:5000")
    print(f"  Esta PC:   http://localhost:5000")
    print("  Admin: admin / admin123")
    print("="*60 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
