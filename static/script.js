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
    const uploadArea = document.getElementById('upload-section');
    const fileInput = document.getElementById('fileInput');
    
    const mediaPreviewImg = document.getElementById('media-preview-img');
    const mediaPreviewVideo = document.getElementById('media-preview-video');
    const mediaPreviewTitle = document.getElementById('media-preview-title');
    const mediaPlaceholderIcon = document.getElementById('media-placeholder-icon');

    const originalMediaImg = document.getElementById('original-media-img');
    const originalMediaVideo = document.getElementById('original-media-video'); 
    const originalMediaPlaceholder = document.getElementById('original-media-placeholder');

    const analyzedMediaImg = document.getElementById('analyzed-media-img');
    const analyzedMediaVideo = document.getElementById('analyzed-media-video'); 
    const analyzedMediaPlaceholder = document.getElementById('analyzed-media-placeholder');

    const analyzeButton = document.getElementById('analyzeButton');
    const analysisResultSection = document.getElementById('analysis-result-section');
    const mediaLoadingOverlay = document.getElementById('mediaLoadingOverlay');

    let currentFile = null; 
    let currentFileType = null; 

    function extractFrame(videoSource, timeInSeconds, callback) {
        const video = document.createElement('video');
        video.style.display = 'none';
        video.muted = true;
        video.preload = 'metadata'; 
        video.crossOrigin = "anonymous";

        let loadTimeout;
        let hasCalledBack = false;
        let objectUrl = null;

        const cleanupAndCallback = (frameData, errorMsg) => {
            if (hasCalledBack) return;
            hasCalledBack = true;

            clearTimeout(loadTimeout);
            video.oncanplay = null;
            video.onseeked = null;
            video.onerror = null;
            video.src = "";
            video.removeAttribute('src'); 
            if (objectUrl) {
                URL.revokeObjectURL(objectUrl); 
                objectUrl = null;
            }

            callback(frameData, errorMsg);
        };
        
        loadTimeout = setTimeout(() => {
            console.warn(`Timeout (10s) al cargar video para extraer fotograma: ${videoSource instanceof File ? videoSource.name : videoSource}`);
            cleanupAndCallback(null, "Timeout al cargar video");
        }, 10000); 

        video.oncanplay = () => {
            if (hasCalledBack) return;
            let targetTime = timeInSeconds;

            if (video.duration && video.duration > 0) {
                if (targetTime >= video.duration) { 
                    targetTime = video.duration * 0.9;
                }
                 if (targetTime < 0) targetTime = 0.1; 
            } else { 
                 targetTime = Math.max(0.1, timeInSeconds); 
            }
            video.currentTime = targetTime;
        };
        
        video.onseeked = () => {
            if (hasCalledBack) return;
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth > 0 ? video.videoWidth : 320;
            canvas.height = video.videoHeight > 0 ? video.videoHeight : 180;

            if (video.videoWidth === 0 || video.videoHeight === 0) {
                console.warn(`Dimensiones del video son 0 al extraer fotograma. Usando ${canvas.width}x${canvas.height}. Video: ${videoSource instanceof File ? videoSource.name : videoSource}`);
            }

            const ctx = canvas.getContext('2d');
            try {
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                const dataURL = canvas.toDataURL('image/jpeg', 0.85); 
                cleanupAndCallback(dataURL, null);
            } catch (e) {
                console.error(`Error en drawImage o toDataURL: ${e.message}. Video: ${videoSource instanceof File ? videoSource.name : videoSource}`, e);
                cleanupAndCallback(null, `Error al procesar fotograma (canvas): ${e.message}`);
            }
        };

        video.onerror = (e) => {
            if (hasCalledBack) return;
            let errorMsg = "Error de video";
            if (video.error) {
                errorMsg += `: ${video.error.message} (code ${video.error.code})`;
                console.error(`Error al cargar video para fotograma: ${video.error.message}, Code: ${video.error.code}. Video: ${videoSource instanceof File ? videoSource.name : videoSource}`);
            } else {
                console.error(`Error desconocido al cargar video para fotograma. Video: ${videoSource instanceof File ? videoSource.name : videoSource}`, e);
                errorMsg += ": Desconocido";
            }
            cleanupAndCallback(null, errorMsg);
        };
        
        if (videoSource instanceof Blob || videoSource instanceof File) {
            objectUrl = URL.createObjectURL(videoSource);
            video.src = objectUrl;
        } else if (typeof videoSource === 'string') {
            video.src = videoSource;
        } else {
            cleanupAndCallback(null, "Fuente de video inválida");
            return;
        }
        
        video.load(); 
    }


    if (uploadArea) {
        uploadArea.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', handleFileSelect);
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, preventDefaults, false);
        });
        function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => uploadArea.classList.add('highlight'), false);
        });
        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => uploadArea.classList.remove('highlight'), false);
        });
        uploadArea.addEventListener('drop', handleDrop, false);
    }

    function handleDrop(e) {
        let dt = e.dataTransfer;
        let files = dt.files;
        if (files.length > 0) {
            fileInput.files = files; 
            handleFileSelect({ target: fileInput }); 
        }
    }

    function resetPreviews() {
        if(mediaPreviewImg) { mediaPreviewImg.style.display = 'none'; mediaPreviewImg.src = ''; }
        if(mediaPreviewVideo) { mediaPreviewVideo.style.display = 'none'; mediaPreviewVideo.src = ''; }
        if (mediaPlaceholderIcon) {
            mediaPlaceholderIcon.innerHTML = '<i class="fas fa-photo-video"></i>'; 
            mediaPlaceholderIcon.style.display = 'flex';
        }

        if(originalMediaImg) { originalMediaImg.style.display = 'none'; originalMediaImg.src = ''; }
        if (originalMediaVideo) { originalMediaVideo.style.display = 'none'; originalMediaVideo.src = ''; }
        if (originalMediaPlaceholder) {
            originalMediaPlaceholder.innerHTML = '<i class="fas fa-film"></i>'; 
            originalMediaPlaceholder.style.display = 'flex';
        }

        if(analyzedMediaImg) { analyzedMediaImg.style.display = 'none'; analyzedMediaImg.src = ''; }
        if (analyzedMediaVideo) { analyzedMediaVideo.style.display = 'none'; analyzedMediaVideo.src = ''; }
        if (analyzedMediaPlaceholder) {
            analyzedMediaPlaceholder.innerHTML = '<i class="fas fa-images"></i>'; 
            analyzedMediaPlaceholder.style.display = 'flex';
        }
        if(analysisResultSection) analysisResultSection.textContent = 'Esperando análisis...';
    }

    function handleFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            currentFile = file;
            resetPreviews(); 

            if (file.type.startsWith('image/')) {
                currentFileType = 'image';
                const reader = new FileReader();
                reader.onload = (e) => {
                    const fileDataUrl = e.target.result;
                    if(mediaPreviewTitle) mediaPreviewTitle.textContent = 'Imagen subida: ' + file.name;
                    if(mediaPreviewImg) { mediaPreviewImg.src = fileDataUrl; mediaPreviewImg.style.display = 'block'; }
                    if(mediaPlaceholderIcon) mediaPlaceholderIcon.style.display = 'none';
                    
                    if(originalMediaImg) { originalMediaImg.src = fileDataUrl; originalMediaImg.style.display = 'block'; }
                    if(originalMediaPlaceholder) originalMediaPlaceholder.style.display = 'none';
                };
                reader.readAsDataURL(file);
            } else if (file.type.startsWith('video/')) {
                currentFileType = 'video';
                const objectURLForPreview = URL.createObjectURL(file);
                if(mediaPreviewTitle) mediaPreviewTitle.textContent = 'Video subido: ' + file.name;
                if(mediaPreviewVideo) { 
                    mediaPreviewVideo.src = objectURLForPreview; 
                    mediaPreviewVideo.style.display = 'block'; 
                    mediaPreviewVideo.load(); 
                }
                if(mediaPlaceholderIcon) mediaPlaceholderIcon.style.display = 'none';
                
                if(originalMediaImg && originalMediaPlaceholder) {
                    originalMediaPlaceholder.style.display = 'flex'; 
                    originalMediaPlaceholder.innerHTML = '<i class="fas fa-spinner fa-spin"></i>'; 
                    extractFrame(file, 1, (frameUrl, errorMsg) => { 
                        if (frameUrl) {
                            originalMediaImg.src = frameUrl;
                            originalMediaImg.style.display = 'block';
                            originalMediaPlaceholder.style.display = 'none';
                        } else {
                            originalMediaImg.style.display = 'none';
                            originalMediaPlaceholder.style.display = 'flex';
                            originalMediaPlaceholder.innerHTML = `<i class="fas fa-exclamation-triangle"></i><p style="font-size:0.5em;margin-top:5px;text-align:center;">${errorMsg || 'Error fotograma'}</p>`;
                        }
                    });
                }

                fileInput.addEventListener('change', () => { URL.revokeObjectURL(objectURLForPreview); }, { once: true });


            } else if (file.type.startsWith('audio/')) {
                currentFileType = 'audio';
                if(mediaPreviewTitle) mediaPreviewTitle.textContent = 'Audio subido: ' + file.name;
                if(mediaPlaceholderIcon) {
                    mediaPlaceholderIcon.innerHTML = '<i class="fas fa-file-audio fa-3x"></i>'; 
                    mediaPlaceholderIcon.style.display = 'flex';
                }
                if(mediaPreviewImg) mediaPreviewImg.style.display = 'none';
                if(mediaPreviewVideo) mediaPreviewVideo.style.display = 'none';

                if(originalMediaPlaceholder) {
                    originalMediaPlaceholder.innerHTML = '<i class="fas fa-file-audio fa-2x"></i>'; 
                    originalMediaPlaceholder.style.display = 'flex';
                }
                if(originalMediaImg) originalMediaImg.style.display = 'none';
                if (originalMediaVideo) originalMediaVideo.style.display = 'none';

            } else {
                currentFileType = null;
                if(mediaPreviewTitle) mediaPreviewTitle.textContent = 'Archivo no soportado';
                if(mediaPlaceholderIcon) {
                     mediaPlaceholderIcon.innerHTML = '<i class="fas fa-exclamation-triangle"></i><p style="font-size:0.5em;margin-top:5px;text-align:center;">Tipo no soportado</p>';
                     mediaPlaceholderIcon.style.display = 'flex';
                }
                currentFile = null;
            }
        }
    }

    if (analyzeButton) {
        analyzeButton.addEventListener('click', async () => {
            if (!currentFile) { alert("Por favor, sube un archivo primero."); return; }
            const selectedModelElements = document.querySelectorAll('.models-list input[type="checkbox"][data-model-id]:checked');
            const selectedModels = Array.from(selectedModelElements).map(el => el.dataset.modelId);
            if (selectedModels.length === 0) { alert("Por favor, selecciona al menos un modelo para analizar."); return; }

            if (selectedModels.includes('Audio_Contexto') && currentFileType === 'image') {
                alert("El modelo 'Audio Contexto' no puede procesar imágenes. Por favor, sube un video o un archivo de audio.");
                return;
            }

            if (mediaLoadingOverlay) mediaLoadingOverlay.classList.add('visible');
            if (analysisResultSection) analysisResultSection.textContent = ''; 

            const formData = new FormData();
            formData.append('file', currentFile);
            selectedModels.forEach(modelId => { formData.append('models[]', modelId); });

            try {
                const response = await fetch('/api/analyze', { method: 'POST', body: formData });
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({ error: 'Error desconocido en el servidor.' }));
                    throw new Error(errorData.error || `Error del servidor: ${response.status}`);
                }
                const data = await response.json();
                if (analysisResultSection) analysisResultSection.innerHTML = data.analysis_text.replace(/\n/g, '<br>');

                if (analyzedMediaImg) { analyzedMediaImg.style.display = 'none'; analyzedMediaImg.src = ''; }
                if (analyzedMediaVideo) { analyzedMediaVideo.style.display = 'none'; analyzedMediaVideo.src = ''; }
                if (analyzedMediaPlaceholder) {
                    analyzedMediaPlaceholder.style.display = 'flex';
                    analyzedMediaPlaceholder.innerHTML = '<i class="fas fa-images"></i>';
                }
                
                let processedMediaAvailable = false;
                if (data.processed_media && Object.keys(data.processed_media).length > 0) {
                    let mediaUrlToDisplay = null;
                    if (data.original_media_type === 'image' || data.original_media_type === 'video') {
                        const preferredOrder = ['face_output', 'plate_output'];
                        for (const key of preferredOrder) {
                            if (data.processed_media[key]) { mediaUrlToDisplay = data.processed_media[key]; break; }
                        }

                        if (!mediaUrlToDisplay) {
                             mediaUrlToDisplay = Object.values(data.processed_media)[0];
                        }
                    }

                    if (mediaUrlToDisplay) {
                        processedMediaAvailable = true;
                        const cacheBustUrl = mediaUrlToDisplay + (mediaUrlToDisplay.includes('?') ? '&t=' : '?t=') + new Date().getTime();

                        const isProcessedImageOutput = cacheBustUrl.match(/\.(jpeg|jpg|png)(\?.*)?$/i);
                        const isProcessedVideoOutput = cacheBustUrl.match(/\.(mp4|avi|mov|webm)(\?.*)?$/i);

                        if (isProcessedImageOutput) {
                            if(analyzedMediaImg) { analyzedMediaImg.src = cacheBustUrl; analyzedMediaImg.style.display = 'block'; }
                            if(analyzedMediaPlaceholder) analyzedMediaPlaceholder.style.display = 'none';
                        } else if (isProcessedVideoOutput) { 
                             if(analyzedMediaVideo) { analyzedMediaVideo.src = cacheBustUrl; analyzedMediaVideo.style.display = 'block'; analyzedMediaVideo.load(); }
                             if(analyzedMediaPlaceholder) analyzedMediaPlaceholder.style.display = 'none';
                        } else {

                            console.warn("Medio procesado con URL desconocida:", cacheBustUrl);
                            processedMediaAvailable = false; 
                        }
                    }
                }

                if (!processedMediaAvailable && analyzedMediaPlaceholder) {
                    if (data.original_media_type === 'audio' && data.analysis_text && data.analysis_text.toLowerCase().includes("audio contexto")) {
                         analyzedMediaPlaceholder.innerHTML = '<i class="fas fa-file-audio"></i> <p style="font-size:0.7em; margin-top:5px;text-align:center;">Análisis de audio completado</p>';
                    } else {
                         analyzedMediaPlaceholder.innerHTML = '<i class="fas fa-times-circle"></i> <p style="font-size:0.7em; margin-top:5px;text-align:center;">No hay vista procesada disponible</p>';
                    }
                }
            } catch (error) {
                console.error('Error al analizar:', error);
                if (analysisResultSection) analysisResultSection.textContent = `Error: ${error.message}`;
                 if (analyzedMediaPlaceholder) {
                    analyzedMediaPlaceholder.innerHTML = '<i class="fas fa-exclamation-triangle"></i> <p style="font-size:0.7em; margin-top:5px;text-align:center;">Fallo el análisis</p>';
                }
            } finally {
                if (mediaLoadingOverlay) mediaLoadingOverlay.classList.remove('visible');
            }
        });
    }

    const menuToggle = document.querySelector('.menu-toggle');
    const navWrapper = document.querySelector('.nav-wrapper');
    const mobileNavLinks = document.querySelectorAll('.mobile-nav .nav-link-mobile');

    function closeMobileMenu() {
        if (navWrapper && navWrapper.classList.contains('open')) {
            menuToggle.setAttribute('aria-expanded', 'false');
            navWrapper.classList.remove('open');
            const icon = menuToggle.querySelector('i');
            if (icon) {
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            }
        }
    }

    if (menuToggle && navWrapper) {
        menuToggle.addEventListener('click', () => {
            const isExpanded = menuToggle.getAttribute('aria-expanded') === 'true' || false;
            menuToggle.setAttribute('aria-expanded', !isExpanded);
            navWrapper.classList.toggle('open');
            const icon = menuToggle.querySelector('i');
            if (icon) {
                if (navWrapper.classList.contains('open')) {
                    icon.classList.remove('fa-bars');
                    icon.classList.add('fa-times');
                } else {
                    icon.classList.remove('fa-times');
                    icon.classList.add('fa-bars');
                }
            }
        });
        mobileNavLinks.forEach(link => { link.addEventListener('click', closeMobileMenu); });
    }

    const body = document.body;
    const themeToggles = document.querySelectorAll('.theme-toggle');
    const themeTransitionOverlay = document.getElementById('themeTransitionOverlay');

    const rootStyles = getComputedStyle(document.documentElement);
    const getCssVar = (name, fallback) => rootStyles.getPropertyValue(name).trim() || fallback;

    const themeAnimTotalDuration = parseFloat(getCssVar('--theme-anim-duration-total', '1s')) * 1000;
    const themeAnimBlurAmount = getCssVar('--theme-anim-blur-amount', '10px');
    const themeAnimBrightness = getCssVar('--theme-anim-brightness', '70%');
    
    const phase1Duration = themeAnimTotalDuration * 0.25;
    const phase2Duration = themeAnimTotalDuration * 0.25;
    const phase3Duration = themeAnimTotalDuration * 0.25;
    const phase4Duration = themeAnimTotalDuration * 0.25;

    function updateThemeIcons(theme) {
        themeToggles.forEach(toggle => {
            const themeIcon = toggle.querySelector('i');
            if (themeIcon) {
                themeIcon.classList.toggle('fa-moon', theme === 'light');
                themeIcon.classList.toggle('fa-sun', theme === 'dark');
            }
        });
    }

    function applyTheme(theme) {
        body.setAttribute('data-theme', theme);
        updateThemeIcons(theme);
        try {
            localStorage.setItem('vanguard-theme', theme);
        } catch (e) {
            console.warn("No se pudo guardar el tema en localStorage:", e);
        }
    }

    let savedTheme = 'light'; 
    try {
        savedTheme = localStorage.getItem('vanguard-theme') || (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    } catch (e) {
        console.warn("No se pudo leer el tema de localStorage:", e);
        savedTheme = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    }
    applyTheme(savedTheme);

    let isAnimatingTheme = false;
    themeToggles.forEach(toggle => {
        toggle.addEventListener('click', async () => {
            if (isAnimatingTheme || !themeTransitionOverlay) return;
            isAnimatingTheme = true;
            if (toggle.classList.contains('mobile-theme-toggle')) closeMobileMenu();
            const newTheme = body.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            
            themeTransitionOverlay.style.transition = 'none';
            Object.assign(themeTransitionOverlay.style, { 
                clipPath: 'circle(0% at center)', 
                opacity: '0', 
                backdropFilter: `blur(0px) brightness(100%)`, 
                pointerEvents: 'auto' 
            });
            themeTransitionOverlay.getBoundingClientRect();

            Object.assign(themeTransitionOverlay.style, {
                transitionProperty: 'clip-path, opacity, backdrop-filter',
                transitionDuration: `${phase1Duration}ms`,
                transitionTimingFunction: 'cubic-bezier(0.33, 1, 0.68, 1)', 
                opacity: '1', 
                clipPath: 'circle(150% at center)', 
                backdropFilter: `blur(${themeAnimBlurAmount}) brightness(${themeAnimBrightness})`
            });
            await new Promise(resolve => setTimeout(resolve, phase1Duration));
            
            Object.assign(themeTransitionOverlay.style, { 
                transitionDuration: `${phase2Duration}ms`, 
                transitionTimingFunction: 'cubic-bezier(0.65, 0, 0.35, 1)', 
                clipPath: 'circle(0% at center)' 
            });
            await new Promise(resolve => setTimeout(resolve, phase2Duration));
            
            applyTheme(newTheme);
            const currentIcon = toggle.querySelector('i');
            if (currentIcon) {
                Object.assign(currentIcon.style, { 
                    transition: 'transform 0.3s ease-in-out', 
                    transform: 'rotate(360deg)' 
                });
                setTimeout(() => {
                    currentIcon.style.transform = 'rotate(0deg)';
                    setTimeout(() => currentIcon.style.transition = '', 50);
                }, 300);
            }
            
            Object.assign(themeTransitionOverlay.style, { 
                transitionDuration: `${phase3Duration}ms`, 
                transitionTimingFunction: 'cubic-bezier(0.33, 1, 0.68, 1)',
                clipPath: 'circle(150% at center)' 
            });
            await new Promise(resolve => setTimeout(resolve, phase3Duration));
            
            Object.assign(themeTransitionOverlay.style, { 
                transitionDuration: `${phase4Duration}ms`, 
                transitionTimingFunction: 'cubic-bezier(0.25, 0.1, 0.25, 1)', 
                opacity: '0', 
                backdropFilter: `blur(0px) brightness(100%)` 
            });
            await new Promise(resolve => setTimeout(resolve, phase4Duration));
            
            themeTransitionOverlay.style.pointerEvents = 'none';
            isAnimatingTheme = false;
        });
    });

    try {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {

            if (!localStorage.getItem('vanguard-theme') && !isAnimatingTheme) {
                applyTheme(e.matches ? 'dark' : 'light');
            }
        });
    } catch (e) {
        console.warn("Error al añadir listener para prefers-color-scheme:", e);
    }
    

    const currentYearSpan = document.getElementById('currentYear');
    if (currentYearSpan) currentYearSpan.textContent = new Date().getFullYear();
});

document.querySelectorAll('[data-logout-container]').forEach(container => {
    const triggerIcon = container.querySelector('.logout-trigger i');

    const collapseButton = () => {
        container.classList.remove('expanded');

        if (triggerIcon) {
            triggerIcon.className = 'fas fa-power-off';
        }
    };

    container.addEventListener('click', async (e) => {
        e.stopPropagation();

        if (container.classList.contains('expanded')) {
            if (triggerIcon) {
                triggerIcon.className = 'fas fa-spinner fa-spin'; 
            }
            try {
                const response = await fetch('/api/logout', { method: 'POST' });
                if (response.ok) {
                    window.location.href = '/'; 
                } else {
                    const errorData = await response.json();
                    alert(`Error al cerrar sesión: ${errorData.error || 'Error'}`);
                    collapseButton(); 
                }
            } catch (error) {
                console.error('Error de red al cerrar sesión:', error);
                alert('Error de red. No se pudo cerrar la sesión.');
                collapseButton(); 
            }
        } 

        else {
            container.classList.add('expanded');
        }
    });

    document.addEventListener('click', (e) => {
        if (!container.contains(e.target)) {
            collapseButton();
        }
    });
});

const profileModalOverlay = document.getElementById('profile-modal-overlay');
const profileModal = document.getElementById('profile-modal');
const profileTriggers = document.querySelectorAll('.profile-trigger');
const closeProfileModalBtn = document.getElementById('close-profile-modal');
const profileForm = document.getElementById('profile-form');
const loader = document.getElementById('profile-modal-loader');
const modalBody = document.getElementById('profile-modal-body');

const openProfileModal = async () => {
    profileModalOverlay.classList.add('visible');
    loader.style.display = 'flex';
    modalBody.style.display = 'none';

    try {
        const response = await fetch('/api/user/profile');
        if (!response.ok) throw new Error('No se pudo cargar el perfil.');
        
        const user = await response.json();

        document.getElementById('profile-nombre').value = user.nombre_completo || '';
        document.getElementById('profile-apellidos').value = user.apellidos || '';
        document.getElementById('profile-correo').value = user.correo || '';
        document.getElementById('profile-celular').value = user.numero_celular || '';
        document.getElementById('profile-rol').value = user.rol || '';

        document.getElementById('profile-current-password').value = '';
        document.getElementById('profile-new-password').value = '';
        
        loader.style.display = 'none';
        modalBody.style.display = 'block';

    } catch (error) {
        console.error('Error al cargar perfil:', error);
        alert(error.message);
        closeProfileModal();
    }
};

const closeProfileModal = () => {
    profileModalOverlay.classList.remove('visible');
};

profileTriggers.forEach(btn => btn.addEventListener('click', openProfileModal));
closeProfileModalBtn.addEventListener('click', closeProfileModal);
profileModalOverlay.addEventListener('click', (e) => {
    if (e.target === profileModalOverlay) {
        closeProfileModal();
    }
});

profileForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const saveButton = document.getElementById('save-profile-button');
    const originalButtonText = saveButton.innerHTML;
    saveButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
    saveButton.disabled = true;

    const formData = new FormData(profileForm);
    const data = Object.fromEntries(formData.entries());

    if (!data.new_password) {
        delete data.new_password;
        delete data.current_password;
    }

    try {
        const response = await fetch('/api/user/profile', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || 'Ocurrió un error al actualizar.');
        }
        
        alert(result.message || 'Perfil actualizado con éxito');
        closeProfileModal();

    } catch (error) {
        console.error('Error al guardar perfil:', error);
        alert(error.message);
    } finally {
        saveButton.innerHTML = originalButtonText;
        saveButton.disabled = false;
    }
});