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

document.addEventListener('DOMContentLoaded', () => {
    const incidentsGrid = document.getElementById('incidentsGrid');
    const openReportIncidentModalBtn = document.getElementById('openReportIncidentModalBtn');
    const incidentModal = document.getElementById('incidentModal');
    const closeIncidentModalBtn = document.getElementById('closeIncidentModalBtn');
    const cancelIncidentModalBtn = document.getElementById('cancelIncidentModalBtn');
    const incidentForm = document.getElementById('incidentForm');
    const modalIncidentTitle = document.getElementById('modalIncidentTitle');
    const incidentIdInput = document.getElementById('incidentId');
    const incidentZoneSelect = document.getElementById('incidentZone');
    const filterZoneSelect = document.getElementById('filterZone');
    const incidentStatusSelect = document.getElementById('incidentStatus'); 
    const statsIncidentsToday = document.getElementById('stats-incidents-today');
    const statsIncidentsPending = document.getElementById('stats-incidents-pending');
    const statsIncidentsVerifiedPercentage = document.getElementById('stats-incidents-verified_percentage');
    const filterForm = document.getElementById('filterForm');
    const resetFiltersBtn = document.getElementById('resetFiltersBtn');
    const API_INCIDENTS_URL = '/api/incidentes';
    const API_ZONES_URL = '/api/zonas'; 
    let currentUserId = 6; 
    async function loadZonesIntoSelects() {
        try {
            const response = await fetch(API_ZONES_URL); 
            if (!response.ok) throw new Error('Error al cargar zonas para selects');
            const zones = await response.json();
    
            const populateSelect = (selectElement) => {
                if (!selectElement) return;
                
                const firstOptionValue = selectElement.options[0] ? selectElement.options[0].value : "";
                const firstOptionText = selectElement.options[0] ? selectElement.options[0].textContent : "Seleccione...";
                
                selectElement.innerHTML = ''; 
                const defaultOption = document.createElement('option');
                defaultOption.value = ""; 
                defaultOption.textContent = firstOptionText; 
                defaultOption.disabled = true; 
                defaultOption.selected = true; 
                selectElement.appendChild(defaultOption);
    
                zones.forEach(zone => {
                    const option = document.createElement('option');
                    option.value = zone.id_zona; 
                    option.textContent = zone.nombre_zona;
                    selectElement.appendChild(option);
                });
            };
            
            populateSelect(incidentZoneSelect); 

            if (filterZoneSelect) {
                filterZoneSelect.innerHTML = '<option value="">Todas las Zonas</option>'; 
                 zones.forEach(zone => {
                    const option = document.createElement('option');
                    option.value = zone.id_zona;
                    option.textContent = zone.nombre_zona;
                    filterZoneSelect.appendChild(option);
                });
            }
    
        } catch (error) {
            console.error('Error populando selects de zonas:', error);
            if(incidentZoneSelect) incidentZoneSelect.innerHTML = '<option value="">Error al cargar zonas</option>';
            if(filterZoneSelect) filterZoneSelect.innerHTML = '<option value="">Error al cargar zonas</option>';
        }
    }

    function openIncidentModal(mode = 'add', incidentData = null) {
        incidentForm.reset();
        incidentIdInput.value = '';
        document.getElementById('incidentConfidence').value = '0.75';
        incidentStatusSelect.closest('.form-group').style.display = 'none'; 

        if (mode === 'edit' && incidentData) {
            modalIncidentTitle.textContent = 'Editar Incidente';
            incidentIdInput.value = incidentData.id_incidente;
            document.getElementById('incidentType').value = incidentData.tipo || '';
            document.getElementById('incidentZone').value = incidentData.zona_afectada || '';
            document.getElementById('incidentDescription').value = incidentData.descripcion || '';
            document.getElementById('incidentCoordinates').value = incidentData.coordenadas_wkt || '';
            document.getElementById('incidentConfidence').value = incidentData.grado_confianza !== null ? parseFloat(incidentData.grado_confianza).toFixed(2) : '0.75';
            incidentStatusSelect.value = incidentData.estado_incidente || 'Pendiente';
            incidentStatusSelect.closest('.form-group').style.display = 'block'; 
        } else {
            modalIncidentTitle.textContent = 'Reportar Nuevo Incidente';
        }
        incidentModal.classList.add('visible');
    }

    function closeIncidentModal() {
        incidentModal.classList.remove('visible');
    }

    if (openReportIncidentModalBtn) openReportIncidentModalBtn.addEventListener('click', () => openIncidentModal('add'));
    if (closeIncidentModalBtn) closeIncidentModalBtn.addEventListener('click', closeIncidentModal);
    if (cancelIncidentModalBtn) cancelIncidentModalBtn.addEventListener('click', closeIncidentModal);
    window.addEventListener('click', (event) => { if (event.target === incidentModal) closeIncidentModal(); });

    async function fetchIncidents(filters = {}) {
        try {
            const queryParams = new URLSearchParams(filters).toString();
            const url = queryParams ? `${API_INCIDENTS_URL}?${queryParams}` : API_INCIDENTS_URL;

            const response = await fetch(url);
            if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
            const incidents = await response.json();
            renderIncidents(incidents);
            updateIncidentStats(incidents);
        } catch (error) {
            console.error('Error al cargar incidentes:', error);
            if(incidentsGrid) incidentsGrid.innerHTML = `<div class="card incident-card placeholder-card" style="text-align: center; padding: 40px; grid-column: 1 / -1;">Error al cargar incidentes.</div>`;
        }
    }

    function renderIncidents(incidents) {
        if(!incidentsGrid) return;
        incidentsGrid.innerHTML = '';
        if (incidents.length === 0) {
            incidentsGrid.innerHTML = `<div class="card incident-card placeholder-card" style="text-align: center; padding: 40px; grid-column: 1 / -1;">No se encontraron incidentes con los filtros aplicados.</div>`;
            return;
        }
        incidents.forEach(incident => {
            const estadoClass = incident.estado_incidente ? incident.estado_incidente.toLowerCase().replace(/\s+/g, '_') : 'desconocido';
            const card = `
                <div class="card incident-card" data-id="${incident.id_incidente}">
                    <div class="incident-card-header">
                        <h3 class="incident-card-type">${incident.tipo}</h3>
                        <span class="incident-status ${estadoClass}">${incident.estado_incidente || 'N/A'}</span>
                    </div>
                    <div class="incident-card-body">
                        <p>${incident.descripcion || 'Sin descripción detallada.'}</p>
                        <p class="detail"><strong>Zona:</strong> ${incident.nombre_zona || 'No especificada'}</p>
                        <p class="detail"><strong>Coordenadas:</strong> ${incident.coordenadas_wkt || 'N/A'}</p>
                        <p class="detail"><strong>Confianza:</strong> ${incident.grado_confianza !== null ? (parseFloat(incident.grado_confianza) * 100).toFixed(0) + '%' : 'N/A'}</p>
                        <p class="detail"><strong>Reportado:</strong> ${new Date(incident.fecha_reporte).toLocaleString()}</p>
                        ${incident.fecha_verificacion ? `<p class="detail"><strong>Verificado:</strong> ${new Date(incident.fecha_verificacion).toLocaleString()}</p>` : ''}
                        <p class="detail"><strong>Reportado por:</strong> Usuario ID ${incident.id_usuario || 'Sistema'}</p>
                    </div>
                    <div class="incident-card-actions">
                    </div>
                </div>
            `;
            incidentsGrid.insertAdjacentHTML('beforeend', card);
        });

        document.querySelectorAll('.edit-incident-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const incidentId = e.currentTarget.dataset.id;

                fetch(`${API_INCIDENTS_URL}/${incidentId}`)
                    .then(res => {
                        if (!res.ok) throw new Error('Incidente no encontrado o error de servidor');
                        return res.json();
                    })
                    .then(incidentToEdit => {
                        if (incidentToEdit) openIncidentModal('edit', incidentToEdit);
                    })
                    .catch(err => {
                        alert('Error al cargar datos del incidente para editar: ' + err.message);
                        console.error(err);
                    });
            });
        });

    }

    function updateIncidentStats(incidents) {
        const today = new Date().toISOString().slice(0, 10);
        const incidentsToday = incidents.filter(inc => inc.fecha_reporte.startsWith(today)).length;
        const incidentsPending = incidents.filter(inc => inc.estado_incidente && inc.estado_incidente.toLowerCase() === 'pendiente').length;
        const verifiedIncidents = incidents.filter(inc => inc.estado_incidente && inc.estado_incidente.toLowerCase() === 'verificado').length;
        const totalManageableIncidents = incidents.filter(inc => ['pendiente', 'en investigación', 'verificado', 'falso positivo', 'resuelto'].includes(inc.estado_incidente?.toLowerCase())).length;
        const verifiedPercentage = totalManageableIncidents > 0 ? ((verifiedIncidents / totalManageableIncidents) * 100).toFixed(0) : 0;


        if(statsIncidentsToday) statsIncidentsToday.textContent = incidentsToday;
        if(statsIncidentsPending) statsIncidentsPending.textContent = incidentsPending;
        if(statsIncidentsVerifiedPercentage) statsIncidentsVerifiedPercentage.textContent = `${verifiedPercentage}%`;
    }


    if (incidentForm) {
        incidentForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const formData = new FormData(incidentForm);
            const incidentData = Object.fromEntries(formData.entries());
            const id = incidentIdInput.value;
    
            incidentData.id_usuario = currentUserId;
    
            if (!incidentData.tipo || !incidentData.zona_afectada || !incidentData.descripcion) {
                alert('Tipo, Zona y Descripción son campos obligatorios.');
                return;
            }
            if (incidentData.coordenadas && incidentData.coordenadas.trim() !== "" && !incidentData.coordenadas.toUpperCase().startsWith('POINT(')) {
                alert('Formato de coordenadas de punto no válido. Debe empezar con POINT(... o estar vacío.');
                return;
            }

            const confidenceStr = incidentData.grado_confianza.trim();
            if (confidenceStr === "") {
                incidentData.grado_confianza = null;
            } else {
                const confidenceVal = parseFloat(confidenceStr);
                if (isNaN(confidenceVal) || confidenceVal < 0 || confidenceVal > 1) {
                    alert('La confianza debe ser un número entre 0.0 y 1.0, o dejarse vacío.');
                    return;
                }
                incidentData.grado_confianza = confidenceVal.toFixed(2);
            }

            if (incidentData.coordenadas && incidentData.coordenadas.trim() === "") {
                incidentData.coordenadas = null; 
            }
    
    
            try {
                let response;
                const fetchOptions = {
                    method: id ? 'PUT' : 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(incidentData)
                };
                const url = id ? `${API_INCIDENTS_URL}/${id}` : API_INCIDENTS_URL;
                
                response = await fetch(url, fetchOptions);
                
                const responseData = await response.json();
    
                if (!response.ok) {

                    throw new Error(responseData.error || `Error HTTP: ${response.status}`);
                }
                
                alert(responseData.message || (id ? 'Incidente actualizado' : 'Incidente reportado'));
                closeIncidentModal();
                fetchIncidents();
            } catch (error) { 
                console.error('Error al guardar incidente:', error);

                alert(`Error al guardar incidente: ${error.message}`);
            }
        });
    }

    loadZonesIntoSelects();
    fetchIncidents(); 
});