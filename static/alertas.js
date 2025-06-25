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

document.addEventListener('DOMContentLoaded', function() {
    loadAlertData();
});

function loadAlertData() {
    fetch('/api/alertas/my_alerts')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Error HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                console.error('Error fetching alert data:', data.error);
                displayErrorMessage('Error al cargar datos de alertas.');
                return;
            }
            populateStats(data.stats);
            populateAlertsCards(data.alerts);
        })
        .catch(error => {
            console.error('Error en la petición de alertas:', error);
            displayErrorMessage(`No se pudieron cargar las alertas: ${error.message}`);
        });
}

function populateStats(stats) {
    document.getElementById('stat-total-alerts').textContent = stats.total_alerts || 0;
    document.getElementById('stat-critical-alerts').textContent = stats.critica || 0;
    document.getElementById('stat-high-alerts').textContent = stats.alta || 0;
    document.getElementById('stat-medium-alerts').textContent = stats.media || 0;
    document.getElementById('stat-low-alerts').textContent = stats.baja || 0;
}

function populateAlertsCards(alerts) {
    const container = document.getElementById('alerts-cards-container');
    container.innerHTML = ''; 

    if (!alerts || alerts.length === 0) {
        const noData = document.createElement('div');
        noData.className = 'no-data-text';
        noData.textContent = 'No hay alertas para mostrar.';
        container.appendChild(noData);
        return;
    }

    alerts.forEach(alert => {
        const card = document.createElement('div');
        card.className = 'card alert-card'; 
        const obsObj = alert.observaciones;

        const isObsObjectValid = obsObj && typeof obsObj === 'object' && !Array.isArray(obsObj);
        
        const tipoDeteccion = isObsObjectValid ? (obsObj.tipo_deteccion || 'desconocido') : 'desconocido';
        const analysisType = isObsObjectValid && obsObj.analysis_type ? obsObj.analysis_type.toLowerCase().replace(/ /g, '_') : '';
        
        let iconClass = 'fas fa-exclamation-triangle alert-icon-default'; 
        let cardTitleText = `Alerta ID: ${alert.id_alerta}`;

        if (tipoDeteccion === 'persona') {
            iconClass = 'fas fa-user-shield alert-icon-persona';
            cardTitleText = `Persona Detectada <span class="alert-id">(ID: ${alert.id_alerta})</span>`;
        } else if (tipoDeteccion === 'placa') {
            iconClass = 'fas fa-car-side alert-icon-placa';
            cardTitleText = `Placa Detectada <span class="alert-id">(ID: ${alert.id_alerta})</span>`;
        } else if (tipoDeteccion === 'gemini_analysis') {
            if (analysisType.includes('audio_contexto')) {
                iconClass = 'fas fa-microphone-alt alert-icon-gemini_analysis_audio_contexto';
                cardTitleText = `Análisis Audio (Gemini) <span class="alert-id">(ID: ${alert.id_alerta})</span>`;
            } else { 
                iconClass = 'fas fa-brain alert-icon-gemini_analysis_video';
                cardTitleText = `Análisis General (Gemini) <span class="alert-id">(ID: ${alert.id_alerta})</span>`;
            }
        }

        const cardHeader = document.createElement('div');
        cardHeader.className = 'alert-card-header';
        
        const iconElement = document.createElement('i');
        iconElement.className = `${iconClass} alert-card-icon`;
        
        const titleElement = document.createElement('h3');
        titleElement.className = 'alert-card-title-id';
        titleElement.innerHTML = cardTitleText;

        const levelBadge = document.createElement('span');
        levelBadge.className = `alert-level-badge alert-level-${alert.nivel_alerta.toLowerCase()}`;
        levelBadge.textContent = alert.nivel_alerta;

        cardHeader.appendChild(iconElement);
        cardHeader.appendChild(titleElement);
        cardHeader.appendChild(levelBadge);

        const cardBody = document.createElement('div');
        cardBody.className = 'alert-card-body';

        if (isObsObjectValid) {

            if (tipoDeteccion === 'persona') {
                cardBody.innerHTML += `<div class="alert-detail"><strong>Nombre:</strong> ${obsObj.nombre_reconocido || 'N/A'}</div>`;
                cardBody.innerHTML += `<div class="alert-detail"><strong>Estado:</strong> ${obsObj.estado_persona || 'N/A'}</div>`;
                if (obsObj.motivo_busqueda) {
                    cardBody.innerHTML += `<div class="alert-detail"><strong>Motivo:</strong> ${obsObj.motivo_busqueda}</div>`;
                }
                cardBody.innerHTML += `<div class="alert-detail"><strong>Confianza:</strong> ${obsObj.confianza_reconocimiento ? (obsObj.confianza_reconocimiento * 100).toFixed(1) + '%' : 'N/A'}</div>`;
            } else if (tipoDeteccion === 'placa') {
                cardBody.innerHTML += `<div class="alert-detail"><strong>Placa:</strong> ${obsObj.placa_texto || 'N/A'}</div>`;
                cardBody.innerHTML += `<div class="alert-detail"><strong>Estado Vehículo:</strong> ${obsObj.estado_vehiculo || 'N/A'}</div>`;
                 if (obsObj.motivo_busqueda_vehiculo) {
                    cardBody.innerHTML += `<div class="alert-detail"><strong>Motivo:</strong> ${obsObj.motivo_busqueda_vehiculo}</div>`;
                }
                cardBody.innerHTML += `<div class="alert-detail"><strong>Confianza OCR:</strong> ${obsObj.confianza_ocr ? (obsObj.confianza_ocr * 100).toFixed(1) + '%' : 'N/A'}</div>`;
            } else if (tipoDeteccion === 'gemini_analysis') {
                cardBody.innerHTML += `<div class="alert-detail"><strong>Modelo:</strong> ${obsObj.gemini_model || 'N/A'}</div>`;
                if (obsObj.triggered_keywords && obsObj.triggered_keywords.length > 0) {
                    cardBody.innerHTML += `<div class="alert-detail"><strong>Palabras Clave:</strong> ${obsObj.triggered_keywords.join(', ')}</div>`;
                }
                if (obsObj.gemini_response_snippet) {
                    let snippet = obsObj.gemini_response_snippet;
                    const alertaMatch = snippet.match(/Alerta🚨🚨🚨(.*)/i);
                    if (alertaMatch && alertaMatch[1]) {
                        snippet = `Alerta: ${alertaMatch[1].trim()}`;
                    } else {
                        snippet = snippet.replace(/^Análisis de Gemini:\s*/i, '')
                                         .replace(/^\*\*Análisis del Video:\*\*\s*/i, '')
                                         .replace(/^\*\*Análisis General del Archivo \(.*?\)\*\*:\s*/i, '')
                                         .replace(/^\*\*Transcripción:\*\*\s*/i, '');
                    }
                    const obsTextDiv = document.createElement('div');
                    obsTextDiv.className = 'alert-card-observation-text';
                    obsTextDiv.textContent = snippet.substring(0, 250) + (snippet.length > 250 ? '...' : '');
                    cardBody.appendChild(obsTextDiv);
                }
            } else { 
                const obsTextDiv = document.createElement('div');
                obsTextDiv.className = 'alert-card-observation-text';

                obsTextDiv.textContent = JSON.stringify(obsObj, null, 2);
                cardBody.appendChild(obsTextDiv);
            }
            if (obsObj.media_source) {
                 cardBody.innerHTML += `<div class="alert-detail" style="font-size:0.8em; opacity:0.7; margin-top:8px;"><strong>Fuente:</strong> ${obsObj.media_source.split(/[\\/]/).pop()}</div>`;
            }

        } else {
            const obsTextDiv = document.createElement('div');
            obsTextDiv.className = 'alert-card-observation-text';
            obsTextDiv.textContent = String(alert.observaciones) || 'No hay detalles de observación.';
            cardBody.appendChild(obsTextDiv);
        }

        const cardFooter = document.createElement('div');
        cardFooter.className = 'alert-card-footer';
        cardFooter.textContent = `Fecha: ${formatDate(alert.fecha_alerta)}`;

        card.appendChild(cardHeader);
        card.appendChild(cardBody);
        card.appendChild(cardFooter);
        container.appendChild(card);
    });
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        const date = new Date(dateString);
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        return `${day}/${month}/${year} ${hours}:${minutes}`; 
    } catch (e) {
        console.error("Error formateando fecha:", dateString, e);
        return dateString;
    }
}

function displayErrorMessage(message) {
    const container = document.getElementById('alerts-cards-container');
    if (container) {
        container.innerHTML = `<div class="no-data-text">${message}</div>`;
    }
    document.getElementById('stat-total-alerts').textContent = '-';
    document.getElementById('stat-critical-alerts').textContent = '-';
    document.getElementById('stat-high-alerts').textContent = '-';
    document.getElementById('stat-medium-alerts').textContent = '-';
    document.getElementById('stat-low-alerts').textContent = '-';
}