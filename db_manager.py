#    ██╗   ██╗ █████╗ ███╗   ██╗ ██████╗ ██╗   ██╗ █████╗ ██████╗ ██████╗ 
#    ██║   ██║██╔══██╗████╗  ██║██╔════╝ ██║   ██║██╔══██╗██╔══██╗██╔══██╗
#    ██║   ██║███████║██╔██╗ ██║██║  ███╗██║   ██║███████║██████╔╝██║  ██║
#    ╚██╗ ██╔╝██╔══██║██║╚██╗██║██║   ██║██║   ██║██╔══██║██╔══██╗██║  ██║
#     ╚████╔╝ ██║  ██║██║ ╚████║╚██████╔╝╚██████╔╝██║  ██║██║  ██║██████╔╝
#      ╚═══╝  ╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ 
#
#                                  ██╗ █████╗ 
#                                  ██║██╔══██╗
#                                  ██║███████║
#                                  ██║██╔══██║
#                                  ██║██║  ██║
#                                  ╚═╝╚═╝  ╚═╝

import mysql.connector
from mysql.connector import errorcode, IntegrityError
import logging
from flask import current_app
from datetime import datetime
import os
import json
import werkzeug.utils
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import time


logger = logging.getLogger(__name__)

# ===================================================================
# --- Conexión y Utilidades de Base de Datos ---
# ===================================================================

def _get_db_connection():
    """
    Establece y devuelve una conexión a la base de datos MySQL.
    
    Intenta leer la configuración de la base de datos desde el contexto de la aplicación
    Flask actual. Si no hay un contexto de aplicación (por ejemplo, al ejecutar un script
    independiente), recurre a las variables de entorno como una alternativa segura.
    Registra un error grave si la conexión falla.
    
    :return: Un objeto de conexión de MySQL si tiene éxito, de lo contrario None.
    :rtype: Optional[mysql.connector.connection.MySQLConnection]
    """
    try:
        if current_app:
            db_config = {
                'host': current_app.config['MYSQL_HOST'],
                'user': current_app.config['MYSQL_USER'],
                'password': current_app.config['MYSQL_PASSWORD'],
                'database': current_app.config['MYSQL_DB'],
                'port': current_app.config['MYSQL_PORT'],
                'charset': 'utf8mb4',
                'collation': 'utf8mb4_unicode_ci'
            }
        else: 
            logger.warning("_get_db_connection: No hay contexto de aplicación Flask, usando os.getenv.")
            db_config = {
                'host': os.getenv('MYSQL_HOST', 'localhost'),
                'user': os.getenv('MYSQL_USER', 'root'),
                'password': os.getenv('MYSQL_PASSWORD', ''),
                'database': os.getenv('MYSQL_DB', 'vanguard'),
                'port': int(os.getenv('MYSQL_PORT', 3306)),
                'charset': 'utf8mb4',
                'collation': 'utf8mb4_unicode_ci'
            }
        
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        logger.error(f"Error fatal al conectar con MySQL ({db_config.get('host', 'N/A')}/{db_config.get('database', 'N/A')}): {err}")
        return None

def _format_datetime_for_json(row_dict: Dict) -> Dict:
    """
    Recorre un diccionario y convierte cualquier objeto `datetime` a su formato de cadena ISO 8601.
    
    Esto es crucial para asegurar que los datos que contienen fechas y horas puedan ser
    serializados correctamente a formato JSON sin causar errores.
    
    :param row_dict: El diccionario a procesar.
    :type row_dict: Dict
    :return: El diccionario con los valores de fecha y hora convertidos a cadenas.
    :rtype: Dict
    """
    if not row_dict:
        return {}
    for key, value in row_dict.items():
        if isinstance(value, datetime):
            row_dict[key] = value.isoformat()
    return row_dict

# ===================================================================
# --- Gestión de Usuarios (Personal Administrativo) ---
# ===================================================================

def create_user(user_data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
    """
    Registra un nuevo usuario administrativo en la base de datos.
    
    Toma un diccionario con los datos del usuario, lo inserta en la tabla `personal_administrativo`
    y devuelve la información básica del usuario creado. Maneja errores comunes como
    correos electrónicos duplicados (error de integridad).

    :param user_data: Diccionario con los datos del usuario a crear. Debe contener
                      'nombre_completo', 'apellidos', 'correo', 'numero_celular',
                      'hash_password' y 'rol'.
    :type user_data: Dict[str, Any]
    :return: Una tupla que contiene:
             - El diccionario con la información del usuario creado (o None si hay error).
             - Un mensaje de error (o None si tiene éxito).
             - Un código de estado HTTP (201, 409, 500).
    :rtype: Tuple[Optional[Dict[str, Any]], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn: return None, "Error de conexión con la base de datos.", 500
    cursor = conn.cursor()

    query = """
        INSERT INTO personal_administrativo 
        (nombre_completo, apellidos, correo, numero_celular, hash_password, rol, activo, fecha_creacion, fecha_modificacion)
        VALUES (%s, %s, %s, %s, %s, %s, TRUE, NOW(), NOW())
    """
    try:
        cursor.execute(query, (
            user_data['nombre_completo'], user_data['apellidos'], user_data['correo'],
            user_data['numero_celular'], user_data['hash_password'], user_data['rol']
        ))
        user_id = cursor.lastrowid
        conn.commit()
        
        created_user_info = {
            "id_usuario": user_id,
            "nombre_completo": user_data['nombre_completo'],
            "correo": user_data['correo'],
            "rol": user_data['rol']
        }
        return created_user_info, None, 201
    except IntegrityError as err:
        conn.rollback()
        if err.errno == errorcode.ER_DUP_ENTRY:
            logger.warning(f"Intento de registrar un correo duplicado: {user_data['correo']}")
            return None, "El correo electrónico ya está registrado.", 409
        logger.error(f"Error de integridad al crear usuario: {err}")
        return None, f"Error de base de datos (Integridad): {err.msg}", 500
    except mysql.connector.Error as err:
        conn.rollback()
        logger.error(f"Error de MySQL al crear usuario: {err}")
        return None, f"Error de base de datos: {err.msg}", 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def get_user_by_email(email: str) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
    """
    Obtiene los datos completos de un usuario a partir de su dirección de correo electrónico.
    
    Esta función es fundamental para el proceso de inicio de sesión, donde el usuario
    se identifica con su email para verificar la contraseña.

    :param email: El correo electrónico del usuario a buscar.
    :type email: str
    :return: Una tupla que contiene:
             - El diccionario con los datos del usuario (o None si no se encuentra).
             - Un mensaje de error (o None si tiene éxito).
             - Un código de estado HTTP (200, 404, 500).
    :rtype: Tuple[Optional[Dict[str, Any]], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn: return None, "Error de conexión DB", 500
    cursor = conn.cursor(dictionary=True)
    
    query = "SELECT * FROM personal_administrativo WHERE correo = %s"
    try:
        cursor.execute(query, (email,))
        user = cursor.fetchone()
        if user:
            return _format_datetime_for_json(user), None, 200
        else:
            return None, "Usuario no encontrado.", 404
    except mysql.connector.Error as err:
        logger.error(f"Error DB obteniendo usuario por email {email}: {err}")
        return None, f"Error DB: {err.msg}", 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def get_user_by_id(user_id: int) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
    """
    Obtiene los datos completos de un usuario a partir de su ID único.
    
    Esta función es crucial para integraciones como Flask-Login, que necesita
    cargar al usuario en la sesión a partir de su ID en cada solicitud.

    :param user_id: El ID del usuario a buscar.
    :type user_id: int
    :return: Una tupla que contiene:
             - El diccionario con los datos del usuario (o None si no se encuentra).
             - Un mensaje de error (o None si tiene éxito).
             - Un código de estado HTTP (200, 404, 500).
    :rtype: Tuple[Optional[Dict[str, Any]], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn: return None, "Error de conexión DB", 500
    cursor = conn.cursor(dictionary=True)

    query = "SELECT * FROM personal_administrativo WHERE id_usuario = %s"
    try:
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()
        if user:
            return _format_datetime_for_json(user), None, 200
        else:
            return None, "Usuario no encontrado.", 404
    except mysql.connector.Error as err:
        logger.error(f"Error DB obteniendo usuario por ID {user_id}: {err}")
        return None, f"Error DB: {err.msg}", 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


# ===================================================================
# --- Gestión de Personas Buscadas---
# ===================================================================

def update_user(user_id: int, data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
    """
    Actualiza los datos de un usuario existente en la base de datos.
    
    Construye dinámicamente una consulta SQL de actualización basada en los campos
    proporcionados en el diccionario de datos, asegurando que solo los campos
    permitidos sean modificados. Devuelve los datos actualizados del usuario.

    :param user_id: El ID del usuario a actualizar.
    :type user_id: int
    :param data: Un diccionario con los campos a actualizar.
    :type data: Dict[str, Any]
    :return: Una tupla que contiene:
             - El diccionario con los datos actualizados del usuario (o None si hay error).
             - Un mensaje de error (o None si tiene éxito).
             - Un código de estado HTTP (200, 400, 409, 500).
    :rtype: Tuple[Optional[Dict[str, Any]], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn:
        return None, "Error de conexión con la base de datos.", 500
    
    cursor = conn.cursor()
    
    allowed_fields = ['nombre_completo', 'apellidos', 'numero_celular', 'hash_password']
    
    updates_sql = []
    params = []
    
    for field in allowed_fields:
        if field in data and data[field] is not None:
            updates_sql.append(f"{field} = %s")
            params.append(data[field])

    if not updates_sql:
        return None, "No se proporcionaron campos válidos para actualizar.", 400
        
    query = f"UPDATE personal_administrativo SET {', '.join(updates_sql)}, fecha_modificacion = NOW() WHERE id_usuario = %s"
    params.append(user_id)
    
    try:
        cursor.execute(query, tuple(params))
        conn.commit()

        updated_user_data, err, code = get_user_by_id(user_id)
        if updated_user_data and 'hash_password' in updated_user_data:
            del updated_user_data['hash_password']

        return updated_user_data, err, code
        
    except IntegrityError as err:
        conn.rollback()

        if err.errno == errorcode.ER_DUP_ENTRY:
            return None, "El correo electrónico ya está en uso por otro usuario.", 409
        return None, f"Error de base de datos: {err.msg}", 500
    except mysql.connector.Error as err:
        conn.rollback()
        return None, f"Error de MySQL: {err.msg}", 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def registrar_nueva_persona(data: Dict[str, Any], imagen_filename: str) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
    """
    Registra una nueva persona de interés en el sistema.
    
    Asocia la persona al usuario que realiza el registro, y guarda el nombre
    del archivo de la imagen de referencia facial.

    :param data: Diccionario con datos de la persona (nombre, identificacion, etc.)
                 y el `registrado_por_usuario_id`.
    :type data: Dict[str, Any]
    :param imagen_filename: El nombre del archivo de la imagen de referencia.
    :type imagen_filename: str
    :return: Una tupla que contiene:
             - Un diccionario de confirmación con el ID de la persona (o None si hay error).
             - Un mensaje de error (o None si tiene éxito).
             - Un código de estado HTTP (201, 400, 409, 500).
    :rtype: Tuple[Optional[Dict[str, Any]], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn: return None, "Error de conexión DB", 500
    cursor = conn.cursor()

    query = """
        INSERT INTO personas_registradas
        (nombre, identificacion, estado_persona, motivo_busqueda, imagen_facial_ref_filename, registrado_por_usuario_id, fecha_registro, fecha_modificacion)
        VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
    """
    try:
        cursor.execute(query, (
            data.get('nombre'), data.get('identificacion'), data.get('estado_persona', 'No asignado'),
            data.get('motivo_busqueda'), imagen_filename, data.get('registrado_por_usuario_id')
        ))
        id_persona = cursor.lastrowid
        conn.commit()
        return {"id_persona": id_persona, "message": "Persona registrada exitosamente."}, None, 201
    except IntegrityError as err:
        conn.rollback()
        if err.errno == errorcode.ER_DUP_ENTRY:
            return None, "Error: Ya existe una persona con esa identificación o nombre de imagen.", 409
        if err.errno == errorcode.ER_NO_REFERENCED_ROW_2:
             return None, "Error de referencia: El usuario que registra no existe.", 400
        return None, f"Error DB (Integridad): {err.msg}", 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

def obtener_personas_registradas_por_usuario(user_id: int) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str], int]:
    """
    Obtiene la lista de todas las personas que han sido registradas por un usuario específico.
    
    Esta función es para que los usuarios puedan ver y gestionar únicamente los registros
    que ellos mismos han creado, garantizando la segregación de datos.

    :param user_id: El ID del usuario cuyos registros se quieren obtener.
    :type user_id: int
    :return: Una tupla que contiene:
             - Una lista de diccionarios, cada uno representando una persona (o None si hay error).
             - Un mensaje de error (o None si tiene éxito).
             - Un código de estado HTTP (200, 500).
    :rtype: Tuple[Optional[List[Dict[str, Any]]], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn: return None, "Error de conexión DB", 500
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT id_persona, nombre, identificacion, estado_persona, motivo_busqueda, 
               imagen_facial_ref_filename, fecha_registro, fecha_modificacion 
        FROM personas_registradas 
        WHERE registrado_por_usuario_id = %s 
        ORDER BY fecha_modificacion DESC
    """
    try:
        cursor.execute(query, (user_id,))
        personas = [_format_datetime_for_json(row) for row in cursor.fetchall()]
        return personas, None, 200
    except mysql.connector.Error as err:
        logger.error(f"Error DB obteniendo personas para usuario {user_id}: {err}")
        return None, f"Error DB: {err.msg}", 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()
        
def obtener_todas_personas_para_referencia() -> Tuple[Optional[List[Dict[str, Any]]], Optional[str], int]:
    """
    Obtiene TODAS las personas registradas que tienen una imagen de referencia facial.
    
    A diferencia de `obtener_personas_registradas_por_usuario`, esta función ignora quién
    registró a la persona. Es utilizada por el motor de reconocimiento facial, que necesita
    comparar una cara detectada contra toda la base de datos de referencias.

    :return: Una tupla que contiene:
             - Una lista de diccionarios de personas con imagen (o None si hay error).
             - Un mensaje de error (o None si tiene éxito).
             - Un código de estado HTTP (200, 500).
    :rtype: Tuple[Optional[List[Dict[str, Any]]], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn: return None, "Error de conexión DB", 500
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT id_persona, nombre, estado_persona, motivo_busqueda, 
               imagen_facial_ref_filename, registrado_por_usuario_id
        FROM personas_registradas
        WHERE imagen_facial_ref_filename IS NOT NULL
    """
    try:
        cursor.execute(query)
        personas = cursor.fetchall()
        return personas, None, 200
    except mysql.connector.Error as err:
        logger.error(f"Error DB obteniendo todas las referencias faciales: {err}")
        return None, f"Error DB: {err.msg}", 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

def check_persona_ownership(id_persona: int, user_id: int) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
    """
    Verifica si una persona específica fue registrada por un usuario determinado.
    
    Esta es una función de seguridad clave para la autorización. Se utiliza antes de
    permitir operaciones de actualización o eliminación para asegurar que un usuario
    solo pueda modificar sus propios registros.

    :param id_persona: El ID de la persona a verificar.
    :type id_persona: int
    :param user_id: El ID del usuario que se presume es el propietario.
    :type user_id: int
    :return: Una tupla que contiene:
             - El diccionario de la persona si el usuario es el propietario (o None en otro caso).
             - Un mensaje de error/denegación (o None si tiene éxito).
             - Un código de estado HTTP (200, 403, 404, 500).
    :rtype: Tuple[Optional[Dict[str, Any]], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn: return None, "Error de conexión DB", 500
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM personas_registradas WHERE id_persona = %s"
    try:
        cursor.execute(query, (id_persona,))
        persona = cursor.fetchone()
        if not persona:
            return None, "Persona no encontrada.", 404
        if persona.get('registrado_por_usuario_id') != user_id:
            logger.warning(f"Acceso denegado: Usuario {user_id} intentó acceder a persona {id_persona} propiedad de {persona.get('registrado_por_usuario_id')}")
            return None, "Acceso denegado. No eres el propietario de este registro.", 403
        
        return _format_datetime_for_json(persona), None, 200
    except mysql.connector.Error as err:
        logger.error(f"Error DB verificando propiedad de persona {id_persona}: {err}")
        return None, f"Error DB: {err.msg}", 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

def actualizar_persona_registrada(id_persona: int, data: Dict[str, Any], nueva_img_file, img_folder: str, persona_actual: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
    """
    Actualiza los datos de una persona registrada, incluyendo su imagen de referencia.
    
    Se asume que la propiedad del registro ya ha sido verificada. Si se proporciona
    una nueva imagen, esta función la guarda en el sistema de archivos y elimina la
    antigua para evitar archivos huérfanos.

    :param id_persona: El ID de la persona a actualizar.
    :param data: Diccionario con los nuevos datos.
    :param nueva_img_file: El objeto de archivo de la nueva imagen (o None).
    :param img_folder: La ruta a la carpeta donde se guardan las imágenes.
    :param persona_actual: Los datos actuales de la persona, para obtener el nombre de la imagen antigua.
    :return: Una tupla con los datos actualizados de la persona, un error y el código HTTP.
    :rtype: Tuple[Optional[Dict[str, Any]], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn: return None, "Error de conexión DB", 500
    cursor = conn.cursor()

    campos_actualizables = ['nombre', 'identificacion', 'estado_persona', 'motivo_busqueda']
    updates_sql = []
    params = []
    
    for campo in campos_actualizables:
        if campo in data:
            updates_sql.append(f"{campo} = %s")
            params.append(data[campo])

    old_img_fname = persona_actual.get('imagen_facial_ref_filename')
    if nueva_img_file:
        ext = Path(nueva_img_file.filename).suffix
        new_fname = werkzeug.utils.secure_filename(f"{data.get('nombre', persona_actual.get('nombre'))}_{int(time.time())}{ext}")
        path = os.path.join(img_folder, new_fname)
        try:
            nueva_img_file.save(path)
            updates_sql.append("imagen_facial_ref_filename = %s")
            params.append(new_fname)
        except Exception as e:
            return None, f"Error al guardar nueva imagen: {e}", 500

    if not updates_sql:
        return {"message": "No se proporcionaron datos para actualizar."}, None, 200

    query = f"UPDATE personas_registradas SET {', '.join(updates_sql)}, fecha_modificacion = NOW() WHERE id_persona = %s"
    params.append(id_persona)

    try:
        cursor.execute(query, tuple(params))
        conn.commit()
        
        if nueva_img_file and old_img_fname:
            old_path = os.path.join(img_folder, old_img_fname)
            if os.path.exists(old_path):
                try: os.remove(old_path)
                except OSError as e: logger.warning(f"No se pudo borrar imagen antigua {old_path}: {e}")

        updated_persona, err, code = check_persona_ownership(id_persona, persona_actual['registrado_por_usuario_id'])
        return updated_persona, err, code
    except IntegrityError as err:
        conn.rollback()
        return None, "Error: La identificación o nombre de imagen ya existen para otra persona.", 409
    except mysql.connector.Error as err:
        conn.rollback()
        return None, f"Error DB: {err.msg}", 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

def eliminar_persona_registrada(id_persona: int, img_folder: str) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
    """
    Elimina permanentemente una persona registrada de la base de datos y su imagen asociada.
    
    Se asume que la propiedad del registro ya ha sido verificada. Primero elimina
    el registro de la base de datos y, si tiene éxito, borra el archivo de imagen
    correspondiente del sistema de archivos.

    :param id_persona: El ID de la persona a eliminar.
    :type id_persona: int
    :param img_folder: La ruta a la carpeta donde está la imagen.
    :type img_folder: str
    :return: Una tupla con un mensaje de confirmación, un error y el código HTTP.
    :rtype: Tuple[Optional[Dict[str, Any]], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn: return None, "Error de conexión DB", 500
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT imagen_facial_ref_filename FROM personas_registradas WHERE id_persona = %s", (id_persona,))
    persona_info = cursor.fetchone()
    
    query_delete = "DELETE FROM personas_registradas WHERE id_persona = %s"
    try:
        cursor.execute(query_delete, (id_persona,))
        if cursor.rowcount == 0:
            conn.rollback()
            return None, "Persona no encontrada para eliminar.", 404
        
        conn.commit()

        if persona_info and persona_info.get('imagen_facial_ref_filename'):
            path = os.path.join(img_folder, persona_info['imagen_facial_ref_filename'])
            if os.path.exists(path):
                try: 
                    os.remove(path)
                    return {"message": "Persona y archivo de imagen eliminados con éxito."}, None, 200
                except OSError as e:
                    return {"message": "Persona eliminada de DB, pero error al borrar archivo de imagen.", "error_fs": str(e)}, None, 200
        
        return {"message": "Persona eliminada con éxito (sin archivo de imagen asociado)."}, None, 200
    except mysql.connector.Error as err:
        conn.rollback()

        if err.errno == errorcode.ER_ROW_IS_REFERENCED_2:
            return None, "No se puede eliminar: esta persona está referenciada en otros registros (ej. como propietaria de un vehículo).", 409
        return None, f"Error DB: {err.msg}", 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

def obtener_nombres_personas_por_usuario(user_id: int) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str], int]:
    """
    Obtiene una lista simplificada (ID y nombre) de las personas registradas por un usuario.
    
    Esta función es una utilidad optimizada para poblar elementos de la interfaz de usuario,
    como menús desplegables (dropdowns), donde solo se necesita el nombre y el ID.

    :param user_id: El ID del usuario para filtrar las personas.
    :type user_id: int
    :return: Una tupla que contiene:
             - Una lista de diccionarios con 'id_persona' y 'nombre' (o None si hay error).
             - Un mensaje de error (o None si tiene éxito).
             - Un código de estado HTTP (200, 500).
    :rtype: Tuple[Optional[List[Dict[str, Any]]], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn: return None, "Error de conexión DB", 500
    cursor = conn.cursor(dictionary=True)
    query = "SELECT id_persona, nombre FROM personas_registradas WHERE registrado_por_usuario_id = %s ORDER BY nombre ASC"
    try:
        cursor.execute(query, (user_id,))
        return cursor.fetchall(), None, 200
    except mysql.connector.Error as err:
        return None, f"Error DB: {err.msg}", 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()


# ===================================================================
# --- Gestión de Vehículos Buscados ---
# ===================================================================

def registrar_nuevo_vehiculo(data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
    """
    Registra un nuevo vehículo en el sistema.
    
    Asocia el vehículo a un propietario (una persona ya registrada) y al usuario que
    está realizando el registro.

    :param data: Diccionario con los datos del vehículo, incluyendo `id_propietario` y
                 `registrado_por_usuario_id`.
    :type data: Dict[str, Any]
    :return: Una tupla con el vehículo recién creado, un error y el código HTTP.
    :rtype: Tuple[Optional[Dict[str, Any]], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn: return None, "Error de conexión DB", 500
    cursor = conn.cursor()
    
    query = """
        INSERT INTO vehiculos_registrados (placa, marca, modelo, color, id_propietario, notas, estado_vehiculo, motivo_busqueda_vehiculo, registrado_por_usuario_id, fecha_registro, fecha_modificacion)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
    """
    try:
        cursor.execute(query, (
            data.get('placa'), data.get('marca'), data.get('modelo'), data.get('color'),
            data.get('id_propietario'), data.get('notas'), data.get('estado_vehiculo', 'Autorizado'),
            data.get('motivo_busqueda_vehiculo'), data.get('registrado_por_usuario_id')
        ))
        id_vehiculo = cursor.lastrowid
        conn.commit()
        
        new_vehiculo, _, _ = obtener_vehiculo_por_id(id_vehiculo)
        return new_vehiculo, None, 201
    except IntegrityError as err:
        conn.rollback()
        if err.errno == errorcode.ER_DUP_ENTRY: return None, "La placa del vehículo ya existe.", 409
        if err.errno == errorcode.ER_NO_REFERENCED_ROW_2: return None, "Error de referencia: el propietario o el usuario que registra no existen.", 400
        return None, f"Error DB (Integridad): {err.msg}", 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

def obtener_vehiculos_registrados_por_usuario(user_id: int) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str], int]:
    """
    Obtiene la lista de todos los vehículos que han sido registrados por un usuario específico.
    
    Realiza un JOIN con la tabla de personas para incluir el nombre del propietario en los resultados.

    :param user_id: El ID del usuario cuyos registros de vehículos se quieren obtener.
    :type user_id: int
    :return: Una tupla con la lista de vehículos, un error y el código HTTP.
    :rtype: Tuple[Optional[List[Dict[str, Any]]], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn: return None, "Error de conexión DB", 500
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT v.*, p.nombre as nombre_propietario
        FROM vehiculos_registrados v
        LEFT JOIN personas_registradas p ON v.id_propietario = p.id_persona
        WHERE v.registrado_por_usuario_id = %s
        ORDER BY v.fecha_modificacion DESC
    """
    try:
        cursor.execute(query, (user_id,))
        vehiculos = [_format_datetime_for_json(row) for row in cursor.fetchall()]
        return vehiculos, None, 200
    except mysql.connector.Error as err:
        return None, f"Error DB: {err.msg}", 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()
        
def check_vehiculo_ownership(id_vehiculo: int, user_id: int) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
    """
    Verifica si un vehículo específico fue registrado por un usuario determinado.
    
    Función de seguridad para autorización, análoga a `check_persona_ownership`.

    :param id_vehiculo: El ID del vehículo a verificar.
    :type id_vehiculo: int
    :param user_id: El ID del usuario que se presume es el propietario del registro.
    :type user_id: int
    :return: Una tupla con los datos del vehículo si la propiedad es correcta, un error y el código HTTP.
    :rtype: Tuple[Optional[Dict[str, Any]], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn: return None, "Error de conexión DB", 500
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM vehiculos_registrados WHERE id_vehiculo = %s"
    try:
        cursor.execute(query, (id_vehiculo,))
        vehiculo = cursor.fetchone()
        if not vehiculo:
            return None, "Vehículo no encontrado.", 404
        if vehiculo.get('registrado_por_usuario_id') != user_id:
            logger.warning(f"Acceso denegado: Usuario {user_id} intentó acceder a vehículo {id_vehiculo} propiedad de {vehiculo.get('registrado_por_usuario_id')}")
            return None, "Acceso denegado. No eres el propietario de este registro.", 403
        
        return _format_datetime_for_json(vehiculo), None, 200
    except mysql.connector.Error as err:
        return None, f"Error DB: {err.msg}", 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

def obtener_vehiculo_por_id(id_vehiculo: int) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
    """
    Obtiene los detalles de un único vehículo por su ID, incluyendo el nombre de su propietario.

    :param id_vehiculo: El ID del vehículo a buscar.
    :type id_vehiculo: int
    :return: Una tupla con los datos del vehículo, un error y el código HTTP.
    :rtype: Tuple[Optional[Dict[str, Any]], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn: return None, "Error de conexión DB", 500
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT v.*, p.nombre as nombre_propietario
        FROM vehiculos_registrados v
        LEFT JOIN personas_registradas p ON v.id_propietario = p.id_persona
        WHERE v.id_vehiculo = %s
    """
    try:
        cursor.execute(query, (id_vehiculo,))
        vehiculo = cursor.fetchone()
        return (_format_datetime_for_json(vehiculo) if vehiculo else None), None, (200 if vehiculo else 404)
    except mysql.connector.Error as err:
        return None, f"Error DB: {err.msg}", 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()
        
def obtener_info_vehiculo_por_placa(placa: str) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
    """
    Busca un vehículo por su número de placa y devuelve su información detallada.
    
    Esta función es crucial para el motor de detección de placas, ya que permite
    correlacionar una placa detectada con un registro existente y obtener
    información clave como el estado del vehículo, el estado del propietario y
    quién lo registró para enviar notificaciones.

    :param placa: El texto de la placa a buscar.
    :type placa: str
    :return: Una tupla con la información del vehículo, un error y el código HTTP.
    :rtype: Tuple[Optional[Dict[str, Any]], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn: return None, "Error de conexión DB", 500
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT v.*, p.nombre as nombre_propietario, p.estado_persona as estado_propietario
        FROM vehiculos_registrados v
        LEFT JOIN personas_registradas p ON v.id_propietario = p.id_persona
        WHERE v.placa = %s
    """
    try:
        cursor.execute(query, (placa,))
        vehiculo = cursor.fetchone()
        return vehiculo, None, (200 if vehiculo else 404)
    except mysql.connector.Error as err:
        logger.error(f"Error DB obteniendo info de vehículo por placa {placa}: {err}")
        return None, f"Error DB: {err.msg}", 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

def actualizar_vehiculo_registrado(id_vehiculo: int, data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
    """
    Actualiza los datos de un vehículo registrado.
    
    Se asume que la propiedad del registro ya ha sido verificada.

    :param id_vehiculo: El ID del vehículo a actualizar.
    :type id_vehiculo: int
    :param data: Un diccionario con los campos del vehículo a actualizar.
    :type data: Dict[str, Any]
    :return: Una tupla con los datos actualizados del vehículo, un error y el código HTTP.
    :rtype: Tuple[Optional[Dict[str, Any]], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn: return None, "Error de conexión DB", 500
    cursor = conn.cursor()

    campos_actualizables = ['placa', 'marca', 'modelo', 'color', 'id_propietario', 'notas', 'estado_vehiculo', 'motivo_busqueda_vehiculo']
    updates_sql = [f"{campo} = %s" for campo in campos_actualizables if campo in data]
    params = [data[campo] for campo in campos_actualizables if campo in data]
    
    if not updates_sql: return {"message": "No se proporcionaron datos para actualizar."}, None, 200

    query = f"UPDATE vehiculos_registrados SET {', '.join(updates_sql)}, fecha_modificacion = NOW() WHERE id_vehiculo = %s"
    params.append(id_vehiculo)

    try:
        cursor.execute(query, tuple(params))
        conn.commit()
        updated_vehiculo, _, _ = obtener_vehiculo_por_id(id_vehiculo)
        return updated_vehiculo, None, 200
    except IntegrityError as err:
        conn.rollback()
        if err.errno == errorcode.ER_DUP_ENTRY: return None, "La placa ya existe.", 409
        if err.errno == errorcode.ER_NO_REFERENCED_ROW_2: return None, "El propietario especificado no existe.", 400
        return None, f"Error DB (Integridad): {err.msg}", 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

def eliminar_vehiculo_registrado(id_vehiculo: int) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
    """
    Elimina permanentemente un vehículo registrado de la base de datos.
    
    Se asume que la propiedad ya ha sido verificada. Antes de eliminar, desvincula
    el vehículo de cualquier registro de `placas_detectadas` para evitar errores
    de clave foránea.

    :param id_vehiculo: El ID del vehículo a eliminar.
    :type id_vehiculo: int
    :return: Una tupla con un mensaje de confirmación, un error y el código HTTP.
    :rtype: Tuple[Optional[Dict[str, Any]], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn: return None, "Error de conexión DB", 500
    cursor = conn.cursor()
    
    try:
        # Desasociar de detecciones pasadas para evitar error de clave foránea
        cursor.execute("UPDATE placas_detectadas SET id_vehiculo_registrado_asociado = NULL WHERE id_vehiculo_registrado_asociado = %s", (id_vehiculo,))
        
        # Eliminar el vehículo
        cursor.execute("DELETE FROM vehiculos_registrados WHERE id_vehiculo = %s", (id_vehiculo,))
        if cursor.rowcount == 0:
            conn.rollback()
            return None, "Vehículo no encontrado para eliminar.", 404
        
        conn.commit()
        return {"message": "Vehículo eliminado con éxito."}, None, 200
    except mysql.connector.Error as err:
        conn.rollback()
        return None, f"Error DB: {err.msg}", 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

# ===================================================================
# --- Gestión de Zonas, Incidentes y Alertas  ---
# ===================================================================

def add_zone(data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
    """
    Añade una nueva zona de vigilancia a la base de datos.
    
    Las zonas se definen por un nombre, una descripción y opcionalmente por
    datos geoespaciales (un polígono que delimita el área y un punto central).
    Cada zona está asociada al usuario que la creó.

    :param data: Diccionario con los datos de la zona, incluyendo `nombre_zona`,
                 `creada_por_usuario_id` y coordenadas opcionales.
    :type data: Dict[str, Any]
    :return: Una tupla con los datos de la zona creada, un error y el código HTTP.
    :rtype: Tuple[Optional[Dict[str, Any]], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn:
        return None, "Error de conexión con la base de datos.", 500
    cursor = conn.cursor()

    nombre_zona = data.get('nombre_zona')
    descripcion = data.get('descripcion')
    coordenadas_poligono = data.get('coordenadas_poligono')
    coordenadas_centro = data.get('coordenadas_centro')
    creada_por_usuario_id = data.get('creada_por_usuario_id')

    if not nombre_zona:
        return None, "El nombre de la zona es obligatorio.", 400
    if not creada_por_usuario_id:
        return None, "No se puede registrar una zona sin un usuario creador.", 400

    query = """
        INSERT INTO zonas_vigiladas 
        (nombre_zona, descripcion, coordenadas_poligono, coordenadas_centro, creada_por_usuario_id, fecha_creacion, fecha_modificacion)
        VALUES (%s, %s, ST_PolygonFromText(%s), ST_PointFromText(%s), %s, NOW(), NOW())
    """
    params = (
        nombre_zona,
        descripcion,
        coordenadas_poligono if coordenadas_poligono else None,
        coordenadas_centro if coordenadas_centro else None,
        creada_por_usuario_id
    )

    try:
        cursor.execute(query, params)
        id_zona = cursor.lastrowid
        conn.commit()

        new_zone_data = {
            "id_zona": id_zona,
            "nombre_zona": nombre_zona,
            "descripcion": descripcion,
            "message": "Zona creada exitosamente."
        }
        return new_zone_data, None, 201
        
    except IntegrityError as err:
        conn.rollback()
        if err.errno == errorcode.ER_DUP_ENTRY:
            logger.warning(f"Intento de crear zona con nombre duplicado: {nombre_zona}")
            return None, "Ya existe una zona con ese nombre.", 409
        logger.error(f"Error de integridad al crear zona: {err}")
        return None, f"Error de base de datos (Integridad): {err.msg}", 500
        
    except mysql.connector.Error as err:
        conn.rollback()
        if err.errno == 1416:
             logger.error(f"Error de formato de geometría al crear zona: {err}")
             return None, "El formato de las coordenadas (POLYGON o POINT) es inválido.", 400
        logger.error(f"Error de MySQL al crear zona: {err}")
        return None, f"Error de base de datos: {err.msg}", 500
        
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

            
def get_all_zones() -> Tuple[Optional[List[Dict[str, Any]]], Optional[str], int]:
    """
    Obtiene una lista simplificada de todas las zonas de vigilancia disponibles.
    
    Esta función es una utilidad para poblar elementos de la interfaz de usuario,
    como filtros de búsqueda o menús desplegables.

    :return: Una tupla con la lista de zonas, un error y el código HTTP.
    :rtype: Tuple[Optional[List[Dict[str, Any]]], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn:
        return None, "Error de conexión con la base de datos.", 500
    cursor = conn.cursor(dictionary=True)
    
    query = "SELECT id_zona, nombre_zona, descripcion FROM zonas_vigiladas ORDER BY nombre_zona ASC"
    
    try:
        cursor.execute(query)
        zonas = cursor.fetchall()
        return zonas, None, 200
    except mysql.connector.Error as err:
        logger.error(f"Error en DB al obtener todas las zonas: {err}")
        return None, f"Error de base de datos: {err.msg}", 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


def get_incidents_for_user(user_id: int, filters: Optional[Dict[str, Any]] = None) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str], int]:
    """
    Obtiene los incidentes relevantes para un usuario específico, con opción de filtrado.
    
    Un incidente es relevante para un usuario si este lo reportó o si es
    destinatario de la alerta asociada a dicho incidente. Permite filtrar
    los resultados por zona, tipo y estado del incidente.

    :param user_id: El ID del usuario para el cual obtener los incidentes.
    :type user_id: int
    :param filters: Un diccionario opcional con filtros a aplicar.
    :type filters: Optional[Dict[str, Any]]
    :return: Una tupla con la lista de incidentes, un error y el código HTTP.
    :rtype: Tuple[Optional[List[Dict[str, Any]]], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn:
        return None, "Error de conexión con la base de datos.", 500
    cursor = conn.cursor(dictionary=True)

    query_base = """
        SELECT i.*, z.nombre_zona
        FROM historial_incidentes i
        LEFT JOIN zonas_vigiladas z ON i.id_zona_afectada = z.id_zona
    """
    
    where_clauses = [
        "(i.id_usuario_reporta = %s OR ad.id_usuario_destinatario = %s)"
    ]
    params = [user_id, user_id]
    
    query_join = """
        LEFT JOIN alertas a ON i.id_incidente = a.id_incidente
        LEFT JOIN alertas_destinatarios ad ON a.id_alerta = ad.id_alerta
    """

    if filters:
        if filters.get('id_zona_afectada'):
            where_clauses.append("i.id_zona_afectada = %s")
            params.append(filters['id_zona_afectada'])
        if filters.get('tipo_incidente'):
            where_clauses.append("i.tipo_incidente LIKE %s")
            params.append(f"%{filters['tipo_incidente']}%")
        if filters.get('estado_incidente'):
            where_clauses.append("i.estado_incidente = %s")
            params.append(filters['estado_incidente'])

    query = f"{query_base} {query_join} WHERE {' AND '.join(where_clauses)} GROUP BY i.id_incidente ORDER BY i.fecha_reporte DESC"

    try:
        cursor.execute(query, tuple(params))
        incidents = [_format_datetime_for_json(row) for row in cursor.fetchall()]
        return incidents, None, 200
    except mysql.connector.Error as err:
        logger.error(f"Error en DB obteniendo incidentes para el usuario {user_id}: {err}")
        return None, f"Error de base de datos: {err.msg}", 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def registrar_incidente_y_alerta(
    tipo_incidente_str: str, descripcion_incidente: str, nivel_alerta_str: str,
    observaciones_alerta_json: Dict[str, Any], id_zona_afectada: Optional[int] = None,
    id_usuario_reporta: Optional[int] = None, grado_confianza: Optional[float] = None,
    fecha_incidente_dt: Optional[datetime] = None, media_source_path_incidente: Optional[str] = None,
    media_type: Optional[str] = None
) -> Tuple[Optional[int], Optional[int], Optional[str], int]:
    """
    Registra un incidente y su alerta correspondiente en una única transacción.
    
    Este enfoque garantiza la consistencia de los datos: o se crean ambos registros
    (incidente y alerta) o no se crea ninguno.

    :param tipo_incidente_str: Tipo de incidente (ej. "Persona Sospechosa").
    :param descripcion_incidente: Descripción detallada del incidente.
    :param nivel_alerta_str: Nivel de la alerta ("BAJA", "MEDIA", "ALTA", "CRITICA").
    :param observaciones_alerta_json: JSON con detalles adicionales de la alerta.
    :param id_zona_afectada: ID opcional de la zona donde ocurrió.
    :param id_usuario_reporta: ID opcional del usuario que reporta.
    :param grado_confianza: Confianza de la detección (si aplica).
    :param fecha_incidente_dt: Fecha y hora exactas del incidente.
    :param media_source_path_incidente: Ruta al archivo de evidencia.
    :param media_type: Tipo de archivo de evidencia ('image', 'video', 'audio').
    :return: Tupla con (id_incidente, id_alerta, error, código_http).
    :rtype: Tuple[Optional[int], Optional[int], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn: return None, None, "Error de conexión DB", 500
    cursor = conn.cursor()
    id_incidente, id_alerta = None, None
    
    try:
        query_inc = "INSERT INTO historial_incidentes (id_usuario_reporta, tipo_incidente, descripcion, grado_confianza_deteccion, id_zona_afectada, fecha_reporte, fecha_incidente, estado_incidente) VALUES (%s, %s, %s, %s, %s, NOW(), %s, 'Pendiente')"
        cursor.execute(query_inc, (id_usuario_reporta, tipo_incidente_str, descripcion_incidente, grado_confianza, id_zona_afectada, fecha_incidente_dt or datetime.now()))
        id_incidente = cursor.lastrowid
        
        query_alert = "INSERT INTO alertas (id_incidente, nivel_alerta, id_zona_impactada, observaciones, fecha_alerta) VALUES (%s, %s, %s, %s, NOW())"
        cursor.execute(query_alert, (id_incidente, nivel_alerta_str.upper(), id_zona_afectada, json.dumps(observaciones_alerta_json)))
        id_alerta = cursor.lastrowid
        
        conn.commit()
        return id_incidente, id_alerta, None, 201
    except mysql.connector.Error as err:
        conn.rollback()
        logger.error(f"Error DB registrando incidente/alerta: {err}")
        return id_incidente, id_alerta, f"Error DB: {err.msg}", 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

def registrar_destinatarios_alerta(id_alerta: int, id_usuarios_destinatarios: List[int]):
    """
    Asocia una alerta a una lista de usuarios destinatarios.
    
    Esta función puebla la tabla de unión `alertas_destinatarios`, que determina
    qué usuarios recibirán la notificación de una alerta específica.

    :param id_alerta: El ID de la alerta a la que se asociarán los usuarios.
    :type id_alerta: int
    :param id_usuarios_destinatarios: Lista de IDs de los usuarios que deben ser notificados.
    :type id_usuarios_destinatarios: List[int]
    """
    if not id_usuarios_destinatarios: return
    conn = _get_db_connection()
    if not conn: return
    cursor = conn.cursor()
    
    query = "INSERT IGNORE INTO alertas_destinatarios (id_alerta, id_usuario_destinatario) VALUES (%s, %s)"
    params = [(id_alerta, user_id) for user_id in id_usuarios_destinatarios]
    
    try:
        cursor.executemany(query, params)
        conn.commit()
        logger.info(f"Registrados {cursor.rowcount} destinatarios para alerta ID {id_alerta}.")
    except mysql.connector.Error as err:
        conn.rollback()
        logger.error(f"Error DB registrando destinatarios para alerta {id_alerta}: {err}")
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

def get_alerts_for_user(user_id: int, limit: int = 100, offset: int = 0) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str], int]:
    """
    Obtiene todas las alertas destinadas a un usuario específico, con paginación.
    
    Consulta la tabla de destinatarios para encontrar las alertas que le corresponden
    al usuario y las enriquece con información del incidente asociado.

    :param user_id: El ID del usuario para el que se buscan las alertas.
    :type user_id: int
    :param limit: El número máximo de alertas a devolver.
    :type limit: int
    :param offset: El número de alertas a omitir (para paginación).
    :type offset: int
    :return: Una tupla con la lista de alertas, un error y el código HTTP.
    :rtype: Tuple[Optional[List[Dict[str, Any]]], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn: return None, "Error de conexión DB", 500
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT a.*, i.tipo_incidente, i.descripcion as descripcion_incidente
        FROM alertas a
        JOIN alertas_destinatarios ad ON a.id_alerta = ad.id_alerta
        JOIN historial_incidentes i ON a.id_incidente = i.id_incidente
        WHERE ad.id_usuario_destinatario = %s
        ORDER BY a.fecha_alerta DESC
        LIMIT %s OFFSET %s
    """
    try:
        cursor.execute(query, (user_id, limit, offset))
        alerts = [_format_datetime_for_json(row) for row in cursor.fetchall()]
        for alert in alerts:
            if alert.get('observaciones') and isinstance(alert['observaciones'], str):
                try: alert['observaciones'] = json.loads(alert['observaciones'])
                except json.JSONDecodeError: alert['observaciones'] = {"raw": alert['observaciones']}
        return alerts, None, 200
    except mysql.connector.Error as err:
        return None, f"Error DB: {err.msg}", 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()
        
def get_alert_summary_stats_for_user(user_id: int) -> Tuple[Optional[Dict[str, int]], Optional[str], int]:
    """
    Calcula estadísticas resumidas de las alertas para un usuario específico.
    
    Cuenta el total de alertas y las desglosa por nivel de severidad (Crítica, Alta, etc.).
    Es ideal para mostrar en un panel de control (dashboard).

    :param user_id: El ID del usuario para el cual calcular las estadísticas.
    :type user_id: int
    :return: Una tupla con un diccionario de estadísticas, un error y el código HTTP.
    :rtype: Tuple[Optional[Dict[str, int]], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn: return None, "Error de conexión DB", 500
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT
            COUNT(a.id_alerta) as total_alerts,
            SUM(CASE WHEN a.nivel_alerta = 'CRITICA' THEN 1 ELSE 0 END) as critica,
            SUM(CASE WHEN a.nivel_alerta = 'ALTA' THEN 1 ELSE 0 END) as alta,
            SUM(CASE WHEN a.nivel_alerta = 'MEDIA' THEN 1 ELSE 0 END) as media,
            SUM(CASE WHEN a.nivel_alerta = 'BAJA' THEN 1 ELSE 0 END) as baja
        FROM alertas a
        JOIN alertas_destinatarios ad ON a.id_alerta = ad.id_alerta
        WHERE ad.id_usuario_destinatario = %s
    """
    try:
        cursor.execute(query, (user_id,))
        stats = cursor.fetchone()
        if stats:
            # Asegurarse de que los valores sean enteros
            for key, val in stats.items():
                stats[key] = int(val) if val is not None else 0
        return stats or {}, None, 200
    except mysql.connector.Error as err:
        return None, f"Error DB: {err.msg}", 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()


# ===================================================================
# --- Gestión de Detecciones  ---
# ===================================================================

def registrar_persona_detectada(
    nombre_persona: str, fecha_deteccion: datetime, id_persona_fk: Optional[int] = None,
    confianza_reconocimiento: Optional[float] = None, distancia_descriptor: Optional[float] = None,
    id_zona_deteccion: Optional[int] = None, coordenadas_deteccion_frame_json: Optional[str] = None,
    media_source_path: Optional[str] = None
):
    """
    Registra un evento de detección de un rostro en la base de datos.
    
    Esta función es llamada por el motor de reconocimiento facial cada vez que
    identifica un rostro. Guarda todos los metadatos relevantes de la detección.

    :param nombre_persona: El nombre asociado a la detección (ej. "Juan Perez" o "Desconocido").
    :param fecha_deteccion: Timestamp exacto de la detección.
    :param id_persona_fk: ID de la persona en `personas_registradas` si hubo coincidencia.
    :param confianza_reconocimiento: Puntuación de confianza del modelo.
    :param distancia_descriptor: Distancia métrica en el espacio de características faciales.
    :param id_zona_deteccion: ID de la zona donde ocurrió la detección.
    :param coordenadas_deteccion_frame_json: Coordenadas del rostro en el frame (JSON).
    :param media_source_path: Ruta al archivo de imagen o video de la detección.
    """
    conn = _get_db_connection()
    if not conn: return
    cursor = conn.cursor()
    query = """
        INSERT INTO rostros_detectados (id_persona_identificada, nombre_detectado, coordenadas_deteccion_frame, 
        confianza_reconocimiento, distancia_descriptor, fecha_deteccion, id_zona_deteccion, media_source_path)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
        cursor.execute(query, (id_persona_fk, nombre_persona, coordenadas_deteccion_frame_json, confianza_reconocimiento, distancia_descriptor, fecha_deteccion, id_zona_deteccion, media_source_path))
        conn.commit()
    except mysql.connector.Error as err:
        conn.rollback()
        logger.error(f"Error DB registrando persona detectada '{nombre_persona}': {err}")
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

def registrar_placa_detectada(
    texto_placa: str, fecha_deteccion: datetime, id_vehiculo_registrado_fk: Optional[int] = None,
    confianza_ocr: Optional[float] = None, id_zona_deteccion: Optional[int] = None,
    media_source_path: Optional[str] = None
):
    """
    Registra un evento de detección de una placa de vehículo en la base de datos.
    
    Llamada por el motor de reconocimiento de placas (ALPR/OCR) cada vez que
    lee una placa, guardando los metadatos de la detección.

    :param texto_placa: El texto de la placa leído por el OCR.
    :param fecha_deteccion: Timestamp exacto de la detección.
    :param id_vehiculo_registrado_fk: ID del vehículo si la placa coincide con un registro.
    :param confianza_ocr: Puntuación de confianza del OCR.
    :param id_zona_deteccion: ID de la zona donde ocurrió la detección.
    :param media_source_path: Ruta al archivo de imagen o video de la detección.
    """
    conn = _get_db_connection()
    if not conn: return
    cursor = conn.cursor()
    query = """
        INSERT INTO placas_detectadas (texto_placa, confianza_ocr, fecha_deteccion, 
        id_zona_deteccion, media_source_path, id_vehiculo_registrado_asociado)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    try:
        cursor.execute(query, (texto_placa, confianza_ocr, fecha_deteccion, id_zona_deteccion, media_source_path, id_vehiculo_registrado_fk))
        conn.commit()
    except mysql.connector.Error as err:
        conn.rollback()
        logger.error(f"Error DB registrando placa detectada '{texto_placa}': {err}")
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

def registrar_evento_audio(
    id_incidente: int, descripcion_corta: Optional[str] = None, transcripcion_completa: Optional[str] = None,
    respuesta_llm: Optional[str] = None, modelo_llm_usado: Optional[str] = None,
    media_source_path: Optional[str] = None, fecha_evento_dt: Optional[datetime] = None
) -> Tuple[Optional[int], Optional[str], int]:
    """
    Registra un evento de audio procesado y lo asocia a un incidente existente.
    
    Guarda la información extraída del audio, como transcripciones y el análisis
    realizado por un modelo de lenguaje grande (LLM).

    :param id_incidente: El ID del incidente al que se asocia este evento de audio.
    :param descripcion_corta: Resumen del evento.
    :param transcripcion_completa: Transcripción completa del audio.
    :param respuesta_llm: La respuesta o análisis del LLM.
    :param modelo_llm_usado: Nombre del modelo LLM utilizado.
    :param media_source_path: Ruta al archivo de audio.
    :param fecha_evento_dt: Timestamp del evento.
    :return: Tupla con (id_evento_audio, error, código_http).
    :rtype: Tuple[Optional[int], Optional[str], int]
    """
    conn = _get_db_connection()
    if not conn: return None, "Error de conexión DB", 500
    cursor = conn.cursor()
    query = "INSERT INTO eventos_audio (id_incidente, descripcion_corta, transcripcion_completa, respuesta_llm, modelo_llm_usado, fecha_evento, media_source_path) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    try:
        cursor.execute(query, (id_incidente, descripcion_corta, transcripcion_completa, respuesta_llm, modelo_llm_usado, fecha_evento_dt or datetime.now(), media_source_path))
        id_evento_audio = cursor.lastrowid
        conn.commit()
        return id_evento_audio, None, 201
    except mysql.connector.Error as err:
        conn.rollback()
        return None, f"Error DB: {err.msg}", 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()
