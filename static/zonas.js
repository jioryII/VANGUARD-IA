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
    const zonesGrid = document.getElementById('zonesGrid');
    const openAddZoneModalBtn = document.getElementById('openAddZoneModalBtn');
    const zoneModal = document.getElementById('zoneModal');
    const closeZoneModalBtn = document.getElementById('closeZoneModalBtn');
    const cancelZoneModalBtn = document.getElementById('cancelZoneModalBtn');
    const zoneForm = document.getElementById('zoneForm');
    const modalTitle = document.getElementById('modalTitle');
    const zoneIdInput = document.getElementById('zoneId');
    const zoneCenterInput = document.getElementById('zoneCenter');

    const statsTotalZones = document.getElementById('stats-total-zones');
    const statsActiveZones = document.getElementById('stats-active-zones');

    const API_URL = '/api/zonas';

    let map = null;
    let heatLayer = null;
    let markersLayer = L.layerGroup(); 
    let tempMarker = null;

    function initMap() {
        if (document.getElementById('zonesMap')) {
            const cuscoCoords = [-13.5170, -71.9762];
            map = L.map('zonesMap').setView(cuscoCoords, 13);

            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(map);
            
            heatLayer = L.heatLayer([], { radius: 25, blur: 15, maxZoom: 18, gradient: {0.4: 'blue', 0.65: 'lime', 1: 'red'} }).addTo(map);
            markersLayer.addTo(map);

            map.on('click', handleMapClick);
            map.on('contextmenu', handleMapClick);
        }
    }

    function handleMapClick(e) {
        const lat = e.latlng.lat.toFixed(6);
        const lng = e.latlng.lng.toFixed(6);
        const wktPoint = `POINT(${lng} ${lat})`;

        if (tempMarker) {
            map.removeLayer(tempMarker);
        }
        tempMarker = L.marker(e.latlng, {draggable: false, opacity: 0.8}).addTo(map)
            .bindPopup(`<b>¿Crear nueva zona aquí?</b><br>Lat: ${lat}, Lng: ${lng}`)
            .openPopup();
        
        openModal('add', null, wktPoint);
    }

    function parsePointWKT(wktString) {
        if (!wktString || !wktString.toUpperCase().startsWith('POINT')) return null;
        const match = wktString.match(/POINT\s*\(\s*(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s*\)/i);
        return match ? [parseFloat(match[2]), parseFloat(match[1])] : null;
    }

    function updateMapWithZones(zones) {
        if (!map) return;

        const heatPoints = [];
        markersLayer.clearLayers();
        
        if (tempMarker && map.hasLayer(tempMarker)) {
             markersLayer.addLayer(tempMarker);
        }

        zones.forEach(zone => {
            const latLng = parsePointWKT(zone.centro);

            if (latLng) {
                const intensity = parseFloat(zone.intensidad) || 0.1;
                heatPoints.push([latLng[0], latLng[1], intensity]);

                const popupContent = `
                    <b>${zone.nombre_zona}</b><br>
                    ${zone.descripcion || 'Sin descripción.'}<br>
                    <hr style="margin: 4px 0; border-color: var(--border-color);">
                    <strong>Estado:</strong> ${zone.estado}<br>
                    <strong>Intensidad:</strong> ${intensity.toFixed(2)}
                `;

                const marker = L.marker(latLng).bindPopup(popupContent);
                markersLayer.addLayer(marker);
            } else {

                 console.warn(`La zona "${zone.nombre_zona}" (ID: ${zone.id_zona}) no tiene coordenadas de centro válidas o está en formato incorrecto:`, zone.centro);
            }
        });
        
        if (heatLayer) {
            heatLayer.setLatLngs(heatPoints);
        }
    }

    function openModal(mode = 'add', zoneData = null, wktPointFromMap = null) {
        zoneForm.reset();
        zoneIdInput.value = '';
        document.getElementById('zoneIntensity').value = 0.5;
        zoneCenterInput.readOnly = false;

        if (wktPointFromMap) {
            modalTitle.textContent = 'Añadir Nueva Zona (desde Mapa)';
            zoneCenterInput.value = wktPointFromMap;
            zoneCenterInput.readOnly = true;
            document.getElementById('zoneName').focus();
        } else if (mode === 'edit' && zoneData) {
            modalTitle.textContent = 'Editar Zona';
            zoneIdInput.value = zoneData.id_zona;
            document.getElementById('zoneName').value = zoneData.nombre_zona || '';
            document.getElementById('zoneDescription').value = zoneData.descripcion || '';
            document.getElementById('zoneCoordinates').value = zoneData.coordenadas_wkt || '';
            zoneCenterInput.value = zoneData.centro_wkt || '';
            document.getElementById('zoneStatus').value = zoneData.estado || 'Activa';
            document.getElementById('zoneIntensity').value = zoneData.intensidad !== null ? parseFloat(zoneData.intensidad).toFixed(2) : 0.5;
        } else {
            modalTitle.textContent = 'Añadir Nueva Zona (Manual)';
            zoneCenterInput.placeholder = 'POINT(lon lat) Ej: POINT(-71.97 -13.51)';
        }
        zoneModal.classList.add('visible');
    }

    function closeModal() {
        zoneModal.classList.remove('visible');
        zoneCenterInput.readOnly = false;
        if (tempMarker) {
            map.removeLayer(tempMarker);
            tempMarker = null;
        }
    }

    if (openAddZoneModalBtn) openAddZoneModalBtn.addEventListener('click', () => openModal('add'));
    if (closeZoneModalBtn) closeZoneModalBtn.addEventListener('click', closeModal);
    if (cancelZoneModalBtn) cancelZoneModalBtn.addEventListener('click', closeModal);
    window.addEventListener('click', (event) => { if (event.target === zoneModal) closeModal(); });

    async function fetchZones() {
        try {
            const response = await fetch(API_URL);
            if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
            const zones = await response.json();
            
            console.log("Datos de zonas recibidos desde el API:", zones);

            renderZoneCards(zones);
            updateStats(zones);
            updateMapWithZones(zones); 

        } catch (error) {
            console.error('Error al cargar zonas:', error);
            if(zonesGrid) zonesGrid.innerHTML = `<div class="card zone-card placeholder-card" style="text-align: center; padding: 40px; grid-column: 1 / -1;">Error al cargar zonas.</div>`;
        }
    }

    function renderZoneCards(zones) {
        if (!zonesGrid) return;
        zonesGrid.innerHTML = '';
        if (zones.length === 0) {
            zonesGrid.innerHTML = `<div class="card zone-card placeholder-card" style="text-align: center; padding: 40px; grid-column: 1 / -1;">No hay zonas registradas.</div>`;
            return;
        }
        zones.forEach(zone => {
            const intensityText = zone.intensidad !== null ? parseFloat(zone.intensidad).toFixed(2) : 'N/A';
            const zoneCard = `
                <div class="card zone-card" data-id="${zone.id_zona}">
                    <div class="zone-card-thumbnail"><i class="fas fa-broadcast-tower"></i></div>
                    <div class="zone-card-header">
                        <h3 class="zone-card-name">${zone.nombre_zona}</h3>
                        <span class="zone-status status-${zone.estado ? zone.estado.toLowerCase() : 'desconocido'}">
                            <span class="zone-status-indicator"></span>
                            ${zone.estado || 'Desconocido'}
                        </span>
                    </div>
                    <p class="zone-card-description">${zone.descripcion || 'Sin descripción.'}</p>
                    <div class="zone-card-info">
                        <!-- Corregido aquí también para usar 'centro' -->
                        <small><strong>Centro:</strong> ${zone.centro || 'N/A'}</small><br>
                        <small><strong>Intensidad:</strong> ${intensityText}</small><br>
                        <small><strong>Modificada:</strong> ${new Date(zone.fecha_modificacion).toLocaleString()}</small>
                    </div>
                    <div class="zone-card-actions">
                        <button class="zone-action-button edit-zone-btn" data-id="${zone.id_zona}"><i class="fas fa-edit"></i> Editar</button>

                    </div>
                </div>`;
            zonesGrid.insertAdjacentHTML('beforeend', zoneCard);
        });

        document.querySelectorAll('.edit-zone-btn').forEach(button => {
            button.addEventListener('click', async (e) => {
                const zoneId = e.currentTarget.dataset.id;
                 try {
                    const response = await fetch(API_URL);
                    if (!response.ok) throw new Error('No se pudo obtener la lista de zonas.');
                    const allZones = await response.json();
                    const zoneToEdit = allZones.find(z => z.id_zona == zoneId);
                    if (zoneToEdit) openModal('edit', zoneToEdit);
                    else alert('La zona que intentas editar ya no existe.');
                } catch (error) {
                    console.error("Error al obtener datos para editar:", error);
                    alert("Error: " + error.message);
                }
            });
        });
        document.querySelectorAll('.delete-zone-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const zoneId = e.currentTarget.dataset.id;
                if (confirm('¿Estás seguro de que quieres eliminar esta zona? Esta acción no se puede deshacer.')) {
                    deleteZone(zoneId);
                }
            });
        });
    }

    function updateStats(zones) {
        if (statsTotalZones) statsTotalZones.textContent = zones.length;
        if (statsActiveZones) {
            const activeCount = zones.filter(zone => zone.estado && zone.estado.toLowerCase() === 'activa').length;
            statsActiveZones.textContent = activeCount;
        }
    }

    if (zoneForm) {
        zoneForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const formData = new FormData(zoneForm);
            const zoneData = Object.fromEntries(formData.entries());
            const id = zoneIdInput.value;

            if (!zoneData.centro || !zoneData.centro.toUpperCase().startsWith('POINT(')) {
                alert('El Centro (Punto WKT) es obligatorio y debe tener el formato POINT(lon lat).');
                return;
            }

            try {
                const response = await fetch(id ? `${API_URL}/${id}` : API_URL, {
                    method: id ? 'PUT' : 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(zoneData)
                });
                if (!response.ok) { const errData = await response.json(); throw new Error(errData.error || `Error HTTP: ${response.status}`); }
                const result = await response.json();
                alert(result.message || (id ? 'Zona actualizada con éxito' : 'Zona creada con éxito'));
                closeModal();
                fetchZones();
            } catch (error) {
                console.error('Error al guardar zona:', error);
                alert(`Error al guardar zona: ${error.message}`);
            }
        });
    }

    async function deleteZone(id) {
        try {
            const response = await fetch(`${API_URL}/${id}`, { method: 'DELETE' });
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || `Error HTTP: ${response.status}`);
            }
            const result = await response.json();
            alert(result.message || 'Zona eliminada con éxito');
            fetchZones(); 
        } catch (error) {
            console.error('Error al eliminar zona:', error);
            alert(`Error al eliminar zona: ${error.message}`);
        }
    }

    initMap();
    if (document.getElementById('zonesMap') || zonesGrid) {
      fetchZones();
    }
});