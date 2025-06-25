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
from mysql.connector import errorcode
import logging
from flask import current_app
from datetime import datetime

logger = logging.getLogger(__name__)

def _get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=current_app.config['MYSQL_HOST'],
            user=current_app.config['MYSQL_USER'],
            password=current_app.config['MYSQL_PASSWORD'],
            database=current_app.config['MYSQL_DB'],
            port=current_app.config['MYSQL_PORT']
        )
        return conn
    except mysql.connector.Error as err:
        logger.error(f"Error al conectar con MySQL: {err}")
        return None
    except Exception as e:
        logger.error(f"Error general obteniendo conexión (¿Fuera de contexto Flask?): {e}")
        return None

# ===================================================================
# --- GESTIÓN DE INCIDENTES (CRUD) ---
# ===================================================================

def get_all_incidents(filters=None):
    conn = _get_db_connection()
    if not conn:
        return None, "Error de conexión a la base de datos", 500
    
    cursor = conn.cursor(dictionary=True)
    
    base_query = """
        SELECT hi.id_incidente, hi.id_usuario, hi.tipo, hi.descripcion, 
               ST_AsText(hi.coordenadas) as coordenadas_wkt, 
               hi.grado_confianza, hi.zona_afectada, zv.nombre_zona,
               hi.fecha_reporte, hi.fecha_verificacion, hi.estado_incidente
        FROM historial_incidentes hi
        LEFT JOIN zonas_vigiladas zv ON hi.zona_afectada = zv.id_zona
    """
    
    where_clauses = []
    params = []

    if filters:
        if filters.get('tipo'):
            where_clauses.append("hi.tipo = %s")
            params.append(filters['tipo'])
        if filters.get('zona_afectada'):
            where_clauses.append("hi.zona_afectada = %s")
            params.append(filters['zona_afectada'])
        if filters.get('estado_incidente'):
            where_clauses.append("hi.estado_incidente = %s")
            params.append(filters['estado_incidente'])
        if filters.get('fecha_desde'):
            where_clauses.append("DATE(hi.fecha_reporte) >= %s")
            params.append(filters['fecha_desde'])
        if filters.get('fecha_hasta'):
            where_clauses.append("DATE(hi.fecha_reporte) <= %s")
            params.append(filters['fecha_hasta'])

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)
    
    base_query += " ORDER BY hi.fecha_reporte DESC"

    try:
        cursor.execute(base_query, tuple(params))
        incidents = cursor.fetchall()
        for incident in incidents:
            if incident.get('fecha_reporte'):
                incident['fecha_reporte'] = incident['fecha_reporte'].isoformat()
            if incident.get('fecha_verificacion'):
                incident['fecha_verificacion'] = incident['fecha_verificacion'].isoformat()
            if incident.get('grado_confianza') is not None:
                incident['grado_confianza'] = float(incident['grado_confianza'])
        return incidents, None, 200
    except mysql.connector.Error as err:
        logger.error(f"Error al obtener incidentes: {err}")
        return None, f"Error de base de datos al obtener incidentes: {err}", 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def get_incident_by_id(incident_id):
    conn = _get_db_connection()
    if not conn:
        return None, "Error de conexión a la base de datos", 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT hi.id_incidente, hi.id_usuario, hi.tipo, hi.descripcion, 
                   ST_AsText(hi.coordenadas) as coordenadas_wkt, 
                   hi.grado_confianza, hi.zona_afectada, zv.nombre_zona,
                   hi.fecha_reporte, hi.fecha_verificacion, hi.estado_incidente
            FROM historial_incidentes hi
            LEFT JOIN zonas_vigiladas zv ON hi.zona_afectada = zv.id_zona
            WHERE hi.id_incidente = %s
        """, (incident_id,))
        incident = cursor.fetchone()
        if incident:
            if incident.get('fecha_reporte'):
                incident['fecha_reporte'] = incident['fecha_reporte'].isoformat()
            if incident.get('fecha_verificacion'):
                incident['fecha_verificacion'] = incident['fecha_verificacion'].isoformat()
            if incident.get('grado_confianza') is not None:
                incident['grado_confianza'] = float(incident['grado_confianza'])
            return incident, None, 200
        else:
            return None, "Incidente no encontrado", 404
    except mysql.connector.Error as err:
        logger.error(f"Error al obtener incidente {incident_id}: {err}")
        return None, f"Error de base de datos: {err}", 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


def add_incident(data):
    id_usuario = data.get('id_usuario')
    tipo = data.get('tipo')
    descripcion = data.get('descripcion')
    coordenadas_wkt = data.get('coordenadas') 
    grado_confianza_str = data.get('grado_confianza')
    zona_afectada_id = data.get('zona_afectada')
    estado_incidente = data.get('estado_incidente', 'Pendiente')

    if not all([id_usuario, tipo, descripcion, zona_afectada_id]):
        return None, "Usuario, Tipo, Descripción y Zona son requeridos", 400
    
    grado_confianza = None
    if grado_confianza_str is not None and grado_confianza_str.strip() != "":
        try:
            grado_confianza = float(grado_confianza_str)
            if not (0.0 <= grado_confianza <= 1.0):
                return None, "Grado de confianza debe estar entre 0.0 y 1.0", 400
        except ValueError:
            return None, "Grado de confianza inválido, debe ser un número.", 400

    conn = _get_db_connection()
    if not conn:
        return None, "Error de conexión a la base de datos", 500
        
    cursor = conn.cursor()
    
    fields = ["id_usuario", "tipo", "descripcion", "zona_afectada", "estado_incidente", "fecha_reporte"]
    params = [id_usuario, tipo, descripcion, zona_afectada_id, estado_incidente]
    
    fields.append("coordenadas")
    params.append(coordenadas_wkt if coordenadas_wkt and coordenadas_wkt.strip() else None)
    
    fields.append("grado_confianza")
    params.append(grado_confianza) 

    query = f"""
        INSERT INTO historial_incidentes ({", ".join(fields)}) 
        VALUES (%s, %s, %s, %s, %s, NOW(), ST_GeomFromText(%s), %s) 
    """ 
    query = """
        INSERT INTO historial_incidentes 
        (id_usuario, tipo, descripcion, zona_afectada, estado_incidente, fecha_reporte, coordenadas, grado_confianza) 
        VALUES (%s, %s, %s, %s, %s, NOW(), ST_GeomFromText(%s), %s)
    """

    final_params = [
        id_usuario, 
        tipo, 
        descripcion, 
        zona_afectada_id, 
        estado_incidente,
        coordenadas_wkt if coordenadas_wkt and coordenadas_wkt.strip() else None, 
        grado_confianza 
    ]

    try:
        logger.debug(f"Ejecutando query: {query} con params: {final_params}")
        cursor.execute(query, tuple(final_params))
        conn.commit()
        new_incident_id = cursor.lastrowid
        return {"message": "Incidente reportado con éxito", "id_incidente": new_incident_id}, None, 201
    except mysql.connector.Error as err:
        conn.rollback()
        logger.error(f"Error al reportar incidente: {err}")
        logger.error(f"Query: {cursor.statement}") 
        if err.errno == 1416: 
             return None, f"Error de formato en coordenadas (WKT inválido): {err}", 400
        if err.errno == errorcode.ER_NO_REFERENCED_ROW_2:
            return None, f"Error de referencia: ID de usuario o zona no válidos.", 400
        if err.errno == errorcode.ER_TRUNCATED_WRONG_VALUE_FOR_FIELD and 'grado_confianza' in err.msg:
             return None, f"Valor incorrecto para grado_confianza. Asegúrate que sea un número válido o NULL.", 400
        return None, f"Error de base de datos al reportar incidente: {err}", 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def update_incident_by_id(incident_id, data):
    tipo = data.get('tipo')
    descripcion = data.get('descripcion')
    coordenadas_wkt = data.get('coordenadas')
    grado_confianza_str = data.get('grado_confianza')
    zona_afectada_id = data.get('zona_afectada')
    estado_incidente = data.get('estado_incidente')
    
    grado_confianza = None
    if grado_confianza_str is not None and grado_confianza_str.strip() != "":
        try:
            grado_confianza = float(grado_confianza_str)
            if not (0.0 <= grado_confianza <= 1.0):
                return None, "Grado de confianza debe estar entre 0.0 y 1.0", 400
        except ValueError:
            return None, "Grado de confianza inválido.", 400

    conn = _get_db_connection()
    if not conn:
        return None, "Error de conexión a la base de datos", 500
        
    cursor = conn.cursor()
    fields_to_update_sql = []
    params = []

    if tipo is not None:
        fields_to_update_sql.append("tipo = %s")
        params.append(tipo)
    if descripcion is not None:
        fields_to_update_sql.append("descripcion = %s")
        params.append(descripcion)
    
    if coordenadas_wkt is not None: 
        fields_to_update_sql.append("coordenadas = ST_GeomFromText(%s)")
        params.append(coordenadas_wkt if coordenadas_wkt and coordenadas_wkt.strip() else None)

    if grado_confianza_str is not None: 
        fields_to_update_sql.append("grado_confianza = %s")
        params.append(grado_confianza) 

    if zona_afectada_id is not None:
        fields_to_update_sql.append("zona_afectada = %s")
        params.append(zona_afectada_id)
    if estado_incidente is not None:
        fields_to_update_sql.append("estado_incidente = %s")
        params.append(estado_incidente)
        if estado_incidente.lower() in ["verificado", "resuelto", "falso positivo"]:
            fields_to_update_sql.append("fecha_verificacion = NOW()")

    if not fields_to_update_sql:
        return {"message": "No hay campos para actualizar"}, None, 200
    
    query = f"UPDATE historial_incidentes SET {', '.join(fields_to_update_sql)} WHERE id_incidente = %s"
    params.append(incident_id)

    try:
        logger.debug(f"Ejecutando query: {query} con params: {params}")
        cursor.execute(query, tuple(params))
        conn.commit()
        if cursor.rowcount == 0:
            return None, "Incidente no encontrado o sin cambios", 404
        return {"message": "Incidente actualizado con éxito"}, None, 200
    except mysql.connector.Error as err:
        conn.rollback()
        logger.error(f"Error al actualizar incidente {incident_id}: {err}")
        logger.error(f"Query: {cursor.statement}") 
        if err.errno == 1416: 
             return None, f"Error de formato en coordenadas (WKT inválido): {err}", 400
        if err.errno == errorcode.ER_NO_REFERENCED_ROW_2:
            return None, f"Error de referencia: ID de zona no válido.", 400
        if err.errno == errorcode.ER_TRUNCATED_WRONG_VALUE_FOR_FIELD and 'grado_confianza' in err.msg:
             return None, f"Valor incorrecto para grado_confianza. Asegúrate que sea un número válido o NULL.", 400
        return None, f"Error de base de datos al actualizar incidente: {err}", 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def get_all_incidents(filters=None):
    conn = _get_db_connection()
    if not conn:
        return None, "Error de conexión a la base de datos", 500
    
    cursor = conn.cursor(dictionary=True)
    
    base_query = """
        SELECT hi.id_incidente, hi.id_usuario, hi.tipo, hi.descripcion, 
               ST_AsText(hi.coordenadas) as coordenadas_wkt, 
               hi.grado_confianza, hi.zona_afectada, zv.nombre_zona,
               hi.fecha_reporte, hi.fecha_verificacion, hi.estado_incidente
        FROM historial_incidentes hi
        LEFT JOIN zonas_vigiladas zv ON hi.zona_afectada = zv.id_zona
    """
    
    where_clauses = []
    params_query = [] 

    if filters:
        if filters.get('tipo'):
            where_clauses.append("hi.tipo = %s")
            params_query.append(filters['tipo'])
        if filters.get('zona_afectada'):
            where_clauses.append("hi.zona_afectada = %s")
            params_query.append(filters['zona_afectada'])
        if filters.get('estado_incidente'):
            where_clauses.append("hi.estado_incidente = %s")
            params_query.append(filters['estado_incidente'])
        if filters.get('fecha_desde'):
            where_clauses.append("DATE(hi.fecha_reporte) >= %s")
            params_query.append(filters['fecha_desde'])
        if filters.get('fecha_hasta'):
            where_clauses.append("DATE(hi.fecha_reporte) <= %s")
            params_query.append(filters['fecha_hasta'])

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)
    
    base_query += " ORDER BY hi.fecha_reporte DESC"

    try:
        cursor.execute(base_query, tuple(params_query))
        incidents = cursor.fetchall()
        for incident in incidents:
            if incident.get('fecha_reporte'):
                incident['fecha_reporte'] = incident['fecha_reporte'].isoformat()
            if incident.get('fecha_verificacion') and isinstance(incident.get('fecha_verificacion'), datetime):
                incident['fecha_verificacion'] = incident['fecha_verificacion'].isoformat()
            elif incident.get('fecha_verificacion') is None:
                pass
            else: 
                logger.warning(f"Tipo inesperado para fecha_verificacion: {type(incident.get('fecha_verificacion'))}")
                incident['fecha_verificacion'] = None


            if incident.get('grado_confianza') is not None:
                try:
                    incident['grado_confianza'] = float(incident['grado_confianza'])
                except ValueError:
                    logger.warning(f"No se pudo convertir grado_confianza a float: {incident.get('grado_confianza')}")
                    incident['grado_confianza'] = None  
        return incidents, None, 200
    except mysql.connector.Error as err:
        logger.error(f"Error al obtener incidentes: {err}")
        return None, f"Error de base de datos al obtener incidentes: {err}", 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def get_incident_by_id(incident_id):
    conn = _get_db_connection()
    if not conn:
        return None, "Error de conexión a la base de datos", 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT hi.id_incidente, hi.id_usuario, hi.tipo, hi.descripcion, 
                   ST_AsText(hi.coordenadas) as coordenadas_wkt, 
                   hi.grado_confianza, hi.zona_afectada, zv.nombre_zona,
                   hi.fecha_reporte, hi.fecha_verificacion, hi.estado_incidente
            FROM historial_incidentes hi
            LEFT JOIN zonas_vigiladas zv ON hi.zona_afectada = zv.id_zona
            WHERE hi.id_incidente = %s
        """, (incident_id,))
        incident = cursor.fetchone()
        if incident:
            if incident.get('fecha_reporte'):
                incident['fecha_reporte'] = incident['fecha_reporte'].isoformat()
            if incident.get('fecha_verificacion') and isinstance(incident.get('fecha_verificacion'), datetime):
                incident['fecha_verificacion'] = incident['fecha_verificacion'].isoformat()
            elif incident.get('fecha_verificacion') is None:
                pass
            else:
                logger.warning(f"Tipo inesperado para fecha_verificacion en get_incident_by_id: {type(incident.get('fecha_verificacion'))}")
                incident['fecha_verificacion'] = None


            if incident.get('grado_confianza') is not None:
                try:
                    incident['grado_confianza'] = float(incident['grado_confianza'])
                except ValueError:
                     incident['grado_confianza'] = None
            return incident, None, 200
        else:
            return None, "Incidente no encontrado", 404
    except mysql.connector.Error as err:
        logger.error(f"Error al obtener incidente {incident_id}: {err}")
        return None, f"Error de base de datos: {err}", 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()