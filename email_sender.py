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

from dotenv import load_dotenv 
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import logging
from pathlib import Path
from typing import Union, List, Optional, Dict, Any
from datetime import datetime
import re
import threading

load_dotenv()
logger = logging.getLogger(__name__)

SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
REMITENTE_EMAIL = os.getenv('REMITENTE_EMAIL') 
USUARIO_SMTP = os.getenv('USUARIO_SMTP', REMITENTE_EMAIL)
PASSWORD_SMTP = os.getenv('PASSWORD_SMTP') 

# ===================================================================
# --- GENERACIÓN DINÁMICA DEL CUERPO HTML DEL CORREO ---
# ===================================================================

def _create_html_body(titulo_para_cuerpo_html: str,
                      nivel_alerta_str: str,
                      detalles_dict: Dict[str, Any],
                      timestamp_str: str,
                      nombre_adjunto: Optional[str] = None) -> str:
    """
    Genera un cuerpo de correo electrónico en formato HTML atractivo y responsivo.
    """
    level_colors = {
        "CRITICA": "#DC3545",  
        "ALTA": "#FF8C00",     
        "MEDIA": "#FFC107",    
        "BAJA": "#17A2B8",    
        "INFO": "#007BFF",     
        "DESCONOCIDO": "#6C757D" 
    }
    color_nivel = level_colors.get(nivel_alerta_str.upper(), level_colors["DESCONOCIDO"])

    tipo_deteccion = detalles_dict.get("tipo_deteccion", "desconocido")
    detalles_html_parts = []

    if tipo_deteccion == "placa":
        detalles_html_parts.append(f"<p><strong>Placa Detectada:</strong> {detalles_dict.get('placa_texto', 'N/A')}</p>")
        detalles_html_parts.append(f"<p><strong>Estado del Vehículo en su Registro:</strong> {detalles_dict.get('estado_vehiculo', 'N/A')}</p>")
        detalles_html_parts.append(f"<p><strong>Motivo de Alerta:</strong> {detalles_dict.get('motivo_busqueda_vehiculo', 'No especificado')}</p>")
        conf_ocr = detalles_dict.get('confianza_ocr')
        if isinstance(conf_ocr, (float, int)):
            detalles_html_parts.append(f"<p><strong>Confianza del Reconocimiento:</strong> {conf_ocr*100:.2f}%</p>")

    elif tipo_deteccion == "persona":
        detalles_html_parts.append(f"<p><strong>Nombre Reconocido:</strong> {detalles_dict.get('nombre_reconocido', 'N/A')}</p>")
        detalles_html_parts.append(f"<p><strong>Estado de la Persona en su Registro:</strong> {detalles_dict.get('estado_persona', 'N/A')}</p>")
        detalles_html_parts.append(f"<p><strong>Motivo de Alerta:</strong> {detalles_dict.get('motivo_busqueda', 'No especificado')}</p>")
        conf_rec = detalles_dict.get('confianza_reconocimiento')
        if isinstance(conf_rec, (float, int)):
            detalles_html_parts.append(f"<p><strong>Confianza del Reconocimiento:</strong> {conf_rec*100:.2f}%</p>")

    elif tipo_deteccion == "gemini_analysis":
        gemini_response = detalles_dict.get("gemini_full_response", "Respuesta de Gemini no disponible.")
        gemini_response_html = gemini_response.replace("\n", "<br>")
        gemini_response_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', gemini_response_html)
        detalles_html_parts.append(f"<div><h3>Resumen del Análisis de IA:</h3><div class='gemini-response-box'>{gemini_response_html}</div></div>")

    else: 
        for key, value in detalles_dict.items():
            display_key = key.replace("_", " ").capitalize()
            display_value = str(value) if value is not None else "N/A"
            detalles_html_parts.append(f"<p><strong>{display_key}:</strong> {display_value}</p>")

    detalles_html_str = "".join(detalles_html_parts)

    style_definition = """
        <style>
            body { font-family: 'Segoe UI', 'Roboto', 'Arial', sans-serif; margin: 0; padding: 0; background-color: #f4f7f6; color: #333; }
            .container { max-width: 680px; margin: 20px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.08); border: 1px solid #e0e0e0; }
            .header { background-color: #2c3e50; color: #ffffff; padding: 25px; text-align: center; border-bottom: 5px solid; }
            .header h1 { margin: 0; font-size: 26px; font-weight: 600; letter-spacing: 0.5px; }
            .content { padding: 25px 30px; }
            .alert-banner { padding: 14px 20px; color: #fff !important; border-radius: 8px; font-size: 20px; font-weight: bold; text-transform: uppercase; margin-bottom: 25px; text-align: center; letter-spacing: 1px; }
            .details { margin-top: 20px; padding-top: 20px; border-top: 1px solid #eaeaea; }
            .details p { font-size: 16px; line-height: 1.7; margin: 12px 0; }
            .details strong { color: #34495e; }
            .timestamp { font-size: 14px; color: #7f8c8d; margin-top: 30px; text-align: right; }
            .footer { background-color: #f8f9fa; color: #555; text-align: center; padding: 18px; font-size: 12px; border-top: 1px solid #e0e0e0; }
            .gemini-response-box { background-color: #f1f3f5; border-left: 4px solid #adb5bd; padding: 15px; border-radius: 5px; white-space: pre-wrap; word-break: break-word; font-size: 15px; line-height: 1.7; margin-top: 10px; }
        </style>
    """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {style_definition}
    </head>
    <body>
        <div class="container">
            <div class="header" style="border-bottom-color: {color_nivel};">
                <h1>{titulo_para_cuerpo_html}</h1>
            </div>
            <div class="content">
                <div class="alert-banner" style="background-color: {color_nivel};">
                    Alerta de Nivel {nivel_alerta_str.upper()}
                </div>
                <div class="details">
                    {detalles_html_str}
                </div>
    """
    if nombre_adjunto and tipo_deteccion not in ["gemini_analysis"]:
        html_content += f"<p style='margin-top: 25px; font-style: italic;'><strong>Evidencia Adjunta:</strong> Se ha incluido el archivo '{nombre_adjunto}' para su revisión.</p>"

    html_content += f"""
                <p class="timestamp">Fecha del evento: {timestamp_str}</p>
            </div>
            <div class="footer">
                Mensaje automático generado por el Sistema Vanguard IA © {datetime.now().year}
            </div>
        </div>
    </body>
    </html>
    """
    return html_content

# ===================================================================
# --- LÓGICA DE ENVÍO DE CORREOS (SÍNCRONA Y ASÍNCRONA) ---
# ===================================================================

def send_alert_email_sync(asunto_para_email: str,
                          titulo_para_cuerpo_html: str,
                          nivel_alerta: str,
                          detalles_observacion: Dict[str, Any],
                          timestamp_deteccion_iso: str,
                          destinatarios_finales: List[str],
                          ruta_adjunto: Optional[str] = None):
    if not all([REMITENTE_EMAIL, PASSWORD_SMTP]):
        logger.error("Configuración de correo incompleta (REMITENTE_EMAIL, PASSWORD_SMTP). No se puede enviar el correo.")
        return False
    if not destinatarios_finales:
        logger.warning("No se proporcionaron destinatarios para el correo de alerta. No se enviará.")
        return False

    try:
        dt_obj = datetime.fromisoformat(timestamp_deteccion_iso)
        timestamp_str_display = dt_obj.strftime("%d/%m/%Y a las %H:%M:%S")
    except (ValueError, TypeError):
        timestamp_str_display = timestamp_deteccion_iso

    nombre_adjunto = Path(ruta_adjunto).name if ruta_adjunto and os.path.exists(ruta_adjunto) else None

    cuerpo_html = _create_html_body(titulo_para_cuerpo_html, nivel_alerta, detalles_observacion, timestamp_str_display, nombre_adjunto)

    msg = MIMEMultipart('related')
    msg['From'] = f"Vanguard IA <{REMITENTE_EMAIL}>"
    msg['To'] = ", ".join(destinatarios_finales)
    msg['Subject'] = asunto_para_email

    msg_alternative = MIMEMultipart('alternative')
    msg.attach(msg_alternative)

    msg_alternative.attach(MIMEText(cuerpo_html, 'html', 'utf-8'))

    if nombre_adjunto and ruta_adjunto:
        try:
            with open(ruta_adjunto, "rb") as attachment_file:
                ext = Path(ruta_adjunto).suffix.lower()
                maintype, subtype = "application", "octet-stream" 
                if ext in ['.jpg', '.jpeg']: maintype, subtype = "image", "jpeg"
                elif ext == '.png': maintype, subtype = "image", "png"
                elif ext == '.mp4': maintype, subtype = "video", "mp4"

                part = MIMEBase(maintype, subtype)
                part.set_payload(attachment_file.read())

            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename=\"{nombre_adjunto}\"")
            msg.attach(part)
            logger.info(f"Archivo '{nombre_adjunto}' adjuntado correctamente al correo.")
        except Exception as e_attach:
            logger.error(f"Error al intentar adjuntar el archivo {ruta_adjunto}: {e_attach}")

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.set_debuglevel(0) 
            server.starttls()
            server.login(USUARIO_SMTP, PASSWORD_SMTP)
            server.sendmail(REMITENTE_EMAIL, destinatarios_finales, msg.as_string())
        logger.info(f"Correo de alerta enviado exitosamente a: {', '.join(destinatarios_finales)}")
        return True
    except smtplib.SMTPAuthenticationError as e_auth:
        logger.critical(f"Error CRÍTICO de autenticación SMTP. Revisa las credenciales (USUARIO_SMTP, PASSWORD_SMTP). Error: {e_auth}")
        return False
    except Exception as e:
        logger.error(f"Error general al enviar correo a {destinatarios_finales}: {e}", exc_info=True)
        return False

def send_alert_email_threaded_wrapper(asunto_base: str,
                                      nivel_alerta: str,
                                      detalles_observacion: Dict[str, Any],
                                      timestamp_deteccion_iso: str,
                                      destinatarios: Union[str, List[str]],
                                      ruta_adjunto: Optional[str] = None):
    if not destinatarios:
        logger.error("Llamada a send_alert_email_threaded_wrapper sin destinatarios. No se enviará correo.")
        return

    destinatarios_lista = [destinatarios] if isinstance(destinatarios, str) else list(destinatarios)

    asunto_completo = f"🚨 {asunto_base} - Nivel {nivel_alerta.upper()}"
    titulo_html = asunto_base 

    email_job_thread = threading.Thread(
        target=send_alert_email_sync,
        args=(
            asunto_completo,
            titulo_html,
            nivel_alerta,
            detalles_observacion,
            timestamp_deteccion_iso,
            destinatarios_lista,
            ruta_adjunto
        )
    )
    email_job_thread.start()
    logger.info(f"Hilo de envío de correo iniciado para el asunto '{asunto_completo}' a '{', '.join(destinatarios_lista)}'.")

# ===================================================================
# --- BLOQUE DE EJECUCIÓN PARA PRUEBAS Y DEMOSTRACIÓN ---
# ===================================================================

if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s %(message)s')

    if not all([REMITENTE_EMAIL, PASSWORD_SMTP]):
        print("\nERROR: Las variables de entorno REMITENTE_EMAIL y PASSWORD_SMTP deben estar configuradas para la prueba.")
        print("Asegúrate de tener un archivo .env en la misma carpeta con estas variables.\n")
    else:
        print("Probando el módulo de envío de correos...")

        test_recipient = "correo_de_prueba@ejemplo.com"
        print(f"Se intentará enviar correos de prueba a: {test_recipient}\n")


        test_obs_persona = {
            "tipo_deteccion": "persona",
            "nombre_reconocido": "Carlos Sospechoso",
            "estado_persona": "Sospechoso",
            "motivo_busqueda": "Actitud evasiva en zona restringida",
            "confianza_reconocimiento": 0.88,
        }
        send_alert_email_threaded_wrapper(
            asunto_base="Persona Sospechosa Detectada",
            nivel_alerta="MEDIA",
            detalles_observacion=test_obs_persona,
            timestamp_deteccion_iso=datetime.now().isoformat(),
            destinatarios=test_recipient,
            ruta_adjunto=None 
        )
        print("-> Hilo de correo para 'Persona Sospechosa' iniciado.")

        import time
        time.sleep(5)

        test_image_path = "evidencia_test.jpg"
        if not os.path.exists(test_image_path):
            try:
                import numpy as np
                import cv2
                dummy_image = np.zeros((200, 400, 3), dtype=np.uint8) + 50
                cv2.putText(dummy_image, "PLACA: XYZ-123", (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 0), 3)
                cv2.imwrite(test_image_path, dummy_image)
                print(f"   (Imagen de prueba '{test_image_path}' creada para el adjunto)")
            except Exception as e:
                print(f"   (Advertencia: No se pudo crear la imagen de prueba: {e}. El adjunto podría fallar.)")

        test_obs_vehiculo = {
            "tipo_deteccion": "placa",
            "placa_texto": "XYZ-123",
            "estado_vehiculo": "Robado",
            "motivo_busqueda_vehiculo": "Reporte de robo #55432",
            "confianza_ocr": 0.97,
        }
        send_alert_email_threaded_wrapper(
            asunto_base="Vehículo Robado Detectado",
            nivel_alerta="CRITICA",
            detalles_observacion=test_obs_vehiculo,
            timestamp_deteccion_iso=datetime.now().isoformat(),
            destinatarios=[test_recipient, "otro_correo@ejemplo.com"],
            ruta_adjunto=test_image_path if os.path.exists(test_image_path) else None
        )
        print("-> Hilo de correo para 'Vehículo Robado' iniciado.")

        print("\nPruebas finalizadas. Revisa la consola para logs y las bandejas de entrada de los correos de prueba.")