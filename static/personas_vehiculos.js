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
    const API_PERSONAS = '/api/personas_registradas';
    const API_VEHICULOS = '/api/vehiculos_registrados';
    const API_DROPDOWN_PERSONAS = '/api/dropdown/personas_usuario';
    const IMAGENES_REF_BASE_URL = '/media_ref/personas/';
    const formPersona = document.getElementById('formRegistrarPersona');
    const tablaPersonasBody = document.getElementById('tablaPersonas')?.querySelector('tbody');
    const personaIdInput = document.getElementById('personaId');
    const personaNombreInput = document.getElementById('personaNombre');
    const personaIdentificacionInput = document.getElementById('personaIdentificacion');
    const personaEstadoSelect = document.getElementById('personaEstado');
    const personaMotivoContainer = document.getElementById('personaMotivoContainer');
    const personaMotivoInput = document.getElementById('personaMotivo');
    const personaImagenInput = document.getElementById('personaImagen');
    const personaImagenPreview = document.getElementById('personaImagenPreview');
    const formPersonaTitle = document.getElementById('formPersonaTitle');
    const btnSubmitPersonaText = document.getElementById('btnSubmitPersonaText');
    const btnCancelarEdicionPersona = document.getElementById('btnCancelarEdicionPersona');
    const imagenPersonaObligatoriaSpan = document.getElementById('imagenPersonaObligatoria');

    const formVehiculo = document.getElementById('formRegistrarVehiculo');
    const tablaVehiculosBody = document.getElementById('tablaVehiculos')?.querySelector('tbody');
    const vehiculoIdInput = document.getElementById('vehiculoId');
    const vehiculoPlacaInput = document.getElementById('vehiculoPlaca');
    const vehiculoMarcaInput = document.getElementById('vehiculoMarca');
    const vehiculoModeloInput = document.getElementById('vehiculoModelo');
    const vehiculoColorInput = document.getElementById('vehiculoColor');
    const vehiculoPropietarioSelect = document.getElementById('vehiculoPropietario');
    const vehiculoEstadoSelect = document.getElementById('vehiculoEstado');
    const vehiculoMotivoContainer = document.getElementById('vehiculoMotivoContainer');
    const vehiculoMotivoInput = document.getElementById('vehiculoMotivo');
    const vehiculoNotasInput = document.getElementById('vehiculoNotas');
    const formVehiculoTitle = document.getElementById('formVehiculoTitle');
    const btnSubmitVehiculoText = document.getElementById('btnSubmitVehiculoText');
    const btnCancelarEdicionVehiculo = document.getElementById('btnCancelarEdicionVehiculo');

    const confirmDeleteModal = document.getElementById('confirmDeleteModal');
    const confirmDeleteMessage = document.getElementById('confirmDeleteMessage');
    const btnConfirmDelete = document.getElementById('btnConfirmDelete');
    const btnCancelDelete = document.getElementById('btnCancelDelete');
    const modalCloseButton = confirmDeleteModal?.querySelector('.close-button');
    let deleteFunction = null;

    const toastContainer = document.getElementById('toast-container');

    function showToast(message, type = 'info', duration = 3500) {
        if (!toastContainer) return; 
        const toast = document.createElement('div');
        toast.className = `toast ${type}`; 

        let iconClass = '';
        if (type === 'success') iconClass = 'fa-check-circle';
        else if (type === 'error') iconClass = 'fa-exclamation-circle';
        else if (type === 'warning') iconClass = 'fa-exclamation-triangle';
        else iconClass = 'fa-info-circle';

        const iconElement = document.createElement('i');
        iconElement.className = `fas ${iconClass}`;

        const messageSpan = document.createElement('span');
        messageSpan.className = 'toast-message';
        messageSpan.textContent = message;

        const closeButton = document.createElement('button');
        closeButton.className = 'toast-close-button';
        closeButton.setAttribute('aria-label', 'Cerrar');
        closeButton.innerHTML = '×';
        
        const removeToast = () => {
            toast.classList.remove('show');

            toast.addEventListener('transitionend', () => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, { once: true });

            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 500);
        };

        closeButton.onclick = removeToast;
        
        toast.appendChild(iconElement);
        toast.appendChild(messageSpan);
        toast.appendChild(closeButton);
        toastContainer.appendChild(toast);

        toast.offsetHeight; 

        toast.classList.add('show');
        setTimeout(removeToast, duration);
    }

    function setSubmitButtonState(formElement, isLoading, defaultText, defaultIconClass) {
        const submitButton = formElement.querySelector('button[type="submit"]');
        if (!submitButton) return;
        const textSpan = submitButton.querySelector('span'); 
        const iconElement = submitButton.querySelector('i');

        if (isLoading) {
            submitButton.disabled = true;
            if(textSpan) textSpan.textContent = 'Procesando...';
            if(iconElement) iconElement.className = 'fas fa-spinner fa-spin';
        } else {
            submitButton.disabled = false;
            if(textSpan) textSpan.textContent = defaultText;
            if(iconElement) iconElement.className = defaultIconClass;
        }
    }

    personaEstadoSelect?.addEventListener('change', function() {
        const estado = this.value;
        if (estado === 'Buscado' || estado === 'Sospechoso' || estado === 'Restringido') {
            personaMotivoContainer.style.display = 'block';
            personaMotivoInput.required = true;
        } else {
            personaMotivoContainer.style.display = 'none';
            personaMotivoInput.required = false;
            personaMotivoInput.value = '';
        }
    });

    personaImagenInput?.addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                personaImagenPreview.src = e.target.result;
                personaImagenPreview.style.display = 'block';
            }
            reader.readAsDataURL(file);
        } else {
            personaImagenPreview.src = '#';
            personaImagenPreview.style.display = 'none';
        }
    });
    
    function resetFormPersona() {
        formPersona.reset();
        personaIdInput.value = '';
        personaImagenPreview.src = '#';
        personaImagenPreview.style.display = 'none';
        personaImagenInput.value = '';
        formPersonaTitle.innerHTML = '<i class="fas fa-user-plus"></i> Registrar Nueva Persona';

        if(btnSubmitPersonaText) btnSubmitPersonaText.textContent = 'Registrar Persona'; 
        btnCancelarEdicionPersona.style.display = 'none';
        personaMotivoContainer.style.display = 'none';
        personaMotivoInput.required = false;
        if(imagenPersonaObligatoriaSpan) imagenPersonaObligatoriaSpan.style.display = 'inline';
        personaImagenInput.required = true;
        setSubmitButtonState(formPersona, false, 'Registrar Persona', 'fas fa-save');
    }

    btnCancelarEdicionPersona?.addEventListener('click', resetFormPersona);

    formPersona?.addEventListener('submit', async function(event) {
        event.preventDefault();
        setSubmitButtonState(formPersona, true, 'Registrar Persona', 'fas fa-save');
        
        const formData = new FormData(formPersona);
        const personaId = personaIdInput.value;
        let url = API_PERSONAS;
        let method = 'POST';

        if (personaId) {
            url = `${API_PERSONAS}/${personaId}`;
            method = 'PUT';
            if (!personaImagenInput.files[0]) {
                formData.delete('imagen_facial');
            }
        } else {
            if (!personaImagenInput.files[0]) {
                showToast('La imagen facial es obligatoria para registrar una nueva persona.', 'error');
                setSubmitButtonState(formPersona, false, 'Registrar Persona', 'fas fa-save');
                return;
            }
        }
        
        const estado = formData.get('estado_persona');
        if (estado !== 'Buscado' && estado !== 'Sospechoso' && estado !== 'Restringido') {
            formData.set('motivo_busqueda', ''); 
        }

        try {
            const response = await fetch(url, { method: method, body: formData });
            const result = await response.json();

            if (response.ok) {
                showToast(result.message || (personaId ? 'Persona actualizada correctamente.' : 'Persona registrada correctamente.'), 'success');
                resetFormPersona();
                cargarPersonas();

                if (window.faceDetector && typeof window.faceDetector.reloadReferences === 'function') {
                    window.faceDetector.reloadReferences();
                } else if (typeof window.app !== 'undefined' && window.app.faceDetector && typeof window.app.faceDetector.reloadReferences === 'function') {
                    window.app.faceDetector.reloadReferences();
                } else {
                    console.warn("Función para recargar referencias de rostros no encontrada (window.faceDetector.reloadReferences o window.app.faceDetector.reloadReferences).");
                }
            } else {
                showToast(result.error || 'Error al procesar la solicitud.', 'error');
            }
        } catch (error) {
            console.error('Error en el formulario de persona:', error);
            showToast('Error de conexión o del servidor.', 'error');
        } finally {
            const submitText = personaId ? 'Actualizar Persona' : 'Registrar Persona';
            setSubmitButtonState(formPersona, false, submitText, 'fas fa-save');
        }
    });

    async function cargarPersonas() {
        if (!tablaPersonasBody) return;
        try {
            const response = await fetch(API_PERSONAS);
            if (!response.ok) {
                 if (response.status === 401) { window.location.href = '/login'; return; }
                 throw new Error(`Error ${response.status}`);
            }
            const personas = await response.json();
            tablaPersonasBody.innerHTML = '';
            personas.forEach(persona => {
                const tr = document.createElement('tr');
                let estadoClass = persona.estado_persona ? persona.estado_persona.toLowerCase().replace(/\s+/g, '_') : 'no_asignado';
                tr.innerHTML = `
                    <td class="td-foto"><div class="table-photo-container"><img src="${persona.imagen_url}" alt="${persona.nombre}" class="table-photo"></div></td>
                    <td class="td-nombre">${persona.nombre}</td>
                    <td>${persona.identificacion || 'N/A'}</td>
                    <td><span class="status-badge status-${estadoClass}">${persona.estado_persona || 'N/A'}</span></td>
                    <td class="td-motivo">${persona.motivo_busqueda || ''}</td>
                    <td class="td-acciones table-actions">
                        <button class="btn btn-sm btn-info btn-edit-persona" data-id="${persona.id_persona}"><i class="fas fa-edit"></i></button>
                        <button class="btn btn-sm btn-danger btn-delete-persona" data-id="${persona.id_persona}"><i class="fas fa-trash"></i></button>
                    </td>
                `;
                tablaPersonasBody.appendChild(tr);
            });
            attachPersonasActionButtons();
        } catch (error) {
            console.error('Error cargando personas:', error);
            tablaPersonasBody.innerHTML = `<tr><td colspan="6" class="text-center error-message">No se pudieron cargar las personas.</td></tr>`;
        }
    }

    function editarPersona(id) {
        fetch(`${API_PERSONAS}/${id}`)
            .then(response => {
                if (!response.ok) {
                     response.json().then(err => showToast(err.error || 'Persona no encontrada.', 'error'));
                     throw new Error('Persona no encontrada o error del servidor');
                }
                return response.json();
            })
            .then(persona => {
                personaIdInput.value = persona.id_persona;
                personaNombreInput.value = persona.nombre;
                personaIdentificacionInput.value = persona.identificacion || '';
                personaEstadoSelect.value = persona.estado_persona;

                const event = new Event('change');
                personaEstadoSelect.dispatchEvent(event);
                
                personaMotivoInput.value = persona.motivo_busqueda || '';

                if (persona.imagen_facial_ref_filename) {
                    personaImagenPreview.src = `${IMAGENES_REF_BASE_URL}${persona.imagen_facial_ref_filename}`;
                    personaImagenPreview.style.display = 'block';
                } else {
                    personaImagenPreview.src = '#';
                    personaImagenPreview.style.display = 'none';
                }
                personaImagenInput.value = '';
                if(imagenPersonaObligatoriaSpan) imagenPersonaObligatoriaSpan.style.display = 'none';
                personaImagenInput.required = false;

                formPersonaTitle.innerHTML = '<i class="fas fa-user-edit"></i> Editar Persona';
                if(btnSubmitPersonaText) btnSubmitPersonaText.textContent = 'Actualizar Persona';
                setSubmitButtonState(formPersona, false, 'Actualizar Persona', 'fas fa-save');
                btnCancelarEdicionPersona.style.display = 'inline-block';
                
                formPersona.scrollIntoView({ behavior: 'smooth', block: 'start' });
            })
            .catch(error => {
                console.error('Error al cargar datos de persona para editar:', error);

            });
    }

    function confirmarEliminarPersona(id) {
        if(!confirmDeleteModal) return;
        confirmDeleteMessage.textContent = `¿Estás seguro de que deseas eliminar a la persona con ID ${id}? Esta acción también eliminará su imagen de referencia.`;
        confirmDeleteModal.classList.add('show');
        deleteFunction = () => procedaEliminarPersona(id);
    }
    
    async function procedaEliminarPersona(id) {
        try {
            const response = await fetch(`${API_PERSONAS}/${id}`, { method: 'DELETE' });
            const result = await response.json();
            if (response.ok) {
                showToast(result.message || 'Persona eliminada correctamente.', 'success');
                cargarPersonas(); 
                 if(window.faceDetector && typeof window.faceDetector.reloadReferences === 'function'){
                    window.faceDetector.reloadReferences();
                } else if (typeof window.app !== 'undefined' && window.app.faceDetector && typeof window.app.faceDetector.reloadReferences === 'function') {
                    window.app.faceDetector.reloadReferences();
                }
            } else {
                showToast(result.error || 'Error al eliminar la persona.', 'error');
            }
        } catch (error) {
            console.error('Error eliminando persona:', error);
            showToast('Error de conexión o del servidor.', 'error');
        } finally {
            if(confirmDeleteModal) confirmDeleteModal.classList.remove('show');
        }
    }

    function attachPersonasActionButtons() {
        document.querySelectorAll('.btn-edit-persona').forEach(button => {
            button.addEventListener('click', (e) => editarPersona(e.currentTarget.dataset.id));
        });
        document.querySelectorAll('.btn-delete-persona').forEach(button => {
            button.addEventListener('click', (e) => confirmarEliminarPersona(e.currentTarget.dataset.id));
        });
    }

    vehiculoEstadoSelect?.addEventListener('change', function() {
        const estado = this.value;
        if (estado === 'Buscado' || estado === 'Sospechoso' || estado === 'Robado') {
            vehiculoMotivoContainer.style.display = 'block';
            vehiculoMotivoInput.required = true;
        } else {
            vehiculoMotivoContainer.style.display = 'none';
            vehiculoMotivoInput.required = false;
            vehiculoMotivoInput.value = '';
        }
    });

    async function cargarPropietariosDropdown() {
        if (!vehiculoPropietarioSelect) return;
        try {
            const response = await fetch(API_DROPDOWN_PERSONAS); 
            if (!response.ok) {
                if (response.status === 401) { window.location.href = '/login'; return; }
                throw new Error('Error al cargar propietarios');
            }
            const propietarios = await response.json();
            vehiculoPropietarioSelect.innerHTML = '<option value="">(Sin propietario)</option>';
            propietarios.forEach(prop => {
                const option = document.createElement('option');
                option.value = prop.id_persona;
                option.textContent = `${prop.nombre} (ID: ${prop.id_persona})`;
                vehiculoPropietarioSelect.appendChild(option);
            });
        } catch (error) {
            console.error('Error cargando propietarios dropdown:', error);
            showToast('No se pudieron cargar los propietarios en el formulario de vehículos.', 'warning');
        }
    }

    function resetFormVehiculo() {
        formVehiculo.reset();
        vehiculoIdInput.value = '';
        formVehiculoTitle.innerHTML = '<i class="fas fa-car-side"></i> Registrar Nuevo Vehículo';
        if(btnSubmitVehiculoText) btnSubmitVehiculoText.textContent = 'Registrar Vehículo';
        btnCancelarEdicionVehiculo.style.display = 'none';
        vehiculoMotivoContainer.style.display = 'none';
        vehiculoMotivoInput.required = false;
        setSubmitButtonState(formVehiculo, false, 'Registrar Vehículo', 'fas fa-save');
        cargarPropietariosDropdown(); 
    }

    btnCancelarEdicionVehiculo?.addEventListener('click', resetFormVehiculo);
    
    formVehiculo?.addEventListener('submit', async function(event) {
        event.preventDefault();
        setSubmitButtonState(formVehiculo, true, 'Registrar Vehículo', 'fas fa-save');

        const vehiculoId = vehiculoIdInput.value;
        const formData = new FormData(formVehiculo);
        const data = Object.fromEntries(formData.entries());

        if (data.id_propietario === "" || data.id_propietario === null || typeof data.id_propietario === 'undefined') {
            data.id_propietario = null;
        } else {
            data.id_propietario = parseInt(data.id_propietario, 10);
            if (isNaN(data.id_propietario)) data.id_propietario = null; 
        }

        if (data.estado_vehiculo !== 'Buscado' && data.estado_vehiculo !== 'Sospechoso' && data.estado_vehiculo !== 'Robado') {
            data.motivo_busqueda_vehiculo = null; 
        }


        let url = API_VEHICULOS;
        let method = 'POST';

        if (vehiculoId) {
            url = `${API_VEHICULOS}/${vehiculoId}`;
            method = 'PUT';
        }

        try {
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await response.json();

            if (response.ok) {
                showToast(result.message || (vehiculoId ? 'Vehículo actualizado correctamente.' : 'Vehículo registrado correctamente.'), 'success');
                resetFormVehiculo();
                cargarVehiculos();
            } else {
                showToast(result.error || 'Error al procesar la solicitud del vehículo.', 'error');
            }
        } catch (error) {
            console.error('Error en formulario de vehículo:', error);
            showToast('Error de conexión o del servidor.', 'error');
        } finally {
            const submitText = vehiculoId ? 'Actualizar Vehículo' : 'Registrar Vehículo';
            setSubmitButtonState(formVehiculo, false, submitText, 'fas fa-save');
        }
    });

    async function cargarVehiculos() {
        if (!tablaVehiculosBody) return;
        try {
            const response = await fetch(API_VEHICULOS);
            if (!response.ok) {
                const errorData = await response.text();
                showToast(`Error cargando vehículos: ${response.status} ${response.statusText}. ${errorData}`, 'error');
                return;
            }
            const vehiculos = await response.json();
            tablaVehiculosBody.innerHTML = ''; 
            vehiculos.forEach(vehiculo => {
                const tr = document.createElement('tr');
                tr.dataset.idVehiculo = vehiculo.id_vehiculo;
                let estadoClass = vehiculo.estado_vehiculo ? vehiculo.estado_vehiculo.toLowerCase().replace(/\s+/g, '_') : 'autorizado';

                tr.innerHTML = `
                    <td><strong>${vehiculo.placa}</strong></td>
                    <td>${vehiculo.marca || ''} ${vehiculo.modelo || ''}</td>
                    <td>${vehiculo.color || ''}</td>
                    <td>${vehiculo.nombre_propietario || (vehiculo.id_propietario ? `ID Prop.: ${vehiculo.id_propietario}`: 'N/A')}</td>
                    <td><span class="status-badge status-${estadoClass}">${vehiculo.estado_vehiculo}</span></td>
                    <td class="td-motivo">${vehiculo.motivo_busqueda_vehiculo || ''}</td>
                    <td class="td-acciones table-actions">
                        <button class="btn btn-sm btn-info btn-edit-vehiculo" data-id="${vehiculo.id_vehiculo}" title="Editar">
                            <i class="fas fa-edit"></i><span class="action-text"> Editar</span>
                        </button>
                        <button class="btn btn-sm btn-danger btn-delete-vehiculo" data-id="${vehiculo.id_vehiculo}" title="Eliminar">
                            <i class="fas fa-trash"></i><span class="action-text"> Eliminar</span>
                        </button>
                    </td>
                `;
                tablaVehiculosBody.appendChild(tr);
            });
            attachVehiculosActionButtons();
        } catch (error) {
            console.error('Error cargando vehículos:', error);
            showToast('Error al cargar la lista de vehículos.', 'error');
        }
    }
    
    async function editarVehiculo(id) {
        try {

            await cargarPropietariosDropdown(); 
            
            const response = await fetch(`${API_VEHICULOS}/${id}`);
            if (!response.ok) {
                response.json().then(err => showToast(err.error || 'Vehículo no encontrado.', 'error'));
                throw new Error('Vehículo no encontrado o error del servidor');
            }
            const vehiculo = await response.json();

            vehiculoIdInput.value = vehiculo.id_vehiculo;
            vehiculoPlacaInput.value = vehiculo.placa;
            vehiculoMarcaInput.value = vehiculo.marca || '';
            vehiculoModeloInput.value = vehiculo.modelo || '';
            vehiculoColorInput.value = vehiculo.color || '';
            vehiculoPropietarioSelect.value = vehiculo.id_propietario || ''; 
            vehiculoEstadoSelect.value = vehiculo.estado_vehiculo;

            const event = new Event('change');
            vehiculoEstadoSelect.dispatchEvent(event);

            vehiculoMotivoInput.value = vehiculo.motivo_busqueda_vehiculo || '';
            vehiculoNotasInput.value = vehiculo.notas || '';

            formVehiculoTitle.innerHTML = '<i class="fas fa-edit"></i> Editar Vehículo';
            if(btnSubmitVehiculoText) btnSubmitVehiculoText.textContent = 'Actualizar Vehículo';
            setSubmitButtonState(formVehiculo, false, 'Actualizar Vehículo', 'fas fa-save');
            btnCancelarEdicionVehiculo.style.display = 'inline-block';
            
            formVehiculo.scrollIntoView({ behavior: 'smooth', block: 'start' });

        } catch (error) {
            console.error('Error al cargar datos de vehículo para editar:', error);

        }
    }

    function confirmarEliminarVehiculo(id) {
        if(!confirmDeleteModal) return;
        confirmDeleteMessage.textContent = `¿Estás seguro de que deseas eliminar el vehículo con ID ${id}?`;
        confirmDeleteModal.classList.add('show');
        deleteFunction = () => procedaEliminarVehiculo(id);
    }
  
    async function procedaEliminarVehiculo(id) {
        try {
            const response = await fetch(`${API_VEHICULOS}/${id}`, { method: 'DELETE' });
            const result = await response.json();
            if (response.ok) {
                showToast(result.message || 'Vehículo eliminado correctamente.', 'success');
                cargarVehiculos();
            } else {
                showToast(result.error || 'Error al eliminar el vehículo.', 'error');
            }
        } catch (error) {
            console.error('Error eliminando vehículo:', error);
            showToast('Error de conexión o del servidor.', 'error');
        } finally {
            if(confirmDeleteModal) confirmDeleteModal.classList.remove('show');
        }
    }

    function attachVehiculosActionButtons() {
        document.querySelectorAll('.btn-edit-vehiculo').forEach(button => {
            button.addEventListener('click', (e) => editarVehiculo(e.currentTarget.dataset.id));
        });
        document.querySelectorAll('.btn-delete-vehiculo').forEach(button => {
            button.addEventListener('click', (e) => confirmarEliminarVehiculo(e.currentTarget.dataset.id));
        });
    }

    btnConfirmDelete?.addEventListener('click', () => {
        if (deleteFunction) {
            deleteFunction();
            deleteFunction = null; 
        }
    });
    const closeModal = () => {
        if (confirmDeleteModal) {
            confirmDeleteModal.classList.remove('show');
        }
        deleteFunction = null; 
    };
    btnCancelDelete?.addEventListener('click', closeModal);
    modalCloseButton?.addEventListener('click', closeModal);
    confirmDeleteModal?.addEventListener('click', (event) => {
        if (event.target === confirmDeleteModal) {
            closeModal();
        }
    });

    if (tablaPersonasBody) cargarPersonas();
    if (tablaVehiculosBody) cargarVehiculos();
    if (vehiculoPropietarioSelect) cargarPropietariosDropdown();

    if (formPersona) setSubmitButtonState(formPersona, false, 'Registrar Persona', 'fas fa-save');
    if (formVehiculo) setSubmitButtonState(formVehiculo, false, 'Registrar Vehículo', 'fas fa-save');
});