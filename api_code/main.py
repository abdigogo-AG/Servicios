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
from typing import Optional
from datetime import date
from fastapi.middleware.cors import CORSMiddleware

# ... (CONFIGURACIÓN IGUAL) ...
log = logging.getLogger("uvicorn")
POSTGRES_URL = os.environ.get("POSTGRES_URL")
db_connections = {}

# ... (MODELOS) ...

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
    
    # ¡NUEVO! Recibimos la tachuela
    latitud: Optional[float] = None
    longitud: Optional[float] = None

class DatosVerificacion(BaseModel):
    correo: EmailStr
    codigo: str

class LoginRequest(BaseModel):
    correo: EmailStr
    password: str

# ... (HELPERS IGUALES) ...

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

# ... (LIFESPAN Y APP IGUALES) ...

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("🚀 Iniciando API...")
    try:
        pg_conn = psycopg2.connect(POSTGRES_URL, cursor_factory=psycopg2.extras.DictCursor)
        db_connections["pg_conn"] = pg_conn
        log.info("✅ Postgres Conectado.")
    except Exception as e:
        log.error(f"❌ Error Postgres: {e}")
    yield
    if db_connections.get("pg_conn"):
        db_connections["pg_conn"].close()

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ... (ENDPOINTS) ...

@app.get("/")
def read_root():
    return {"mensaje": "API Funcionando"}

@app.post("/registro-cliente")
def registrar_cliente(datos: RegistroCliente):
    conn = db_connections.get("pg_conn")
    if conn is None: raise HTTPException(503, "Sin BD")

    try:
        with conn.cursor() as cursor:
            hashed_pass = encriptar_password(datos.password)
            codigo = generar_codigo_verificacion()

            cursor.execute(
                """
                INSERT INTO usuarios 
                (nombre, apellidos, correo_electronico, password_hash, telefono, fecha_nacimiento, activo, codigo_verificacion)
                VALUES (%s, %s, %s, %s, %s, %s, FALSE, %s)
                RETURNING id
                """,
                (datos.nombre, datos.apellidos, datos.correo_electronico, hashed_pass, datos.telefono, datos.fecha_nacimiento, codigo)
            )
            nuevo_id = cursor.fetchone()['id']

            # AQUÍ GUARDAMOS LA TACHUELA
            cursor.execute(
                """
                INSERT INTO detalles_cliente
                (usuario_id, calle, colonia, numero_exterior, numero_interior, codigo_postal, ciudad, referencias_domicilio, latitud, longitud)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    nuevo_id, 
                    datos.calle, 
                    datos.colonia, 
                    datos.numero_exterior, 
                    datos.numero_interior, 
                    datos.codigo_postal, 
                    datos.ciudad, 
                    datos.referencias,
                    datos.latitud, # <---
                    datos.longitud # <---
                )
            )
            conn.commit()
            
            print(f"\n=== 📧 SIMULACIÓN EMAIL: {datos.correo_electronico} | 🔑 CÓDIGO: {codigo} ===\n")
            return {"mensaje": "Registrado. Verifica tu código.", "correo": datos.correo_electronico}

    except psycopg2.IntegrityError:
        conn.rollback()
        raise HTTPException(400, "Correo ya registrado.")
    except Exception as e:
        conn.rollback()
        log.error(f"Error: {e}")
        raise HTTPException(500, f"Error interno: {str(e)}")

# ... (EL RESTO DE LOS ENDPOINTS SIGUE IGUAL: VERIFICAR Y LOGIN) ...
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
            else:
                raise HTTPException(400, "Código incorrecto.")
    except HTTPException as e: raise e
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, "Error interno.")

@app.post("/login")
def login(datos: LoginRequest):
    conn = db_connections.get("pg_conn")
    if conn is None: raise HTTPException(503, "Sin BD")
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, nombre, password_hash, activo FROM usuarios WHERE correo_electronico = %s", (datos.correo,))
            usuario = cursor.fetchone()
            if not usuario: raise HTTPException(401, "Credenciales incorrectas")
            if not usuario['activo']: raise HTTPException(403, "Tu cuenta no ha sido activada.")
            if not verificar_password(datos.password, usuario['password_hash']): raise HTTPException(401, "Credenciales incorrectas")
            return {"mensaje": "Login exitoso", "usuario": {"id": str(usuario['id']), "nombre": usuario['nombre']}}
    except HTTPException as e: raise e
    except Exception as e:
        log.error(f"Error Login: {e}")
        raise HTTPException(500, "Error interno")
    

    # ------------------------------------------------------------------------------------------------
