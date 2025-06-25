/*
██╗   ██╗ █████╗ ███╗   ██╗ ██████╗ ██╗   ██╗ █████╗ ██████╗ ██████╗ 
██║   ██║██╔══██╗████╗  ██║██╔════╝ ██║   ██║██╔══██╗██╔══██╗██╔══██╗
██║   ██║███████║██╔██╗ ██║██║  ███╗██║   ██║███████║██████╔╝██║  ██║
╚██╗ ██╔╝██╔══██║██║╚██╗██║██║   ██║██║   ██║██╔══██║██╔══██╗██║  ██║
 ╚████╔╝ ██║  ██║██║ ╚████║╚██████╔╝╚██████╔╝██║  ██║██║  ██║██████╔╝
  ╚═══╝  ╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ 

                              ██╗ █████╗ 
                              ██║██╔══██╗
                              ██║███████║
                              ██║██╔══██║
                              ██║██║  ██║
                              ╚═╝╚═╝  ╚═╝
*/

CREATE DATABASE IF NOT EXISTS vanguard CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE vanguard;

CREATE TABLE IF NOT EXISTS personal_administrativo (
    id_usuario INT PRIMARY KEY AUTO_INCREMENT,
    nombre_completo VARCHAR(200) NOT NULL,
    apellidos VARCHAR(200) NOT NULL,
    correo VARCHAR(100) UNIQUE NOT NULL, 
    numero_celular VARCHAR(20) NOT NULL,
    hash_password VARCHAR(255) NOT NULL, 
    rol ENUM('admin', 'operador', 'supervisor', 'analista') DEFAULT 'operador' NOT NULL,
    cargo VARCHAR(100),
    departamento VARCHAR(100),
    fecha_ingreso DATE,
    activo BOOLEAN DEFAULT TRUE,
    permisos JSON, 
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    creado_por_usuario_id INT,
    FOREIGN KEY (creado_por_usuario_id) REFERENCES personal_administrativo(id_usuario) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS personas_registradas (
    id_persona INT PRIMARY KEY AUTO_INCREMENT,
    nombre VARCHAR(150) NOT NULL,
    identificacion VARCHAR(30) UNIQUE,
    direccion TEXT,
    contacto JSON,
    imagen_facial_ref_filename VARCHAR(255) UNIQUE,
    estado_persona ENUM('No asignado', 'Buscado', 'Sospechoso', 'Restringido', 'Autorizado') DEFAULT 'No asignado' NOT NULL,
    motivo_busqueda TEXT NULL,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    registrado_por_usuario_id INT,
    FOREIGN KEY (registrado_por_usuario_id) REFERENCES personal_administrativo(id_usuario) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS vehiculos_registrados (
    id_vehiculo INT PRIMARY KEY AUTO_INCREMENT,
    placa VARCHAR(20) UNIQUE NOT NULL,
    marca VARCHAR(50),
    modelo VARCHAR(50),
    color VARCHAR(50),
    id_propietario INT,
    notas TEXT,
    estado_vehiculo ENUM('Autorizado', 'Buscado', 'Sospechoso', 'Robado', 'Otro') DEFAULT 'Autorizado' NOT NULL,
    motivo_busqueda_vehiculo TEXT NULL,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    registrado_por_usuario_id INT,
    FOREIGN KEY (id_propietario) REFERENCES personas_registradas(id_persona) ON DELETE SET NULL,
    FOREIGN KEY (registrado_por_usuario_id) REFERENCES personal_administrativo(id_usuario) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS zonas_vigiladas (
    id_zona INT PRIMARY KEY AUTO_INCREMENT,
    nombre_zona VARCHAR(100) NOT NULL UNIQUE, 
    descripcion TEXT,
    coordenadas_poligono POLYGON,
    coordenadas_centro POINT,
    estado VARCHAR(20) DEFAULT 'activa',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    creada_por_usuario_id INT,
    FOREIGN KEY (creada_por_usuario_id) REFERENCES personal_administrativo(id_usuario) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS permisos_zona_usuario (
    id_permiso INT PRIMARY KEY AUTO_INCREMENT,
    id_usuario INT NOT NULL,
    id_zona INT NOT NULL,
    rol_acceso ENUM('lectura', 'escritura', 'admin') DEFAULT 'lectura',
    fecha_asignacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_usuario_zona (id_usuario, id_zona),
    FOREIGN KEY (id_usuario) REFERENCES personal_administrativo(id_usuario) ON DELETE CASCADE,
    FOREIGN KEY (id_zona) REFERENCES zonas_vigiladas(id_zona) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS historial_incidentes (
    id_incidente INT PRIMARY KEY AUTO_INCREMENT,
    id_usuario_reporta INT NULL,
    tipo_incidente VARCHAR(50) NOT NULL,
    descripcion TEXT,
    coordenadas_incidente POINT,
    estado_incidente VARCHAR(50) DEFAULT 'Pendiente',
    grado_confianza_deteccion DECIMAL(5,2),
    id_zona_afectada INT,
    fecha_reporte TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_incidente DATETIME,
    fecha_verificacion DATETIME,
    verificado_por_usuario_id INT,
    FOREIGN KEY (id_usuario_reporta) REFERENCES personal_administrativo(id_usuario) ON DELETE SET NULL,
    FOREIGN KEY (verificado_por_usuario_id) REFERENCES personal_administrativo(id_usuario) ON DELETE SET NULL,
    FOREIGN KEY (id_zona_afectada) REFERENCES zonas_vigiladas(id_zona) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS alertas (
    id_alerta INT PRIMARY KEY AUTO_INCREMENT,
    id_incidente INT NOT NULL,
    nivel_alerta VARCHAR(20) NOT NULL,
    id_zona_impactada INT,
    observaciones JSON,
    fecha_alerta DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_respuesta DATETIME,
    respondida_por_usuario_id INT,
    FOREIGN KEY (id_incidente) REFERENCES historial_incidentes(id_incidente) ON DELETE CASCADE,
    FOREIGN KEY (id_zona_impactada) REFERENCES zonas_vigiladas(id_zona) ON DELETE SET NULL,
    FOREIGN KEY (respondida_por_usuario_id) REFERENCES personal_administrativo(id_usuario) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS alertas_destinatarios (
    id_alerta INT NOT NULL,
    id_usuario_destinatario INT NOT NULL,
    estado_notificacion ENUM('pendiente', 'enviado', 'visto', 'fallido') DEFAULT 'pendiente',
    fecha_envio TIMESTAMP NULL,
    PRIMARY KEY (id_alerta, id_usuario_destinatario),
    FOREIGN KEY (id_alerta) REFERENCES alertas(id_alerta) ON DELETE CASCADE,
    FOREIGN KEY (id_usuario_destinatario) REFERENCES personal_administrativo(id_usuario) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS acciones_sistema (
    id_log INT PRIMARY KEY AUTO_INCREMENT,
    id_usuario_accion INT,
    tipo_accion VARCHAR(100) NOT NULL,
    descripcion_detallada TEXT,
    ip_origen VARCHAR(45),
    entidad_afectada VARCHAR(50),
    id_entidad_afectada INT,
    payload_request JSON,
    fecha_accion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_usuario_accion) REFERENCES personal_administrativo(id_usuario) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS rostros_detectados (
    id_deteccion_rostro INT PRIMARY KEY AUTO_INCREMENT,
    id_persona_identificada INT NULL,
    nombre_detectado VARCHAR(150),
    imagen_deteccion_path VARCHAR(255),
    coordenadas_deteccion_frame JSON,
    confianza_reconocimiento DECIMAL(5,4),
    distancia_descriptor DECIMAL(8,6),
    fecha_deteccion TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    id_incidente_asociado INT NULL,
    id_zona_deteccion INT NULL,
    media_source_path VARCHAR(255),
    FOREIGN KEY (id_persona_identificada) REFERENCES personas_registradas(id_persona) ON DELETE SET NULL,
    FOREIGN KEY (id_incidente_asociado) REFERENCES historial_incidentes(id_incidente) ON DELETE SET NULL,
    FOREIGN KEY (id_zona_deteccion) REFERENCES zonas_vigiladas(id_zona) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS placas_detectadas (
    id_deteccion_placa INT PRIMARY KEY AUTO_INCREMENT,
    id_incidente_asociado INT NULL,
    texto_placa VARCHAR(20) NOT NULL,
    imagen_deteccion_path VARCHAR(255),
    confianza_ocr DECIMAL(5,4),
    fecha_deteccion TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    id_zona_deteccion INT NULL,
    media_source_path VARCHAR(255),
    id_vehiculo_registrado_asociado INT NULL,
    FOREIGN KEY (id_incidente_asociado) REFERENCES historial_incidentes(id_incidente) ON DELETE SET NULL,
    FOREIGN KEY (id_zona_deteccion) REFERENCES zonas_vigiladas(id_zona) ON DELETE SET NULL,
    FOREIGN KEY (id_vehiculo_registrado_asociado) REFERENCES vehiculos_registrados(id_vehiculo) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS eventos_audio (
    id_evento_audio INT PRIMARY KEY AUTO_INCREMENT,
    id_incidente INT NOT NULL,
    descripcion_corta TEXT,
    transcripcion_completa TEXT,
    duracion_segundos FLOAT,
    confianza_deteccion_emergencia DECIMAL(5,4),
    respuesta_llm VARCHAR(50),
    modelo_llm_usado VARCHAR(50),
    fecha_evento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    media_source_path VARCHAR(255),
    FOREIGN KEY (id_incidente) REFERENCES historial_incidentes(id_incidente) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS eventos_video_referencia (
    id_evento_video INT PRIMARY KEY AUTO_INCREMENT,
    id_incidente INT NOT NULL,
    archivo_video_path VARCHAR(255) NOT NULL,
    descripcion_relevancia TEXT,
    timestamp_inicio_relevante TIME,
    timestamp_fin_relevante TIME,
    fecha_asociacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_incidente) REFERENCES historial_incidentes(id_incidente) ON DELETE CASCADE
);

CREATE INDEX idx_personas_nombre ON personas_registradas(nombre);
CREATE INDEX idx_personas_estado ON personas_registradas(estado_persona);
CREATE INDEX idx_personal_correo ON personal_administrativo(correo);
CREATE INDEX idx_personal_activo ON personal_administrativo(activo);
CREATE INDEX idx_vehiculos_placa ON vehiculos_registrados(placa);
CREATE INDEX idx_vehiculos_estado ON vehiculos_registrados(estado_vehiculo);
CREATE INDEX idx_rostros_detectados_fecha ON rostros_detectados(fecha_deteccion);
CREATE INDEX idx_placas_detectadas_fecha ON placas_detectadas(fecha_deteccion);
CREATE INDEX idx_placas_detectadas_texto ON placas_detectadas(texto_placa);
