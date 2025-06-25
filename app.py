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
from flask import Flask, request, jsonify, render_template, send_from_directory, url_for, redirect, flash
import cv2
import dlib
import json
import logging
import numpy as np
import os
import re
import threading
import time
import torch
import werkzeug.utils
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, send_from_directory, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from pathlib import Path
from ultralytics import YOLO
from typing import Optional, List, Dict, Any, Tuple
from werkzeug.security import generate_password_hash, check_password_hash
import google.generativeai as genai
import db_manager
import email_sender

# ===================================================================
# --- CONFIGURACIÓN INICIAL DE LA APLICACIÓN Y LOGGING ---
# ===================================================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv('FLASK_SECRET_KEY', 'una-llave-secreta-muy-segura-y-dificil-de-adivinar-cambiame')
app.config['UPLOAD_FOLDER'] = 'Uploads'
app.config['OUTPUT_FOLDER'] = 'Outputs'
PERSONAS_IMG_REF_FOLDER_RELATIVE = os.path.join('Outputs', 'D_Rostros', 'imagenes_referencia')
app.config['PERSONAS_IMG_REF_FOLDER'] = os.path.join(app.root_path, PERSONAS_IMG_REF_FOLDER_RELATIVE)
app.config['FRAMES_OUTPUT_FOLDER'] = os.path.join(app.config['OUTPUT_FOLDER'], 'alert_frames')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'mp4', 'avi', 'mov', 'mp3', 'wav', 'ogg', 'm4a', 'flac'}
app.config['MAX_CONTENT_LENGTH'] = 300 * 1024 * 1024

app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'vanguard')
app.config['MYSQL_PORT'] = int(os.getenv('MYSQL_PORT', 3306))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        logger.info("Gemini API Key configurada correctamente.")
    except Exception as e:
        logger.error(f"Error configurando la API de Gemini con la clave proporcionada: {e}")
        genai = None
else:
    logger.warning("GEMINI_API_KEY no encontrada en el entorno. Los modelos de Gemini no funcionarán.")
    genai = None

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
os.makedirs(app.config['PERSONAS_IMG_REF_FOLDER'], exist_ok=True)
os.makedirs(app.config['FRAMES_OUTPUT_FOLDER'], exist_ok=True)

# ===================================================================
# --- GESTIÓN DE AUTENTICACIÓN Y SESIONES (FLASK-LOGIN) ---
# ===================================================================

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.session_protection = "strong"
login_manager.login_view = 'inicio_route'
login_manager.login_message = "Por favor, inicie sesión para acceder a esta página."
login_manager.login_message_category = "info"

@login_manager.unauthorized_handler
def unauthorized_callback():
    """
    Redirige a los usuarios no autenticados.
    Responde con JSON para rutas API y redirige a la página de inicio para otras rutas.
    """
    if request.path.startswith('/api/'):
        return jsonify({"error": "Acceso no autorizado. Se requiere autenticación."}), 401
    
    flash("Por favor, inicie sesión para acceder a esa página.", "warning")
    return redirect(url_for('inicio_route'))

class User(UserMixin):
    """
    Clase de Usuario que Flask-Login necesita para manejar las sesiones.
    Se mapea con los datos de la tabla `personal_administrativo`.
    """
    def __init__(self, id_usuario, correo, rol, nombre_completo, activo=True):
        self.id = id_usuario
        self.correo = correo
        self.rol = rol
        self.nombre_completo = nombre_completo
        self._is_active = activo 

    @property
    def is_active(self):
        """
        Propiedad de solo lectura que devuelve el estado de actividad del usuario.
        Flask-Login usará esto.
        """
        return self._is_active

@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    """
    Función que Flask-Login usa para recargar el objeto de usuario desde la sesión.
    Busca en la base de datos usando el ID de usuario.
    """
    user_data, err, _ = db_manager.get_user_by_id(int(user_id))
    if user_data and not err:
        return User(
            id_usuario=user_data['id_usuario'],
            correo=user_data['correo'],
            rol=user_data['rol'],
            nombre_completo=user_data['nombre_completo'],
            activo=user_data['activo']
        )
    return None

# ===================================================================
# --- CONSTANTES Y FUNCIONES DE UTILIDAD ---
# ===================================================================

KEYWORDS_EMERGENCIA_GEMINI_STRICT = [
    "emergencia confirmada", "ayuda inmediata", "situación crítica", "peligro inminente",
    "disparos confirmados", "explosión confirmada", "accidente grave confirmado"
]
KEYWORDS_EMERGENCIA_GEMINI = [
    "emergencia", "ayuda", "socorro", "policía", "ambulancia", "fuego", "bomberos",
    "disparo", "explosión", "accidente", "herido", "sangre", "asalto violento",
    "grito de terror", "llamada de auxilio"
]
KEYWORDS_SOSPECHOSO_GEMINI = [
    "sospechoso", "merodeando", "vigilando", "intruso", "acechando", "comportamiento errático",
    "discusión acalorada", "amenaza verbal", "vandalismo", "intento de robo", "actividad ilícita"
]

def allowed_file(filename: str, allowed_extensions_override: Optional[set] = None) -> bool:
    """Verifica si la extensión de un archivo está permitida."""
    ext_set = allowed_extensions_override if allowed_extensions_override else app.config['ALLOWED_EXTENSIONS']
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ext_set

def get_file_type(filename: str) -> Optional[str]:
    """Determina el tipo de archivo (imagen, video, audio) basado en su extensión."""
    ext = filename.rsplit('.', 1)[1].lower()
    if ext in ['png', 'jpg', 'jpeg']: return 'image'
    if ext in ['mp4', 'avi', 'mov']: return 'video'
    if ext in ['mp3', 'wav', 'ogg', 'm4a', 'flac']: return 'audio'
    return None

def save_alert_frame(frame_image_to_save: np.ndarray, base_filename: str, detection_type: str) -> Optional[str]:
    """Guarda un frame específico como imagen JPG para asociarlo a una alerta."""
    if frame_image_to_save is None or frame_image_to_save.size == 0:
        logger.warning(f"Intento de guardar frame vacío para {base_filename}, tipo {detection_type}.")
        return None
    try:
        os.makedirs(app.config['FRAMES_OUTPUT_FOLDER'], exist_ok=True)
        timestamp = int(time.time())
        safe_stem = werkzeug.utils.secure_filename(Path(base_filename).stem)
        filename = f"{safe_stem}_{detection_type}_alertframe_{timestamp}.jpg"
        save_path = os.path.join(app.config['FRAMES_OUTPUT_FOLDER'], filename)
        success = cv2.imwrite(save_path, frame_image_to_save.copy())
        if success:
            logger.info(f"Frame de alerta guardado en: {save_path}")
            return save_path
        else:
            logger.error(f"cv2.imwrite falló al guardar el frame de alerta: {save_path}")
            return None
    except Exception as e:
        logger.error(f"EXCEPCIÓN al guardar el frame de alerta para {base_filename}, tipo {detection_type}: {e}", exc_info=True)
        return None

# ===================================================================
# --- CLASE: DETECTOR DE PLACAS DE MATRÍCULA ---
# ===================================================================
class LicensePlateDetector:
    """
    Gestiona la detección de vehículos y el reconocimiento de placas de matrícula (LPR/ANPR).
    Utiliza YOLO para detectar vehículos y placas, y PaddleOCR para el reconocimiento de texto.
    """
    def __init__(self, vehicle_model_path="D_placas/Modelos/yolov10n.pt",
                 plate_model_path="D_placas/Modelos/placa.pt", ocr_lang='es', device='cpu',
                 frame_processing_interval=5):
        from paddleocr import PaddleOCR
        self.device = device
        self.frame_processing_interval = max(1, frame_processing_interval)
        self.model_vehiculos = None
        self.model_placas = None
        self.ocr = None
        try:
            base_dir = Path(__file__).resolve().parent
            vehicle_model_path_abs = base_dir / vehicle_model_path
            plate_model_path_abs = base_dir / plate_model_path
            if vehicle_model_path_abs.exists(): self.model_vehiculos = YOLO(str(vehicle_model_path_abs))
            else: logger.error(f"Modelo de vehículos no encontrado: {vehicle_model_path_abs}")
            if plate_model_path_abs.exists(): self.model_placas = YOLO(str(plate_model_path_abs))
            else: logger.error(f"Modelo de placas no encontrado: {plate_model_path_abs}")
        except Exception as e: logger.error(f"Error cargando modelos YOLO (placas): {e}")
        try:
            self.ocr = PaddleOCR(use_angle_cls=True, lang=ocr_lang, use_gpu=(self.device == 'cuda'), show_log=False)
        except ImportError:
             logger.error("PaddleOCR no está instalado.")
             self.ocr = None
        except Exception as e:
            logger.error(f"Error inicializando PaddleOCR: {e}")
            self.ocr = None
        self.detected_plates_data_session: Dict[str, Dict[str, Any]] = {}
        self.MIN_PLATE_LENGTH = 4
        self.MAX_PLATE_LENGTH = 10

    def is_ready(self) -> bool:
        """Verifica si todos los modelos (vehículos, placas, OCR) están cargados y listos."""
        return all([self.model_vehiculos, self.model_placas, self.ocr])

    def _extract_text_paddle(self, plate_img_bgr: np.ndarray) -> Tuple[Optional[str], float]:
        """Utiliza PaddleOCR para extraer texto de una imagen de placa recortada."""
        if not self.ocr: return None, 0.0
        try:
            img_for_ocr = plate_img_bgr.copy()
            result = self.ocr.ocr(img_for_ocr, cls=True)
            if not result or not result[0]: return None, 0.0
            
            all_texts, all_confidences = [], []
            def process_ocr_line(line_item):
                text_segment, confidence_segment = None, None
                if isinstance(line_item, list) and len(line_item) == 2 and \
                   isinstance(line_item[1], tuple) and len(line_item[1]) == 2:
                    text_segment, confidence_segment = line_item[1]
                elif isinstance(line_item, list) and len(line_item) > 0 and \
                     isinstance(line_item[0], list) and isinstance(line_item[0][0], list) and \
                     isinstance(line_item[0][1], tuple) and len(line_item[0][1]) == 2:
                     text_segment, confidence_segment = line_item[0][1]
                elif isinstance(line_item, tuple) and len(line_item) == 2 and isinstance(line_item[0], str):
                    text_segment, confidence_segment = line_item
                
                if text_segment is not None and confidence_segment is not None:
                    cleaned_segment = ''.join(char for char in text_segment if char.isalnum()).upper()
                    if cleaned_segment:
                        all_texts.append(cleaned_segment)
                        all_confidences.append(float(confidence_segment))

            for detection_block in result:
                if isinstance(detection_block, list):
                    for line_item in detection_block:
                        process_ocr_line(line_item)
                else:
                    process_ocr_line(detection_block)
            
            if not all_texts: return None, 0.0
            final_text = "".join(all_texts)
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
            return final_text, avg_confidence
        except Exception as e:
            logger.error(f"Error en OCR de placa (_extract_text_paddle): {e}", exc_info=True)
            return None, 0.0

    def _process_frame_for_plates(self, frame_bgr: np.ndarray, media_source_path: str, current_timestamp: datetime, id_zona: Optional[int] = None, media_type: Optional[str] = 'image') -> Tuple[List[Dict], Optional[str], float, Optional[Dict[str, Any]]]:
        """
        Lógica central para procesar un único frame:
        1. Detecta vehículos.
        2. En cada vehículo, detecta la placa.
        3. Recorta la placa y aplica OCR.
        4. Consulta la base de datos con el texto de la placa.
        5. Si el vehículo está marcado (Buscado, Robado), genera un incidente y una alerta.
        """
        if not self.is_ready(): return [], None, 0.0, None
        frame_to_process = frame_bgr.copy()
        detected_plates_in_frame_info: List[Dict] = []
        best_plate_text_this_frame: Optional[str] = None
        highest_confidence_this_frame: float = 0.0
        info_vehiculo_registrado_detectado: Optional[Dict[str, Any]] = None

        vehicle_results = self.model_vehiculos(frame_to_process, verbose=False, device=self.device)
        for res_v in vehicle_results:
            for box_v in res_v.boxes:
                if int(box_v.cls[0]) in [2, 3, 5, 7]:
                    x1_v, y1_v, x2_v, y2_v = map(int, box_v.xyxy[0])
                    vehicle_roi = frame_to_process[y1_v:y2_v, x1_v:x2_v]
                    if vehicle_roi.size == 0: continue

                    plate_results = self.model_placas(vehicle_roi.copy(), verbose=False, device=self.device)
                    for res_p in plate_results:
                        for box_p in res_p.boxes:
                            px1_rel, py1_rel, px2_rel, py2_rel = map(int, box_p.xyxy[0])
                            abs_px1, abs_py1 = x1_v + px1_rel, y1_v + py1_rel
                            abs_px2, abs_py2 = x1_v + px2_rel, y1_v + py2_rel
                            
                            plate_img_roi = vehicle_roi[max(0,py1_rel):min(vehicle_roi.shape[0],py2_rel), max(0,px1_rel):min(vehicle_roi.shape[1],px2_rel)]
                            if plate_img_roi.size == 0: continue
                            plate_text, ocr_confidence = self._extract_text_paddle(plate_img_roi)

                            if plate_text and ocr_confidence > 0.3:
                                info_vehiculo_bd, err_db, _ = db_manager.obtener_info_vehiculo_por_placa(plate_text)
                                if err_db: logger.error(f"Error DB al buscar placa {plate_text}: {err_db}")
                                
                                plate_info_summary = {"text": plate_text, "confidence": ocr_confidence, "box_vehicle_abs": [x1_v, y1_v, x2_v, y2_v], "box_plate_abs": [abs_px1, abs_py1, abs_px2, abs_py2], "info_bd": info_vehiculo_bd}
                                detected_plates_in_frame_info.append(plate_info_summary)
                                
                                if plate_text not in self.detected_plates_data_session: self.detected_plates_data_session[plate_text] = {'confidences': [], 'count': 0, 'timestamps': [], 'info_bd': info_vehiculo_bd}
                                self.detected_plates_data_session[plate_text]['confidences'].append(ocr_confidence)
                                self.detected_plates_data_session[plate_text]['count'] += 1
                                self.detected_plates_data_session[plate_text]['timestamps'].append(current_timestamp)

                                if ocr_confidence > highest_confidence_this_frame:
                                    highest_confidence_this_frame, best_plate_text_this_frame = ocr_confidence, plate_text
                                    if info_vehiculo_bd: info_vehiculo_registrado_detectado = info_vehiculo_bd
                                
                                is_alert_condition = info_vehiculo_bd and info_vehiculo_bd.get('estado_vehiculo') in ['Buscado', 'Sospechoso', 'Robado']
                                owner_user_id = info_vehiculo_bd.get('registrado_por_usuario_id') if info_vehiculo_bd else None
                                
                                if is_alert_condition and owner_user_id:
                                    estado_veh, nivel_alerta = info_vehiculo_bd.get('estado_vehiculo'), 'CRITICA' if info_vehiculo_bd.get('estado_vehiculo') == 'Buscado' else ('ALTA' if info_vehiculo_bd.get('estado_vehiculo') == 'Robado' else 'MEDIA')
                                    descripcion_inc = f"Vehículo {estado_veh}: Placa {plate_text}"
                                    
                                    observaciones_alerta = {"tipo_deteccion": "placa", "placa_texto": plate_text, "estado_vehiculo": estado_veh, "motivo_busqueda_vehiculo": info_vehiculo_bd.get('motivo_busqueda_vehiculo'), "confianza_ocr": round(float(ocr_confidence), 4), "id_vehiculo_registrado": info_vehiculo_bd.get('id_vehiculo'), "media_source": media_source_path, "timestamp_deteccion": current_timestamp.isoformat(), "coordenadas_placa_abs": [abs_px1, abs_py1, abs_px2, abs_py2]}
                                    
                                    id_inc, id_al, err_al, _ = db_manager.registrar_incidente_y_alerta(tipo_incidente_str='DETECCION_PLACA_ALERTA', descripcion_incidente=descripcion_inc, nivel_alerta_str=nivel_alerta, observaciones_alerta_json=observaciones_alerta, id_zona_afectada=id_zona, grado_confianza=round(float(ocr_confidence), 2), fecha_incidente_dt=current_timestamp, media_source_path_incidente=media_source_path, media_type=media_type)
                                    
                                    if not err_al and id_al:
                                        logger.info(f"ALERTA PLACA (ID: {id_al}) registrada para {plate_text}.")
                                        owner_user_data, err_user, _ = db_manager.get_user_by_id(owner_user_id)
                                        if owner_user_data and not err_user:
                                            db_manager.registrar_destinatarios_alerta(id_al, [owner_user_id])
                                            ruta_adjunto = media_source_path if media_type == 'image' else save_alert_frame(frame_to_process[y1_v:y2_v, x1_v:x2_v], Path(media_source_path).name, "placa_vehiculo")
                                            asunto_email = f"ALERTA VANGUARD IA: Vehículo {estado_veh} Detectado ({plate_text})"
                                            email_sender.send_alert_email_threaded_wrapper(asunto_email, nivel_alerta, observaciones_alerta, current_timestamp.isoformat(), owner_user_data['correo'], ruta_adjunto)
                                        else:
                                            logger.warning(f"No se pudo notificar: Usuario dueño {owner_user_id} del vehículo no encontrado o hubo un error: {err_user}")
                                    else: logger.error(f"Error al registrar alerta de placa {plate_text}: {err_al}")
        return detected_plates_in_frame_info, best_plate_text_this_frame, highest_confidence_this_frame, info_vehiculo_registrado_detectado
    
    def process_image(self, image_path: str, output_image_path: Optional[str] = None, id_zona: Optional[int] = None) -> Tuple[str, Optional[str], Optional[str], float, Optional[Dict[str, Any]]]:
        """Procesa una única imagen para detectar placas."""
        if not self.is_ready(): return "Detector de placas no listo.", None, None, 0.0, None
        self.detected_plates_data_session = {} 
        img_bgr_original = cv2.imread(image_path)
        if img_bgr_original is None: return "Error cargando imagen.", None, None, 0.0, None
        current_time = datetime.now()
        
        detected_plates_info, best_plate_text, highest_confidence, info_vehiculo_bd = self._process_frame_for_plates(
            img_bgr_original, image_path, current_time, id_zona, media_type='image'
        )
        
        summary_parts = [f"Placa: {best_plate_text if best_plate_text else 'No detectada'} (Conf: {highest_confidence:.2f})"]
        if info_vehiculo_bd:
            summary_parts.append(f"Info BD: {info_vehiculo_bd.get('marca', '')} {info_vehiculo_bd.get('modelo', '')}, Estado: {info_vehiculo_bd.get('estado_vehiculo', 'N/A')}")
            if info_vehiculo_bd.get('estado_vehiculo') in ['Buscado', 'Robado', 'Sospechoso']:
                summary_parts[-1] = f"🚨 {summary_parts[-1]} (Motivo: {info_vehiculo_bd.get('motivo_busqueda_vehiculo', 'N/A')})"
            if info_vehiculo_bd.get('nombre_propietario'):
                 summary_parts.append(f"Prop.: {info_vehiculo_bd['nombre_propietario']} (Estado Prop.: {info_vehiculo_bd.get('estado_propietario', 'N/A')})")
        final_summary_text = ". ".join(summary_parts)
        
        id_vehiculo_fk_para_registro = info_vehiculo_bd['id_vehiculo'] if info_vehiculo_bd else None
        if best_plate_text and highest_confidence > 0.4:
            db_manager.registrar_placa_detectada(
                texto_placa=best_plate_text, fecha_deteccion=current_time,
                id_vehiculo_registrado_fk=id_vehiculo_fk_para_registro,
                confianza_ocr=round(float(highest_confidence), 4), id_zona_deteccion=id_zona,
                media_source_path=image_path
            )
            
        if output_image_path and detected_plates_info:
            img_to_draw_output = img_bgr_original.copy()
            for p_info in detected_plates_info:
                if 'box_plate_abs' in p_info:
                    x1p, y1p, x2p, y2p = p_info['box_plate_abs'] 
                    color = (0,0,255) if p_info.get('info_bd') and p_info['info_bd'].get('estado_vehiculo') in ['Buscado','Robado','Sospechoso'] else (0,255,0)
                    cv2.rectangle(img_to_draw_output, (x1p, y1p), (x2p, y2p), color, 2)
                    cv2.putText(img_to_draw_output, f"{p_info.get('text','?')} ({p_info.get('confidence',0):.2f})", (x1p, y1p-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            try:
                cv2.imwrite(output_image_path, img_to_draw_output)
            except Exception as e: logger.error(f"Error escribiendo img salida (placas): {e}"); output_image_path = None
            return final_summary_text, output_image_path, best_plate_text, highest_confidence, info_vehiculo_bd
        return final_summary_text, None, best_plate_text, highest_confidence, info_vehiculo_bd

    def process_video(self, video_path: str, output_video_path: Optional[str] = None, id_zona: Optional[int] = None) -> Tuple[str, Optional[str], Optional[str], float, Optional[Dict[str, Any]]]:
        """Procesa un archivo de video, frame por frame, para detectar placas."""
        if not self.is_ready(): return "Detector de placas no listo.", None, None, 0.0, None
        self.detected_plates_data_session = {}
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened(): return "Error abriendo video.", None, None, 0.0, None
        out_writer = None
        if output_video_path:
            fps = cap.get(cv2.CAP_PROP_FPS); w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if w > 0 and h > 0 and fps > 0:
                out_writer = cv2.VideoWriter(output_video_path, cv2.VideoWriter_fourcc(*'avc1'), fps, (w,h))
                if not out_writer.isOpened(): logger.error(f"No se pudo init VideoWriter (placas): {output_video_path}"); out_writer = None
            else: logger.warning(f"Props video inválidas para {video_path}."); output_video_path = None
        
        frame_idx = 0; video_start_time = datetime.now(); detections_count = 0
        while cap.isOpened():
            ret, frame_orig = cap.read()
            if not ret: break
            ts_approx = video_start_time + timedelta(seconds=frame_idx / (cap.get(cv2.CAP_PROP_FPS) or 30.0))
            frame_out_for_video_writer = frame_orig.copy() 

            if frame_idx % self.frame_processing_interval == 0:
                infos, _, _, _ = self._process_frame_for_plates(frame_orig, video_path, ts_approx, id_zona, 'video')
                if infos:
                    detections_count += 1
                    if out_writer:
                        for p_info in infos:
                            if 'box_plate_abs' in p_info:
                                x1p,y1p,x2p,y2p = p_info['box_plate_abs']
                                clr = (0,0,255) if p_info.get('info_bd') and p_info.get('estado_vehiculo') in ['Buscado','Robado','Sospechoso'] else (0,255,0)
                                cv2.rectangle(frame_out_for_video_writer, (x1p,y1p), (x2p,y2p), clr, 2)
                                cv2.putText(frame_out_for_video_writer, f"{p_info.get('text','?')}", (x1p,y1p-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, clr, 2)
            
            if out_writer: out_writer.write(frame_out_for_video_writer)
            frame_idx += 1
        
        cap.release()
        if out_writer: out_writer.release()
        
        best_plate, best_conf, best_info_bd = self._get_most_accurate_plate_from_session()
        summary_parts = [f"Mejor Placa (Video): {best_plate or 'N/A'} (Conf Prom: {best_conf:.2f})"]
        id_veh_fk = None
        if best_info_bd:
            summary_parts.append(f"Info BD: {best_info_bd.get('marca','')} {best_info_bd.get('modelo','')}, Estado: {best_info_bd.get('estado_vehiculo','N/A')}")
            if best_info_bd.get('estado_vehiculo') in ['Buscado','Robado','Sospechoso']:
                summary_parts[-1] = f"🚨 {summary_parts[-1]} (Motivo: {best_info_bd.get('motivo_busqueda_vehiculo','N/A')})"
            if best_info_bd.get('nombre_propietario'):
                 summary_parts.append(f"Prop.: {best_info_bd['nombre_propietario']} (Estado Prop.: {best_info_bd.get('estado_propietario','N/A')})")
            id_veh_fk = best_info_bd.get('id_vehiculo')
        final_summary = ". ".join(summary_parts)

        if best_plate and best_conf > 0.5:
            first_ts = min(self.detected_plates_data_session[best_plate]['timestamps']) if best_plate in self.detected_plates_data_session and self.detected_plates_data_session[best_plate]['timestamps'] else video_start_time
            db_manager.registrar_placa_detectada(best_plate, first_ts, id_veh_fk, round(float(best_conf),4), id_zona, video_path)

        final_out_path = None
        if output_video_path and os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 0:
            if detections_count > 0: final_out_path = output_video_path
            else:
                try: os.remove(output_video_path)
                except OSError: pass
        elif output_video_path and os.path.exists(output_video_path):
            try: os.remove(output_video_path)
            except OSError: pass
        return final_summary, final_out_path, best_plate, best_conf, best_info_bd

    def _get_most_accurate_plate_from_session(self) -> Tuple[Optional[str], float, Optional[Dict[str, Any]]]:
        """
        Analiza todas las detecciones de placas de una sesión de video para determinar la más confiable.
        Pondera la confianza promedio del OCR, el número de detecciones y si la placa está en la base de datos.
        """
        if not self.detected_plates_data_session: return None, 0.0, None
        best_text: Optional[str] = None; highest_s: float = -1.0; best_avg_c: float = 0.0; best_bd: Optional[Dict[str, Any]] = None
        MIN_D, MIN_C = 2, 0.60; reliable, all_cand = [], []
        for text, data in self.detected_plates_data_session.items():
            cnt, confs, bd = data['count'], data['confidences'], data.get('info_bd')
            if not confs or cnt == 0: continue
            avg_c = sum(confs)/cnt; len_pen = 1.0
            if not (self.MIN_PLATE_LENGTH <= len(text) <= self.MAX_PLATE_LENGTH): len_pen = 0.7
            prio_b = 1.5 if bd and bd.get('estado_vehiculo') in ['Buscado','Robado','Sospechoso'] else 1.0
            s = (avg_c**1.5)*(cnt**0.5)*len_pen*prio_b; cand = (s,text,avg_c,bd); all_cand.append(cand)
            if cnt >= MIN_D and avg_c >= MIN_C: reliable.append(cand)
        if reliable: best = max(reliable, key=lambda i:i[0])
        elif all_cand: best = max(all_cand, key=lambda i:i[0])
        else: return None,0.0,None
        _, best_text, best_avg_c, best_bd = best
        return best_text, best_avg_c, best_bd

# ===================================================================
# --- CLASE: DETECTOR Y RECONOCEDOR FACIAL ---
# ===================================================================
class FaceDetector:
    """
    Gestiona la detección y el reconocimiento facial.
    Utiliza dlib para detectar rostros y un modelo ResNet para generar descriptores faciales.
    Compara los descriptores detectados con una base de datos de referencias cargada previamente.
    """
    def __init__(self, predictor_path="D_Rostros/Modelo/shape_predictor_68_face_landmarks.dat",
                 face_rec_model_path="D_Rostros/Modelo/dlib_face_recognition_resnet_model_v1.dat",
                 db_refresh_interval_seconds=300):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.detector, self.shape_predictor, self.face_recognizer = None, None, None
        try:
            base_dir = Path(__file__).resolve().parent
            predictor_path_abs = base_dir / predictor_path
            face_rec_model_path_abs = base_dir / face_rec_model_path
            self.detector = dlib.get_frontal_face_detector()
            if predictor_path_abs.exists(): self.shape_predictor = dlib.shape_predictor(str(predictor_path_abs))
            else: logger.error(f"Predictor no hallado: {predictor_path_abs}")
            if face_rec_model_path_abs.exists(): self.face_recognizer = dlib.face_recognition_model_v1(str(face_rec_model_path_abs))
            else: logger.error(f"Modelo ResNet no hallado: {face_rec_model_path_abs}")
        except Exception as e: logger.error(f"Error cargando dlib (rostros): {e}")
        self.ref_descriptors: Optional[torch.Tensor] = None
        self.ref_data: List[Dict[str, Any]] = []
        self.RECOGNITION_THRESHOLD = 0.55
        self.last_db_refresh_time = 0.0
        self.db_refresh_interval = db_refresh_interval_seconds
        self.needs_refresh = True

    def is_ready(self):
        """Verifica si los modelos dlib y las referencias faciales están cargados."""
        return all([self.detector, self.shape_predictor, self.face_recognizer, self.ref_descriptors is not None and self.ref_descriptors.numel() > 0])
    
    def _should_refresh_db(self):
        """Determina si es necesario recargar las referencias faciales desde la BD."""
        return self.needs_refresh or (time.time() - self.last_db_refresh_time > self.db_refresh_interval)
    
    def force_reload_references(self):
        """Fuerza una recarga de las referencias faciales en la próxima detección."""
        self.needs_refresh = True
        logger.info("Recarga forzada de referencias faciales solicitada.")
        self._load_references_from_db()
    
    def _load_references_from_db(self):
        """
        Carga las imágenes de referencia de las personas desde la base de datos,
        calcula sus descriptores faciales y los almacena en memoria para una comparación rápida.
        """
        if not self.is_ready_for_refs(): return
        if not self._should_refresh_db() and self.ref_descriptors is not None: return
        logger.info("Cargando/Recargando referencias faciales desde la base de datos...")
        folder_abs = app.config['PERSONAS_IMG_REF_FOLDER']

        data, err, _ = db_manager.obtener_todas_personas_para_referencia()
        if err or not data:
            logger.error(f"Error obteniendo personas de BD para referencias: {err or 'No hay personas.'}")
            self.ref_descriptors, self.ref_data = None, []
            self.last_db_refresh_time, self.needs_refresh = time.time(), False
            return
            
        descs, valid_ref_data = [], []
        for p in data:
            if not p.get('imagen_facial_ref_filename'): continue
            path = os.path.join(folder_abs, p['imagen_facial_ref_filename'])
            if not os.path.exists(path):
                logger.warning(f"Imagen de referencia no encontrada en disco: {path}"); continue
            try:
                img_bgr = cv2.imread(path)
                img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                rects = self.detector(img_rgb, 1)
                if not rects:
                    logger.warning(f"No se detectaron rostros en imagen de referencia: {path}"); continue
                
                main_face_rect = max(rects, key=lambda r: r.width() * r.height())
                descriptor = self._get_face_descriptor_tensor(img_rgb, main_face_rect)
                
                if descriptor is not None:
                    descs.append(descriptor)
                    valid_ref_data.append(p) 
            except Exception as e:
                logger.error(f"Error procesando imagen de referencia {path}: {e}")

        if descs:
            self.ref_descriptors = torch.stack(descs).to(self.device)
            self.ref_data = valid_ref_data
            logger.info(f"{len(self.ref_data)} referencias faciales cargadas y listas para reconocimiento.")
        else:
            logger.warning("No se cargó ningún descriptor de referencia facial válido.")
            self.ref_descriptors, self.ref_data = torch.empty(0), []
        
        self.last_db_refresh_time, self.needs_refresh = time.time(), False

    def is_ready_for_refs(self):
        """Verifica si los modelos base de dlib están listos para procesar referencias."""
        return all([self.detector, self.shape_predictor, self.face_recognizer])
    
    def _get_face_descriptor_tensor(self, img_rgb, face_rect):
        """Calcula el descriptor facial de 128 dimensiones para un rostro detectado."""
        try:
            shape = self.shape_predictor(img_rgb, face_rect)
            desc = np.array(self.face_recognizer.compute_face_descriptor(img_rgb, shape, 1))
            return torch.tensor(desc, dtype=torch.float32, device=self.device)
        except Exception as e:
            logger.error(f"No se pudo computar el descriptor facial: {e}")
            return None

    def _recognize_face(self, desc_check: torch.Tensor) -> Dict[str, Any]:
        """
        Compara un descriptor facial detectado con la base de datos de descriptores de referencia.
        Devuelve la información de la persona con la coincidencia más cercana si supera el umbral.
        """
        default_result = {
            "id_persona": None, "nombre": "Desconocido", "distance": float('inf'),
            "confidence": 0.0, "estado_persona": "N/A", "motivo_busqueda": None,
            "registrado_por_usuario_id": None
        }
        if self.ref_descriptors is None or not self.ref_descriptors.numel() or not self.ref_data:
            return default_result

        try:
            dists = torch.norm(self.ref_descriptors - desc_check.unsqueeze(0), dim=1)
            min_dist_tensor, best_match_idx_tensor = torch.min(dists, dim=0)
            min_distance = min_dist_tensor.item()
            best_match_idx = best_match_idx_tensor.item()

            if min_distance < self.RECOGNITION_THRESHOLD:
                confidence = max(0.0, (self.RECOGNITION_THRESHOLD - min_distance) / self.RECOGNITION_THRESHOLD)
                matched_person_data = self.ref_data[best_match_idx]
                return {
                    "id_persona": matched_person_data.get('id_persona'),
                    "nombre": matched_person_data.get('nombre'),
                    "distance": min_distance,
                    "confidence": confidence,
                    "estado_persona": matched_person_data.get('estado_persona'),
                    "motivo_busqueda": matched_person_data.get('motivo_busqueda'),
                    "registrado_por_usuario_id": matched_person_data.get('registrado_por_usuario_id')
                }
            
            default_result["distance"] = min_distance
            return default_result
        except Exception as e:
            logger.error(f"Error en la lógica de reconocimiento facial (_recognize_face): {e}")
            return default_result

    def _process_single_frame_for_faces(self, frame_bgr: np.ndarray, media_source_path: str, frame_timestamp: datetime, id_zona: Optional[int] = None, media_type: Optional[str] = 'image') -> Tuple[List[Dict], List[str]]:
        """
        Lógica central para procesar un único frame en busca de rostros:
        1. Detecta todos los rostros en el frame.
        2. Para cada rostro, calcula su descriptor.
        3. Intenta reconocer el rostro comparándolo con las referencias.
        4. Registra la detección en la base de datos.
        5. Si la persona reconocida está marcada (Buscada, Restringida), genera un incidente y una alerta.
        """
        self._load_references_from_db()
        if not self.is_ready_for_refs(): return [], []
        frame_to_process = frame_bgr.copy()
        detected_faces_info_list: List[Dict] = []
        known_persons_this_frame: List[str] = []

        try:
            frame_rgb = cv2.cvtColor(frame_to_process, cv2.COLOR_BGR2RGB)
            face_rects = self.detector(frame_rgb, 0)
            for rect in face_rects:
                x, y, w, h = rect.left(), rect.top(), rect.width(), rect.height()
                if w < 40 or h < 40: continue
                
                descriptor = self._get_face_descriptor_tensor(frame_rgb, rect)
                if descriptor is None: continue

                recognition_result = self._recognize_face(descriptor)
                persona_id = recognition_result['id_persona']
                
                db_manager.registrar_persona_detectada(
                    nombre_persona=recognition_result['nombre'], id_persona_fk=persona_id, fecha_deteccion=frame_timestamp,
                    confianza_reconocimiento=round(float(recognition_result['confidence']), 4), distancia_descriptor=round(float(recognition_result['distance']), 6),
                    id_zona_deteccion=id_zona, coordenadas_deteccion_frame_json=json.dumps({"x":x,"y":y,"w":w,"h":h}),
                    media_source_path=media_source_path
                )
                
                is_alert_condition = persona_id is not None and recognition_result['estado_persona'] in ['Buscado', 'Restringido', 'Sospechoso']
                owner_user_id = recognition_result.get('registrado_por_usuario_id')

                if is_alert_condition and owner_user_id:
                    estado_persona = recognition_result['estado_persona']
                    nombre_display = recognition_result['nombre']
                    nivel_alerta = 'CRITICA' if estado_persona == 'Buscado' else ('ALTA' if estado_persona == 'Restringido' else 'MEDIA')
                    descripcion_inc = f"Persona {estado_persona}: {nombre_display}"
                    
                    obs_alerta = {"tipo_deteccion":"persona", "nombre_reconocido":nombre_display, "estado_persona":estado_persona, "motivo_busqueda": recognition_result.get('motivo_busqueda'), "confianza_reconocimiento":round(float(recognition_result['confidence']),4), "id_persona_registrada":persona_id, "media_source":media_source_path, "timestamp_deteccion":frame_timestamp.isoformat(), "coordenadas_rostro_abs":[x,y,x+w,y+h]}
                    
                    id_inc, id_al, err_al, _ = db_manager.registrar_incidente_y_alerta(tipo_incidente_str='DETECCION_PERSONA_ALERTA', descripcion_incidente=descripcion_inc, nivel_alerta_str=nivel_alerta, observaciones_alerta_json=obs_alerta, id_zona_afectada=id_zona, grado_confianza=round(float(recognition_result['confidence']),2), fecha_incidente_dt=frame_timestamp, media_source_path_incidente=media_source_path, media_type=media_type)
                    
                    if not err_al and id_al:
                        logger.info(f"ALERTA PERSONA (ID: {id_al}) registrada para {nombre_display}.")
                        owner_user_data, err_user, _ = db_manager.get_user_by_id(owner_user_id)
                        if owner_user_data and not err_user:
                            db_manager.registrar_destinatarios_alerta(id_al, [owner_user_id])
                            adj_path = media_source_path if media_type == 'image' else save_alert_frame(frame_to_process[y:y+h, x:x+w], Path(media_source_path).name, "rostro")
                            asunto = f"ALERTA VANGUARD IA: Persona {estado_persona} Detectada ({nombre_display})"
                            email_sender.send_alert_email_threaded_wrapper(asunto, nivel_alerta, obs_alerta, frame_timestamp.isoformat(), owner_user_data['correo'], adj_path)
                        else:
                            logger.warning(f"No se pudo notificar: Usuario dueño {owner_user_id} de la persona no encontrado o hubo un error: {err_user}")
                    else:
                        logger.error(f"Error al registrar alerta de persona {nombre_display}: {err_al}")
                
                detected_faces_info_list.append({"id_persona_registrada":persona_id, "nombre_reconocido": recognition_result['nombre'], "estado_persona": recognition_result['estado_persona'], "confidence_recognition": recognition_result['confidence'], "box_abs":[x,y,w,h]})
                if persona_id is not None: known_persons_this_frame.append(f"{recognition_result['nombre']} (ID:{persona_id}, Estado:{recognition_result['estado_persona']})")
        except Exception as e: logger.error(f"EXCEPCIÓN procesando frame (rostros): {e}", exc_info=True)
        return detected_faces_info_list, list(set(known_persons_this_frame))

    def process_image(self, image_path: str, output_image_path: Optional[str] = None, id_zona: Optional[int] = None) -> Tuple[str, Optional[str], List[str]]:
        """Procesa una única imagen para detectar y reconocer rostros."""
        self._load_references_from_db() 
        if not self.is_ready_for_refs(): return "Detector de rostros no listo.", None, []
        img_orig = cv2.imread(image_path)
        if img_orig is None: return "Error cargando imagen.", None, []
        
        infos, names_sum = self._process_single_frame_for_faces(img_orig, image_path, datetime.now(), id_zona, 'image')
        
        parts = []
        if not infos: parts.append("No se detectaron rostros.")
        else:
            alert_present = any(fi.get('estado_persona') in ['Buscado','Sospechoso','Restringido'] for fi in infos)
            if names_sum: parts.append(f"Identificados: {'; '.join(names_sum)}")
            else: parts.append(f"Detectados {len(infos)} rostro(s), ninguno conocido.")
            if alert_present: parts.append("🚨 ALERTA: Persona de interés detectada.") 
        sum_txt = "D_Rostro: " + ". ".join(parts)

        if output_image_path and infos:
            img_draw = img_orig.copy()
            for fi in infos:
                x,y,w,h = fi['box_abs']; lbl = f"{fi['nombre_reconocido']}"
                if fi['id_persona_registrada']: lbl += f" ({fi['confidence_recognition']:.2f})"
                clr=(0,0,255) 
                if fi['id_persona_registrada']:
                    if fi.get('estado_persona')=='Autorizado' or fi.get('estado_persona')=='No asignado': clr=(0,255,0) 
                    elif fi.get('estado_persona') in ['Buscado','Sospechoso','Restringido']: clr=(0,0,255) 
                    else: clr=(0,255,255) 
                if fi.get('estado_persona') in ['Buscado','Sospechoso','Restringido']: lbl = f"🚨 {lbl} ({fi['estado_persona']})"
                cv2.rectangle(img_draw,(x,y),(x+w,y+h),clr,2)
                txt_y=y-10 if y-10>10 else y+h+20; font_s=0.5
                (txt_w,_),_=cv2.getTextSize(lbl,cv2.FONT_HERSHEY_SIMPLEX,font_s,1)
                txt_x=x if x+txt_w<=img_draw.shape[1] else img_draw.shape[1]-txt_w-5
                cv2.putText(img_draw,lbl,(txt_x,txt_y),cv2.FONT_HERSHEY_SIMPLEX,font_s,clr,2)
            try: cv2.imwrite(output_image_path,img_draw)
            except Exception as e: logger.error(f"Error escribiendo img salida (rostros): {e}"); output_image_path=None
            return sum_txt, output_image_path, names_sum
        return sum_txt, None, names_sum

    def process_video(self, video_path: str, output_video_path: Optional[str] = None, id_zona: Optional[int] = None) -> Tuple[str, Optional[str], List[str]]:
        """Procesa un archivo de video, frame por frame, para detectar y reconocer rostros."""
        self._load_references_from_db()
        if not self.is_ready_for_refs(): return "Detector de rostros no listo.", None, []
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened(): return "Error abriendo video.", None, []
        out_writer = None
        if output_video_path:
            fps=cap.get(cv2.CAP_PROP_FPS); w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if w>0 and h>0 and fps>0:
                out_writer=cv2.VideoWriter(output_video_path,cv2.VideoWriter_fourcc(*'avc1'),fps,(w,h))
                if not out_writer.isOpened(): logger.error(f"No se pudo init VideoWriter (rostros): {output_video_path}"); out_writer=None
            else: logger.warning(f"Props video inválidas: {video_path}"); output_video_path=None
        
        all_known_vid_summary=set(); frame_idx=0; start_t=datetime.now(); dets_count_in_video=0; alert_flag_in_video=False; VID_INTERVAL=5
        
        while cap.isOpened():
            ret,frame_orig=cap.read()
            if not ret: break
            ts=start_t+timedelta(seconds=frame_idx/(cap.get(cv2.CAP_PROP_FPS) or 30.0))
            frame_out_for_video_writer=frame_orig.copy()
            
            if frame_idx % VID_INTERVAL == 0:
                infos,names_this_frame=self._process_single_frame_for_faces(frame_orig,video_path,ts,id_zona,'video')
                
                if names_this_frame: all_known_vid_summary.update(names_this_frame)
                if infos:
                    dets_count_in_video+=1
                    if any(fi.get('estado_persona') in ['Buscado','Sospechoso','Restringido'] for fi in infos): 
                        alert_flag_in_video=True
                    if out_writer:
                        for fi in infos:
                            x,y,wf,hf=fi['box_abs']; lbl=f"{fi['nombre_reconocido']}"
                            if fi['id_persona_registrada']: lbl+=f" ({fi['confidence_recognition']:.2f})"
                            clr=(0,0,255) 
                            if fi['id_persona_registrada']:
                                if fi.get('estado_persona')=='Autorizado' or fi.get('estado_persona')=='No asignado': clr=(0,255,0)
                                elif fi.get('estado_persona') in ['Buscado','Sospechoso','Restringido']: clr=(0,0,255)
                                else: clr=(0,255,255)
                            if fi.get('estado_persona') in ['Buscado','Sospechoso','Restringido']: lbl=f"🚨 {lbl} ({fi['estado_persona']})"
                            cv2.rectangle(frame_out_for_video_writer,(x,y),(x+wf,y+hf),clr,2)
                            txt_y=y-10 if y-10>10 else y+hf+20
                            cv2.putText(frame_out_for_video_writer,lbl,(x,txt_y),cv2.FONT_HERSHEY_SIMPLEX,0.5,clr,2)
            
            if out_writer: out_writer.write(frame_out_for_video_writer)
            frame_idx+=1
        
        cap.release()
        if out_writer: out_writer.release()
        
        parts=[]
        if not dets_count_in_video: parts.append("No se detectaron rostros.")
        elif not all_known_vid_summary: parts.append("Rostros detectados, ninguno conocido.")
        else:
            parts.append(f"Identificados: {'; '.join(list(all_known_vid_summary))}.")
            if alert_flag_in_video: parts.append("🚨 ALERTA: Persona(s) de interés detectada(s).")
        sum_txt="D_Rostro (Video): "+" ".join(parts)
        
        final_path=None
        if output_video_path and os.path.exists(output_video_path) and os.path.getsize(output_video_path)>0:
            if dets_count_in_video>0: final_path=output_video_path
            else:
                try: os.remove(output_video_path)
                except OSError: pass
        elif output_video_path and os.path.exists(output_video_path):
            try: os.remove(output_video_path)
            except OSError: pass
        return sum_txt,final_path,list(all_known_vid_summary)

license_plate_detector = LicensePlateDetector()
face_detector = FaceDetector()

# ===================================================================
# --- RUTAS DE API: AUTENTICACIÓN Y GESTIÓN DE USUARIOS ---
# ===================================================================
@app.route('/api/user/profile', methods=['GET'])
@login_required
def get_user_profile():
    """Obtiene el perfil completo del usuario con sesión activa."""
    user_data, err, code = db_manager.get_user_by_id(current_user.id)
    if err:
        return jsonify({"error": err}), code

    if 'hash_password' in user_data:
        del user_data['hash_password']
        
    return jsonify(user_data), 200

@app.route('/api/user/profile', methods=['PUT'])
@login_required
def update_user_profile():
    """Actualiza el perfil del usuario con sesión activa."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No se proporcionaron datos."}), 400

    new_password = data.pop('new_password', None)
    current_password = data.pop('current_password', None)

    if new_password:
        if not current_password:
            return jsonify({"error": "Se requiere la contraseña actual para establecer una nueva."}), 400
        
        user_full_data, _, _ = db_manager.get_user_by_id(current_user.id)
        if not check_password_hash(user_full_data['hash_password'], current_password):
            return jsonify({"error": "La contraseña actual es incorrecta."}), 403
        
        data['hash_password'] = generate_password_hash(new_password)

    updated_user, err, code = db_manager.update_user(current_user.id, data)

    if err:
        return jsonify({"error": err}), code
        
    if 'hash_password' in updated_user:
        del updated_user['hash_password']
        
    flash("Perfil actualizado con éxito.", "success")
    return jsonify({"message": "Perfil actualizado con éxito.", "user": updated_user}), code
    
@app.route('/api/register', methods=['POST'])
def register_api():
    """Endpoint para registrar un nuevo usuario en el sistema."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No se proporcionaron datos."}), 400
    
    correo = data.get('correo')
    password = data.get('password')
    nombre_completo = data.get('nombre_completo')
    apellidos = data.get('apellidos')
    numero_celular = data.get('numero_celular')
    rol = data.get('rol', 'operador') 

    if not all([correo, password, nombre_completo, apellidos, numero_celular]):
        return jsonify({"error": "Faltan campos obligatorios: correo, password, nombre_completo, apellidos, numero_celular."}), 400
        
    if rol not in ['admin', 'operador', 'supervisor', 'analista']:
        return jsonify({"error": "Rol no válido."}), 400

    hashed_password = generate_password_hash(password)
    
    user_data = {
        "nombre_completo": nombre_completo, "apellidos": apellidos, "correo": correo,
        "numero_celular": numero_celular, "hash_password": hashed_password, "rol": rol
    }
    
    new_user, error, code = db_manager.create_user(user_data)
    
    if error:
        return jsonify({"error": error}), code
    
    return jsonify({"message": "Usuario registrado exitosamente.", "user": new_user}), code

@app.route('/api/login', methods=['POST'])
def login_api():
    """Endpoint para iniciar sesión de un usuario y crear una sesión."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No se proporcionaron datos."}), 400
        
    correo = data.get('correo')
    password = data.get('password')

    if not correo or not password:
        return jsonify({"error": "Se requiere correo y contraseña."}), 400
    
    user_data, err, _ = db_manager.get_user_by_email(correo)
    
    if user_data and not err and check_password_hash(user_data['hash_password'], password):
        if user_data['activo']:
            user_obj = User(
                id_usuario=user_data['id_usuario'], correo=user_data['correo'],
                rol=user_data['rol'], nombre_completo=user_data['nombre_completo'],
                activo=user_data['activo']
            )
            login_user(user_obj, remember=True)
            return jsonify({"message": "Login exitoso"}), 200
        else:
            return jsonify({"error": "La cuenta de usuario está inactiva."}), 403
    
    return jsonify({"error": "Credenciales inválidas."}), 401

@app.route('/api/logout', methods=['POST'])
@login_required
def logout_api():
    """Endpoint para cerrar la sesión del usuario actual."""
    logger.info(f"Logout para usuario: {current_user.correo} (ID: {current_user.id})")
    logout_user()
    return jsonify({"message": "Sesión cerrada exitosamente."}), 200

@app.route('/api/current_user_profile', methods=['GET'])
@login_required
def current_user_profile_api():
    """Devuelve la información del perfil del usuario actualmente autenticado."""
    user_data, error, code = db_manager.get_user_by_id(current_user.id)
    
    if error:
        return jsonify({"error": error}), code

    if user_data and 'hash_password' in user_data:
        del user_data['hash_password']
        
    return jsonify(user_data), 200

# ===================================================================
# --- RUTAS DE VISTAS (FRONTEND) ---
# ===================================================================
@app.route('/')
def inicio_route(): return render_template('inicio.html')

@app.route('/inicio')
@login_required
def index_route(): return render_template('index.html')

@app.route('/analisis')
@login_required
def analisis_page(): return render_template('analisis.html')

@app.route('/zonas_vigiladas')
@login_required
def zonas_vigiladas_page(): return render_template('zonas_vigiladas.html')

@app.route('/incidentes')
@login_required
def incidentes_page(): return render_template('incidentes.html')

@app.route('/personas_vehiculos')
@login_required
def personas_vehiculos_page(): return render_template('personas_vehiculos.html')

@app.route('/alertas')
@login_required
def alertas_main_page(): return render_template('alertas.html')

@app.route('/login')
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for('index_route'))
    return render_template('login.html')

@app.route('/register')
def register_page():
    if current_user.is_authenticated:
        return redirect(url_for('index_route'))
    return render_template('register.html')

# ===================================================================
# --- RUTAS DE API: SERVICIO DE ARCHIVOS Y RECURSOS ---
# ===================================================================
@app.route('/media_ref/personas/<path:filename>')
@login_required
def serve_personas_imagen_ref(filename):
    """Sirve las imágenes de referencia de las personas registradas."""
    return send_from_directory(app.config['PERSONAS_IMG_REF_FOLDER'], filename)

@app.route('/outputs/<path:filename>')
@login_required
def serve_output_file(filename):
    """Sirve los archivos generados por el análisis (videos/imágenes con detecciones)."""
    for folder_key in ['FRAMES_OUTPUT_FOLDER', 'OUTPUT_FOLDER']:
        folder_path = os.path.abspath(app.config[folder_key])
        file_path = os.path.join(folder_path, filename)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(folder_path, filename)
    logger.warning(f"Archivo no encontrado en outputs o frames: {filename}")
    return jsonify({"error": "Archivo no encontrado."}), 404

# ===================================================================
# --- API PRINCIPAL DE ANÁLISIS Y GEMINI ---
# ===================================================================
def _check_gemini_response_for_alert_and_log(
    gemini_response_text_raw: str, original_media_path: str, media_type: str,
    model_name_gemini: str, id_zona_contexto: Optional[int], analysis_type: str,
    user_requesting: User
):
    """
    Analiza la respuesta de texto de Gemini para detectar palabras clave de emergencia/sospecha.
    Si se encuentran, registra un incidente y una alerta en la base de datos.
    """
    if not gemini_response_text_raw: return
    text_lower = gemini_response_text_raw.lower()
    triggered_kws, nivel_alerta_str, desc_incidente_db = [], None, ""
    
    match_emergencia = re.search(r"evaluación de emergencia:\s*(alerta🚨🚨🚨|sí🚨🚨🚨|sí|si)\s*(.*)", text_lower, re.IGNORECASE)
    if match_emergencia and match_emergencia.group(1).lower().startswith(("alerta","sí","si")):
        nivel_alerta_str, desc_gemini = 'CRITICA', match_emergencia.group(2).strip()
        desc_incidente_db = f"Gemini (Audio): Emergencia. Detalles: {desc_gemini or 'No especificados.'}"
        triggered_kws.append("evaluacion_emergencia_si_audio")
    elif "alerta🚨🚨🚨" in text_lower:
        nivel_alerta_str, desc_incidente_db = 'CRITICA', f"Gemini ({analysis_type}): Alerta crítica explícita."
        triggered_kws.append("gemini_alerta_explicita_critica")
    else:
        for kw_list, level, type_msg in [(KEYWORDS_EMERGENCIA_GEMINI_STRICT + KEYWORDS_EMERGENCIA_GEMINI, 'ALTA', 'Posible emergencia'), (KEYWORDS_SOSPECHOSO_GEMINI, 'MEDIA', 'Actividad sospechosa')]:
            for kw in kw_list:
                if kw in text_lower:
                    nivel_alerta_str, desc_incidente_db = level, f"Gemini ({analysis_type}): {type_msg} (keyword: '{kw}')."
                    triggered_kws.append(kw); break
            if nivel_alerta_str: break

    if nivel_alerta_str and desc_incidente_db: 
        obs_alerta_db = {"tipo_deteccion":"gemini_analysis", "analysis_type":analysis_type, "gemini_model":model_name_gemini, "triggered_keywords":triggered_kws, "gemini_response_snippet":gemini_response_text_raw[:500], "media_source":original_media_path, "timestamp_analysis":datetime.now().isoformat()}
        
        id_inc, id_al, err_al, _ = db_manager.registrar_incidente_y_alerta(
            id_usuario_reporta=user_requesting.id, tipo_incidente_str=f"INCIDENTE_GEMINI_{analysis_type.upper()}",
            descripcion_incidente=desc_incidente_db, nivel_alerta_str=nivel_alerta_str, 
            observaciones_alerta_json=obs_alerta_db, id_zona_afectada=id_zona_contexto,
            grado_confianza=(0.85 if nivel_alerta_str=='CRITICA' else (0.75 if nivel_alerta_str=='ALTA' else 0.50)),
            fecha_incidente_dt=datetime.now(), media_source_path_incidente=(original_media_path if media_type in ['video', 'audio'] else None), media_type=media_type
        )
        if not err_al and id_al:
            logger.info(f"ALERTA GEMINI (ID:{id_al}) registrada para usuario {user_requesting.id}.")
            db_manager.registrar_destinatarios_alerta(id_al, [user_requesting.id])
            asunto_email_gemini = f"Alerta Vanguard IA ({user_requesting.nombre_completo}) - {nivel_alerta_str.upper()} (Análisis {analysis_type})"
            detalles_email_gemini = {"tipo_deteccion":"gemini_analysis", "gemini_full_response":gemini_response_text_raw}
            email_sender.send_alert_email_threaded_wrapper(asunto_email_gemini, nivel_alerta_str, detalles_email_gemini, obs_alerta_db["timestamp_analysis"], user_requesting.correo, None)
        else:
            logger.error(f"Error al registrar alerta de Gemini para {analysis_type}: {err_al}")
    
    if nivel_alerta_str and desc_incidente_db and media_type == 'audio' and id_inc:
        match_trans = re.search(r"transcripción:\s*(.*?)(\*\*evaluación|\*\*resumen|$)", gemini_response_text_raw, re.IGNORECASE | re.DOTALL)
        transcripcion = match_trans.group(1).strip() if match_trans else "Transcripción no disponible o no extraída."
        db_manager.registrar_evento_audio(id_incidente=id_inc, descripcion_corta=desc_incidente_db[:250], transcripcion_completa=transcripcion, respuesta_llm=gemini_response_text_raw[:500], modelo_llm_usado=model_name_gemini, media_source_path=original_media_path, fecha_evento_dt=datetime.now())

@app.route('/api/analyze', methods=['POST'])
@login_required
def analyze_media_api():
    """
    Endpoint principal que recibe un archivo multimedia y lo procesa con los modelos seleccionados
    (Rostros, Placas, Gemini). Orquesta la ejecución de los diferentes detectores.
    """
    if 'file' not in request.files: return jsonify({"error": "No se proporcionó archivo."}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({"error": "No se seleccionó archivo."}), 400
    if not allowed_file(file.filename): return jsonify({"error": "Tipo de archivo no permitido."}), 400
    
    selected_models = request.form.getlist('models[]')
    if not selected_models: return jsonify({"error": "No se seleccionaron modelos."}), 400

    original_filename_safe = werkzeug.utils.secure_filename(Path(file.filename).name if file.filename else "unknown_file")
    ts_file = str(int(time.time()))
    unique_stem = f"{ts_file}_{Path(original_filename_safe).stem}"
    file_ext = Path(original_filename_safe).suffix.lower()
    saved_filename = f"{unique_stem}{file_ext}"
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)

    try:
        file.save(upload_path)
    except Exception as e:
        logger.error(f"Error guardando archivo subido {upload_path}: {e}")
        return jsonify({"error": f"Error al guardar archivo: {e}"}), 500

    current_file_type = get_file_type(saved_filename)
    if not current_file_type:
        if os.path.exists(upload_path): os.remove(upload_path)
        return jsonify({"error": "No se pudo determinar tipo de archivo válido."}), 400

    results_web: List[str] = []
    processed_media_web: Dict[str, str] = {}
    id_zona = request.form.get('id_zona', type=int)

    if "D_Rostro" in selected_models and current_file_type in ['image', 'video']:
        face_detector.force_reload_references()
        if face_detector.is_ready_for_refs():
            out_fn = f"{unique_stem}_faces_web{file_ext}"
            out_path = os.path.join(app.config['OUTPUT_FOLDER'], out_fn)
            try:
                res, proc_path, _ = face_detector.process_image(upload_path, out_path, id_zona) if current_file_type == 'image' else face_detector.process_video(upload_path, out_path, id_zona)
                results_web.append(res)
                if proc_path: processed_media_web['face_output'] = url_for('serve_output_file', filename=Path(proc_path).name)
            except Exception as e: results_web.append(f"D_Rostro: Error - {e}"); logger.error("Error en API D_Rostro", exc_info=True)
        else: results_web.append("D_Rostro: Modelo no listo.")
    
    if "D_Placas" in selected_models and current_file_type in ['image', 'video']:
        if license_plate_detector.is_ready():
            out_fn = f"{unique_stem}_plates_web{file_ext}"
            out_path = os.path.join(app.config['OUTPUT_FOLDER'], out_fn)
            try:
                res, proc_path, _, _, _ = license_plate_detector.process_image(upload_path, out_path, id_zona) if current_file_type == 'image' else license_plate_detector.process_video(upload_path, out_path, id_zona)
                results_web.append(f"D_Placas: {res}")
                if proc_path: processed_media_web['plate_output'] = url_for('serve_output_file', filename=Path(proc_path).name)
            except Exception as e: results_web.append(f"D_Placas: Error - {e}"); logger.error("Error en API D_Placas", exc_info=True)
        else: results_web.append("D_Placas: Modelo no listo.")

    gemini_prompts = {
        "Audio_Contexto": (
            "**Análisis de Contexto de Audio Vanguard IA**:\n"
            "Por favor, analiza el contenido de audio de este archivo. Sigue estas instrucciones cuidadosamente:\n"
            "1.  **Transcripción (Si aplica):** Si hay voz humana significativa y clara, transcribe las partes más relevantes. Si el audio es muy largo o el habla no es clara, indica que la transcripción completa no es viable y proporciona un resumen de los temas hablados si es posible.\n"
            "2.  **Evaluación de Emergencia:** Evalúa si el audio contiene alguna situación de emergencia (ej. gritos de auxilio claros, sonidos de disparos evidentes, explosiones, sirenas de emergencia muy cercanas y persistentes, accidentes graves audibles). Responde con \"Alerta🚨🚨🚨\" o \"No\". Si es \"Alerta🚨🚨🚨\", describe brevemente la naturaleza de la emergencia detectada.\n"
            "3.  **Resumen del Contenido General:** Proporciona un resumen conciso del contenido general del audio (ej. conversación casual, música, ruido ambiental, sonidos específicos).\n"
            "4.  **Sonidos Clave Detectados:** Lista cualquier sonido clave o distintivo adicional (ej. tipos de vehículos, animales, herramientas, alarmas no de emergencia).\n"
            "Formatea tu respuesta usando estos encabezados en negrita: **Transcripción:**, **Evaluación de Emergencia:**, **Resumen del Contenido General:**, **Sonidos Clave Detectados:**."
        ),
        "Analisis_profundo": (
            f"**Análisis General del Archivo Vanguard IA ({current_file_type.capitalize() if current_file_type else 'Multimedia'})**:\n"
            "Describe la escena visual (si es imagen o video) y/o el contenido auditivo (si es audio o video). "
            "Identifica objetos, personas, acciones o sonidos relevantes. "
            "Si detectas alguna actividad que podría considerarse inusual, sospechosa o una emergencia, menciónala específicamente. "
            "Proporciona la información clave de forma clara y concisa. "
            "Usa **negrita** para enfatizar los títulos o puntos importantes si generas una estructura con ellos."
            "En caso haya algun incidente relevante o algo urgente en el medio, lo primero que mencionaras sera Alerta🚨🚨🚨, en caso no haya nada relevante o inmediato solo describelo brevemente."
        )
    }
    for model_key, prompt_text in gemini_prompts.items():
        if model_key in selected_models:
            is_audio_context = (model_key == "Audio_Contexto")
            is_applicable = (current_file_type in ['audio', 'video']) if is_audio_context else (current_file_type is not None)
            if is_applicable and genai:
                raw_res, model_name = analyze_with_gemini(upload_path, current_file_type, custom_prompt=prompt_text)
                if raw_res and model_name:
                    html_res = raw_res.replace("\n", "<br>").replace(r'\*\*(.*?)\*\*', r'<strong>\1</strong>')
                    results_web.append(f"<b>{model_key.replace('_', ' ')}:</b><br>{html_res}")
                    _check_gemini_response_for_alert_and_log(raw_res, upload_path, current_file_type, model_name, id_zona, model_key, current_user)
                else: results_web.append(f"{model_key.replace('_', ' ')}: {raw_res or 'No se obtuvo respuesta.'}")
            elif not genai: results_web.append(f"{model_key}: Gemini API no configurada.")
            else: results_web.append(f"{model_key}: No aplicable a este archivo.")

    if os.path.exists(upload_path):
        try: os.remove(upload_path)
        except OSError as e: logger.error(f"Error eliminando archivo temporal {upload_path}: {e}")

    final_response_text = "<br><hr><br>".join(results_web) if results_web else "No se seleccionaron modelos válidos o no hubo resultados."
    
    return jsonify({"analysis_text": final_response_text, "processed_media": processed_media_web, "original_media_type": current_file_type})

def analyze_with_gemini(file_path: str, file_type_str: str, custom_prompt: Optional[str] = None) -> Tuple[str, Optional[str]]:
    """
    Gestiona la interacción con el API de Google Gemini:
    1. Sube el archivo multimedia.
    2. Espera a que el archivo esté procesado y activo.
    3. Envía el prompt junto con el archivo para su análisis.
    4. Elimina el archivo de los servidores de Gemini después del análisis.
    """
    if not genai:
        return "Error: Gemini API no configurada.", None
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return "Error: Archivo no encontrado o vacío.", None

    uploaded_file = None
    try:
        mime_map = {'image': {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg'},
                    'video': {'mp4': 'video/mp4', 'avi': 'video/x-msvideo', 'mov': 'video/quicktime'},
                    'audio': {'mp3': 'audio/mpeg', 'wav': 'audio/wav', 'ogg': 'audio/ogg'}}
        ext = Path(file_path).suffix.lower().lstrip('.')
        actual_mime_type = mime_map.get(file_type_str, {}).get(ext)
        if not actual_mime_type:
            return f"Error: Tipo/extensión ({ext}) no soportado por Gemini.", None

        logger.info(f"Subiendo archivo a Gemini: {file_path}")
        uploaded_file = genai.upload_file(path=file_path, display_name=Path(file_path).name, mime_type=actual_mime_type)
        logger.info(f"Archivo subido. ID: {uploaded_file.name}. Estado inicial: {uploaded_file.state}")

        timeout_seconds = 180 
        polling_interval_seconds = 5 
        start_time = time.time()

        while (time.time() - start_time) < timeout_seconds:
            file_status = genai.get_file(name=uploaded_file.name)
            logger.info(f"Consultando estado del archivo {uploaded_file.name}: {file_status.state}")
            
            if file_status.state.name == "ACTIVE":
                logger.info("El archivo está ACTIVO. Procediendo con el análisis.")
                break
            elif file_status.state.name == "FAILED":
                error_message = f"El procesamiento del archivo en Gemini falló. Estado: {file_status.state.name}"
                logger.error(error_message)
                return error_message, None
            
            time.sleep(polling_interval_seconds)
        else: 
            timeout_error = f"Tiempo de espera agotado ({timeout_seconds}s) para el procesamiento del archivo en Gemini. Estado final: {file_status.state.name}"
            logger.error(timeout_error)
            return timeout_error, None

        model_name_to_use = "gemini-1.5-flash-latest"
        model = genai.GenerativeModel(model_name=model_name_to_use)
        
        logger.info("Enviando solicitud de análisis a Gemini...")
        response = model.generate_content([custom_prompt or "Analiza este archivo.", uploaded_file], request_options={'timeout': 300})

        response_text = "".join(part.text for part in response.parts) if hasattr(response, 'parts') else getattr(response, 'text', '')
        if response_text:
            return response_text, model_name_to_use
        elif hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
            return f"Análisis bloqueado: {response.prompt_feedback.block_reason_message}", model_name_to_use
        else:
            return "Respuesta vacía de Gemini.", model_name_to_use

    except Exception as e:
        logger.error(f"Error en el proceso de Gemini para {file_path}: {e}", exc_info=True)
        return f"Error procesando con Gemini: {e}", None

    finally:
        if uploaded_file and hasattr(uploaded_file, 'name'):
            try:
                logger.info(f"Eliminando archivo {uploaded_file.name} de los servidores de Gemini.")
                genai.delete_file(uploaded_file.name)
            except Exception as e_del:
                logger.warning(f"No se pudo eliminar el archivo {uploaded_file.name} de Gemini: {e_del}")

# ===================================================================
# --- API DE GESTIÓN DE PERSONAS ---
# ===================================================================

@app.route('/api/personas_registradas', methods=['POST'])
@login_required
def api_registrar_persona():
    """Crea un nuevo registro de persona, incluyendo su imagen facial de referencia."""
    data = request.form.to_dict()
    imagen_file = request.files.get('imagen_facial')
    if not data.get('nombre') or not imagen_file:
        return jsonify({"error": "Nombre e imagen facial son obligatorios."}), 400
    if not imagen_file.filename or not allowed_file(imagen_file.filename, {'png','jpg','jpeg'}):
        return jsonify({"error": "Tipo de archivo de imagen no permitido."}), 400
    
    data['registrado_por_usuario_id'] = current_user.id
    
    uid = data.get('nombre','unknown').lower().replace(" ","_") + "_" + str(int(time.time()))
    ext = Path(imagen_file.filename).suffix
    fname = werkzeug.utils.secure_filename(f"{uid}{ext}")
    path = os.path.join(app.config['PERSONAS_IMG_REF_FOLDER'], fname)
    
    try: imagen_file.save(path)
    except Exception as e: return jsonify({"error":f"Error al guardar imagen: {e}"}), 500
    
    res, err, code = db_manager.registrar_nueva_persona(data, imagen_filename=fname)
    
    if err:
        if os.path.exists(path): os.remove(path)
        return jsonify({"error": err}), code
        
    face_detector.force_reload_references()
    return jsonify(res), code

@app.route('/api/personas_registradas', methods=['GET'])
@login_required
def api_obtener_personas_por_usuario():
    """Obtiene todas las personas registradas por el usuario actual."""
    personas, err, code = db_manager.obtener_personas_registradas_por_usuario(current_user.id)
    if err: return jsonify({"error": err}), code
    
    for p in personas:
        if p.get('imagen_facial_ref_filename'):
            p['imagen_url'] = url_for('serve_personas_imagen_ref', filename=p['imagen_facial_ref_filename'])
    return jsonify(personas), code

@app.route('/api/personas_registradas/<int:id_persona>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_gestionar_persona_especifica(id_persona):
    """Gestiona (GET, PUT, DELETE) una persona específica, verificando la propiedad."""
    persona, err, code = db_manager.check_persona_ownership(id_persona, current_user.id)
    if err: return jsonify({"error": err}), code
    if not persona: return jsonify({"error": "Acceso denegado o persona no encontrada."}), 403

    if request.method == 'GET':
        if persona.get('imagen_facial_ref_filename'):
            persona['imagen_url'] = url_for('serve_personas_imagen_ref', filename=persona['imagen_facial_ref_filename'])
        return jsonify(persona), 200

    if request.method == 'PUT':
        data = request.form.to_dict()
        nueva_img_file = request.files.get('imagen_facial')
        res, err, code = db_manager.actualizar_persona_registrada(id_persona, data, nueva_img_file, app.config['PERSONAS_IMG_REF_FOLDER'], persona)
        if not err: face_detector.force_reload_references()
        return jsonify({"error": err} if err else res), code

    if request.method == 'DELETE':
        res, err, code = db_manager.eliminar_persona_registrada(id_persona, app.config['PERSONAS_IMG_REF_FOLDER'])
        if not err: face_detector.force_reload_references()
        return jsonify({"error": err} if err else res), code

# ===================================================================
# --- API DE GESTIÓN DE VEHÍCULOS ---
# ===================================================================
@app.route('/api/dropdown/personas_usuario', methods=['GET'])
@login_required
def api_get_personas_usuario_for_dropdown():
    """Obtiene una lista simplificada (ID, nombre) de personas para usar en dropdowns."""
    personas, err, code = db_manager.obtener_nombres_personas_por_usuario(current_user.id)
    if err:
        return jsonify({"error": err}), code
    return jsonify(personas), code
    
@app.route('/api/vehiculos_registrados', methods=['POST'])
@login_required
def api_registrar_vehiculo():
    """Crea un nuevo registro de vehículo."""
    data = request.get_json()
    if not data or not data.get('placa'): return jsonify({"error": "La placa es obligatoria."}), 400

    data['registrado_por_usuario_id'] = current_user.id
    
    res, err, code = db_manager.registrar_nuevo_vehiculo(data)
    return jsonify({"error": err} if err else res), code

@app.route('/api/vehiculos_registrados', methods=['GET'])
@login_required
def api_obtener_vehiculos_por_usuario():
    """Obtiene todos los vehículos registrados por el usuario actual."""
    vehiculos, err, code = db_manager.obtener_vehiculos_registrados_por_usuario(current_user.id)
    return jsonify({"error": err} if err else vehiculos), code

@app.route('/api/vehiculos_registrados/<int:id_vehiculo>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_gestionar_vehiculo_especifico(id_vehiculo):
    """Gestiona (GET, PUT, DELETE) un vehículo específico, verificando la propiedad."""
    vehiculo, err, code = db_manager.check_vehiculo_ownership(id_vehiculo, current_user.id)
    if err: return jsonify({"error": err}), code
    if not vehiculo: return jsonify({"error": "Acceso denegado o vehículo no encontrado."}), 403

    if request.method == 'GET':
        return jsonify(vehiculo), 200

    if request.method == 'PUT':
        data = request.get_json()
        if not data: return jsonify({"error": "Cuerpo JSON requerido."}), 400
        res, err, code = db_manager.actualizar_vehiculo_registrado(id_vehiculo, data)
        return jsonify({"error": err} if err else res), code

    if request.method == 'DELETE':
        res, err, code = db_manager.eliminar_vehiculo_registrado(id_vehiculo)
        return jsonify({"error": err} if err else res), code

# ===================================================================
# --- API DE GESTIÓN DE ZONAS, INCIDENTES Y ALERTAS ---
# ===================================================================
@app.route('/api/zonas', methods=['GET'])
@login_required
def get_zonas_api_por_usuario():
    """Obtiene todas las zonas de vigilancia disponibles."""
    zonas, err, code = db_manager.get_all_zones() 
    if err:
        return jsonify({"error": err}), code
    return jsonify(zonas), code

@app.route('/api/zonas', methods=['POST'])
@login_required
def create_zona_api():
    """Crea una nueva zona de vigilancia."""
    data = request.get_json()
    if not data: return jsonify({"error": "Cuerpo JSON requerido"}), 400
    data['creada_por_usuario_id'] = current_user.id
    res, err, code = db_manager.add_zone(data)
    return jsonify({"error": err} if err else res), code

@app.route('/api/zonas/<int:zona_id>', methods=['PUT', 'DELETE'])
@login_required
def manage_specific_zona_api(zona_id):
    """Gestiona (PUT, DELETE) una zona específica, verificando la propiedad."""
    zona, err, code = db_manager.check_zona_ownership(zona_id, current_user.id)
    if err: return jsonify({"error": err}), code
    if not zona: return jsonify({"error": "Acceso denegado o zona no encontrada."}), 403

    if request.method == 'PUT':
        data = request.get_json()
        if not data: return jsonify({"error": "Cuerpo JSON requerido"}), 400
        res, err, code = db_manager.update_zone_by_id(zona_id, data)
        return jsonify({"error": err} if err else res), code

    if request.method == 'DELETE':
        res, err, code = db_manager.delete_zone_by_id(zona_id)
        return jsonify({"error": err} if err else res), code

@app.route('/api/incidentes', methods=['GET'])
@login_required
def get_incidentes_api_por_usuario():
    """Obtiene una lista de incidentes relevantes para el usuario, con filtros opcionales."""
    filters = request.args.to_dict()
    incidents, error, code = db_manager.get_incidents_for_user(current_user.id, filters)
    if error:
        return jsonify({"error": error}), code
    return jsonify(incidents), code

@app.route('/api/alertas/my_alerts', methods=['GET'])
@login_required
def get_alertas_data_api_por_usuario():
    """Obtiene un resumen estadístico y una lista detallada de las alertas para el usuario."""
    stats, err_stats, _ = db_manager.get_alert_summary_stats_for_user(current_user.id)
    alerts, err_list, _ = db_manager.get_alerts_for_user(current_user.id)
    
    if err_stats or err_list:
        err_msg = (f"Stats error: {err_stats}" if err_stats else "") + (" List error: "+err_list if err_list else "")
        return jsonify({"error": err_msg.strip()}), 500
        
    return jsonify({"stats": stats, "alerts": alerts}), 200

# ===================================================================
# --- ARRANQUE DE LA APLICACIÓN ---
# ===================================================================
if __name__ == '__main__':
    with app.app_context():

        logger.info("Iniciando carga inicial de referencias faciales...")
        face_detector.force_reload_references()
        logger.info(f"Estado de FaceDetector al inicio: {'Listo' if face_detector.is_ready() else 'No Listo'}")
    
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)