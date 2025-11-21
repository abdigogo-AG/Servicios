import os
import logging
import random
import string
import psycopg2
import psycopg2.extras
import bcrypt
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime, timedelta # <--- ¡AQUÍ ESTABA EL ERROR DEL BLOQUEO!
from fastapi.middleware.cors import CORSMiddleware

# 1. CONFIGURACIÓN
log = logging.getLogger("uvicorn")
POSTGRES_URL = os.environ.get("POSTGRES_URL")
db_connections = {}

# 2. MODELOS DE DATOS
class RegistroCliente(BaseModel):
    nombre: str
    apellidos: str
    correo_electronico: EmailStr
    password: str
    telefono: str
    fecha_nacimiento: date
    calle: str
    colonia: str
    numero_exterior: str
    numero_interior: Optional[str] = None
    codigo_postal: str
    ciudad: str
    referencias: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None

class RegistroTrabajador(BaseModel):
    nombre: str
    apellidos: str
    correo_electronico: EmailStr
    password: str
    telefono: str
    fecha_nacimiento: date
    descripcion_bio: str
    anios_experiencia: int
    tarifa_hora: float
    oficios_ids: List[int]
    latitud: Optional[float] = None
    longitud: Optional[float] = None

class DatosVerificacion(BaseModel):
    correo: EmailStr
    codigo: str

class LoginRequest(BaseModel):
    correo: EmailStr
    password: str

class AccionAdmin(BaseModel):
    usuario_id: str
    accion: str # 'validar', 'bloquear', 'desbloquear', 'borrar'
    dias_bloqueo: Optional[int] = 0

# 3. HELPERS
def encriptar_password(password_plana: str) -> str:
    password_bytes = password_plana[:72].encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def generar_codigo_verificacion():
    return ''.join(random.choices(string.digits, k=6))

def verificar_password(password_plana: str, password_hash: str) -> bool:
    password_bytes = password_plana[:72].encode('utf-8')
    hash_bytes = password_hash.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hash_bytes)

# 4. LIFESPAN (CREACIÓN DE ADMIN CORRECTA)
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Iniciando API...")
    try:
        pg_conn = psycopg2.connect(POSTGRES_URL, cursor_factory=psycopg2.extras.DictCursor)
        db_connections["pg_conn"] = pg_conn
        
        # --- CREAR ADMIN AL INICIAR (ESTA VEZ BIEN) ---
        with pg_conn.cursor() as cur:
            # Encriptamos la contraseña CON EL MISMO ALGORITMO que el login
            pass_admin = encriptar_password("admin123")
            
            cur.execute("""
                INSERT INTO usuarios (
                    nombre, apellidos, correo_electronico, password_hash, telefono, 
                    es_admin, activo, fecha_nacimiento
                )
                VALUES (
                    'Super', 'Admin', 'admin@sistema.com', %s, '0000000000', 
                    TRUE, TRUE, '2000-01-01'
                )
                ON CONFLICT (correo_electronico) DO NOTHING
            """, (pass_admin,))
            
            pg_conn.commit()
            log.info("Admin asegurado: admin@sistema.com")
            
        log.info("Postgres Conectado.")

    except Exception as e:
        if 'pg_conn' in locals() and pg_conn: pg_conn.rollback()
        log.error(f"Error al iniciar Postgres: {e}")
    yield
    if db_connections.get("pg_conn"):
        db_connections["pg_conn"].close()

# 5. APP
app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# 6. ENDPOINTS

@app.get("/")
def read_root(): return {"mensaje": "API ISF Funcionando"}

@app.get("/categorias")
def obtener_categorias():
    conn = db_connections.get("pg_conn")
    if conn is None: raise HTTPException(503, "Sin BD")
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, nombre, icono_url FROM categorias_oficios")
            return [dict(cat) for cat in cursor.fetchall()]
    except Exception as e: raise HTTPException(500, "Error interno")

@app.post("/registro-cliente")
def registrar_cliente(datos: RegistroCliente):
    conn = db_connections.get("pg_conn")
    if conn is None: raise HTTPException(503, "Sin BD")
    try:
        with conn.cursor() as cursor:
            hashed_pass = encriptar_password(datos.password)
            codigo = generar_codigo_verificacion()
            cursor.execute("INSERT INTO usuarios (nombre, apellidos, correo_electronico, password_hash, telefono, fecha_nacimiento, activo, codigo_verificacion) VALUES (%s, %s, %s, %s, %s, %s, FALSE, %s) RETURNING id", 
                           (datos.nombre, datos.apellidos, datos.correo_electronico, hashed_pass, datos.telefono, datos.fecha_nacimiento, codigo))
            nuevo_id = cursor.fetchone()['id']
            cursor.execute("INSERT INTO detalles_cliente (usuario_id, calle, colonia, numero_exterior, numero_interior, codigo_postal, ciudad, referencias_domicilio, latitud, longitud) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                           (nuevo_id, datos.calle, datos.colonia, datos.numero_exterior, datos.numero_interior, datos.codigo_postal, datos.ciudad, datos.referencias, datos.latitud, datos.longitud))
            conn.commit()
            print(f"\n=== CLIENTE: {datos.correo_electronico} | LLAVE: {codigo} ===\n")
            return {"mensaje": "Cliente registrado.", "correo": datos.correo_electronico}
    except psycopg2.IntegrityError: conn.rollback(); raise HTTPException(400, "Correo ya registrado.")
    except Exception as e: conn.rollback(); raise HTTPException(500, f"Error: {str(e)}")

@app.post("/registro-trabajador")
def registrar_trabajador(datos: RegistroTrabajador):
    conn = db_connections.get("pg_conn")
    if conn is None: raise HTTPException(503, "Sin BD")
    try:
        with conn.cursor() as cursor:
            hashed_pass = encriptar_password(datos.password)
            codigo = generar_codigo_verificacion()
            cursor.execute("INSERT INTO usuarios (nombre, apellidos, correo_electronico, password_hash, telefono, fecha_nacimiento, activo, codigo_verificacion) VALUES (%s, %s, %s, %s, %s, %s, FALSE, %s) RETURNING id", 
                           (datos.nombre, datos.apellidos, datos.correo_electronico, hashed_pass, datos.telefono, datos.fecha_nacimiento, codigo))
            nuevo_id = cursor.fetchone()['id']
            cursor.execute("INSERT INTO detalles_trabajador (usuario_id, descripcion_bio, anios_experiencia, tarifa_hora_estimada, latitud, longitud) VALUES (%s, %s, %s, %s, %s, %s)", 
                           (nuevo_id, datos.descripcion_bio, datos.anios_experiencia, datos.tarifa_hora, datos.latitud, datos.longitud))
            if datos.oficios_ids:
                for oficio_id in datos.oficios_ids:
                    cursor.execute("INSERT INTO trabajador_oficios (usuario_id, categoria_id) VALUES (%s, %s)", (nuevo_id, oficio_id))
            conn.commit()
            print(f"\n=== TRABAJADOR: {datos.correo_electronico} | LLAVE: {codigo} ===\n")
            return {"mensaje": "Trabajador registrado.", "correo": datos.correo_electronico}
    except psycopg2.IntegrityError as e: conn.rollback(); raise HTTPException(400, "Error registro.")
    except Exception as e: conn.rollback(); raise HTTPException(500, f"Error interno: {str(e)}")

@app.post("/verificar-cuenta")
def verificar_cuenta(datos: DatosVerificacion):
    conn = db_connections.get("pg_conn")
    if conn is None: raise HTTPException(503, "Sin BD")
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, codigo_verificacion, activo FROM usuarios WHERE correo_electronico = %s", (datos.correo,))
            usuario = cursor.fetchone()
            if not usuario: raise HTTPException(404, "Usuario no encontrado.")
            if usuario['activo']: return {"mensaje": "Cuenta ya activa."}
            if usuario['codigo_verificacion'] == datos.codigo:
                cursor.execute("UPDATE usuarios SET activo = TRUE WHERE id = %s", (usuario['id'],))
                conn.commit()
                return {"mensaje": "¡Cuenta activada!"}
            else: raise HTTPException(400, "Código incorrecto.")
    except Exception as e: conn.rollback(); raise HTTPException(500, "Error interno.")

@app.post("/login")
def login(datos: LoginRequest):
    conn = db_connections.get("pg_conn")
    if conn is None: raise HTTPException(503, "Sin BD")
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, nombre, password_hash, activo, es_admin, bloqueado_hasta FROM usuarios WHERE correo_electronico = %s", (datos.correo,))
            usuario = cursor.fetchone()

            if not usuario: raise HTTPException(401, "Credenciales incorrectas")
            
            if not verificar_password(datos.password, usuario['password_hash']): 
                raise HTTPException(401, "Credenciales incorrectas")

            if not usuario['activo']: raise HTTPException(403, "Tu cuenta no ha sido activada.")
            
            # Validar Bloqueo
            if usuario['bloqueado_hasta']:
                if usuario['bloqueado_hasta'] > datetime.now(usuario['bloqueado_hasta'].tzinfo):
                    raise HTTPException(403, "Tu cuenta está bloqueada temporalmente.")

            return {
                "mensaje": "Login exitoso",
                "usuario": {
                    "id": str(usuario['id']),
                    "nombre": usuario['nombre'],
                    "es_admin": usuario['es_admin']
                }
            }
    except HTTPException as e: raise e
    except Exception as e:
        log.error(f"Error Login: {e}")
        raise HTTPException(500, "Error interno")

# --- ENDPOINTS ADMIN ---
@app.get("/admin/usuarios")
def admin_listar_usuarios():
    conn = db_connections.get("pg_conn")
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT u.id, u.nombre, u.apellidos, u.correo_electronico, u.activo, u.bloqueado_hasta,
                CASE WHEN dt.usuario_id IS NOT NULL THEN 'Trabajador' WHEN dc.usuario_id IS NOT NULL THEN 'Cliente' WHEN u.es_admin THEN 'Admin' ELSE 'Desconocido' END as rol,
                dt.validado_por_admin
                FROM usuarios u
                LEFT JOIN detalles_trabajador dt ON u.id = dt.usuario_id
                LEFT JOIN detalles_cliente dc ON u.id = dc.usuario_id
                ORDER BY u.fecha_registro DESC
            """)
            usuarios = cursor.fetchall()
            res = []
            for u in usuarios:
                d = dict(u)
                d['id'] = str(d['id'])
                # Convertir fecha a string para JSON
                if d['bloqueado_hasta']: d['bloqueado_hasta'] = str(d['bloqueado_hasta'])
                res.append(d)
            return res
    except Exception as e:
        log.error(f"Error admin: {e}")
        raise HTTPException(500, "Error listando")

@app.post("/admin/accion")
def admin_accion_usuario(datos: AccionAdmin):
    conn = db_connections.get("pg_conn")
    try:
        with conn.cursor() as cursor:
            if datos.accion == "validar":
                cursor.execute("UPDATE detalles_trabajador SET validado_por_admin = TRUE WHERE usuario_id = %s", (datos.usuario_id,))
            elif datos.accion == "bloquear":
                # Ahora sí tenemos datetime y timedelta importados
                dias = datos.dias_bloqueo if datos.dias_bloqueo else 36500
                fecha_fin = datetime.now() + timedelta(days=dias)
                cursor.execute("UPDATE usuarios SET bloqueado_hasta = %s WHERE id = %s", (fecha_fin, datos.usuario_id))
            elif datos.accion == "desbloquear":
                cursor.execute("UPDATE usuarios SET bloqueado_hasta = NULL WHERE id = %s", (datos.usuario_id,))
            elif datos.accion == "borrar":
                cursor.execute("DELETE FROM usuarios WHERE id = %s", (datos.usuario_id,))
            
            conn.commit()
            return {"mensaje": f"Acción '{datos.accion}' ejecutada."}
    except Exception as e:
        conn.rollback()
        log.error(f"Error accion: {e}")
        raise HTTPException(500, f"Error: {str(e)}")