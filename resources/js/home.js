/**
 * IndoLens - Home Main Interface Script
 * Implementation of Session 9 Workflow & Reserved Methods
 */

document.addEventListener('DOMContentLoaded', () => {
    IndoLensHome.init();
});

const IndoLensHome = {
    // State Properties
    currentMode: 'demo', // 'demo' | 'user'
    isProcessing: false,
    selectedActorId: null,
    recognitionData: null,
    demoVideoPath: '/videos/demo.mp4',

    // DOM References
    elements: {},

    /**
     * Entry Point Initialization
     */
    init() {
        this.cacheDOM();
        this.bindEvents();
        this.initializeVideo();
        this.initializeUpload();
    },

    /**
     * Cache DOM Elements
     */
    cacheDOM() {
        this.elements = {
            mainVideo: document.getElementById('mainVideo'),
            videoFallback: document.getElementById('videoFallback'),
            videoWrapper: document.getElementById('videoWrapper'),
            overlayLayer: document.getElementById('videoOverlayLayer'),
            pausePanel: document.getElementById('pauseMetadataPanel'),
            
            // Upload
            uploadSection: document.getElementById('uploadSection'),
            uploadCard: document.getElementById('uploadCard'),
            fileInput: document.getElementById('fileInput'),
            
            // Progress
            progressContainer: document.getElementById('progressContainer'),
            statusText: document.getElementById('statusText'),
            progressBarFill: document.getElementById('progressBarFill'),
            
            // Buttons
            btnActorList: document.getElementById('btnActorList'),
            btnUploadNew: document.getElementById('btnUploadNew'),
            btnResetSession: document.getElementById('btnResetSession'),
            
            // Toast
            toastContainer: document.getElementById('toastContainer'),
        };
    },

    /**
     * Bind Event Listeners
     */
    bindEvents() {
        if (this.elements.uploadCard) {
            this.elements.uploadCard.addEventListener('click', () => {
                if (!this.isProcessing) this.elements.fileInput.click();
            });

            this.elements.uploadCard.addEventListener('dragover', (e) => {
                e.preventDefault();
                if (!this.isProcessing) this.elements.uploadCard.classList.add('drag-over');
            });

            this.elements.uploadCard.addEventListener('dragleave', () => {
                this.elements.uploadCard.classList.remove('drag-over');
            });

            this.elements.uploadCard.addEventListener('drop', (e) => {
                e.preventDefault();
                this.elements.uploadCard.classList.remove('drag-over');
                if (this.isProcessing) return;
                
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    this.handleFileSelect(files[0]);
                }
            });
        }

        if (this.elements.btnUploadNew) {
            this.elements.btnUploadNew.addEventListener('click', () => {
                if (!this.isProcessing && this.elements.fileInput) {
                    this.elements.fileInput.click();
                }
            });
        }

        if (this.elements.btnResetSession) {
            this.elements.btnResetSession.addEventListener('click', () => {
                if (!this.isProcessing) {
                    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
                    fetch('/reset', {
                        method: 'POST',
                        headers: {
                            'X-CSRF-TOKEN': csrfToken || '',
                            'Accept': 'application/json'
                        }
                    }).then(() => {
                        window.location.reload();
                    }).catch(() => {
                        window.location.reload();
                    });
                }
            });
        }

        if (this.elements.fileInput) {
            this.elements.fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    this.handleFileSelect(e.target.files[0]);
                }
            });
        }

        if (this.elements.mainVideo) {
            this.elements.mainVideo.addEventListener('pause', () => {
                this.handleVideoPause();
            });

            this.elements.mainVideo.addEventListener('play', () => {
                this.handleVideoPlay();
            });

            this.elements.mainVideo.addEventListener('error', () => {
                this.handleVideoError();
            });
        }
    },

    /* =========================================================================
       RESERVED METHODS - VIDEO PLAYER CONTROLS
       ========================================================================= */

    initializeVideo() {
        const config = window.INDO_LENS_CONFIG || {};
        if (config.hasActiveVideo && config.currentVideoUrl) {
            this.currentMode = 'user';
            this.replaceVideo(config.currentVideoUrl);
            if (config.recognitionData) {
                this.receiveRecognition(config.recognitionData);
            }
        } else {
            this.playDemo();
        }
    },

    playDemo() {
        this.currentMode = 'demo';
        this.elements.videoFallback.style.display = 'none';
        this.elements.mainVideo.style.display = 'block';
        this.elements.mainVideo.src = this.demoVideoPath;
        this.elements.mainVideo.loop = true;
        this.elements.mainVideo.muted = true;

        const playPromise = this.elements.mainVideo.play();
        if (playPromise !== undefined) {
            playPromise.catch(() => {
                // If demo video is missing or autoplay blocked, show fallback
                this.handleVideoError();
            });
        }
        this.toggleOverlay(false);
        this.disableActorButton();
    },

    replaceVideo(videoUrl) {
        console.log('[IndoLens] [replaceVideo] Called');
        console.log('[IndoLens] [replaceVideo] Received URL:', videoUrl);
        console.log('[IndoLens] [replaceVideo] videoElement:', this.elements.mainVideo);
        console.log('[IndoLens] [replaceVideo] src BEFORE:', this.elements.mainVideo ? this.elements.mainVideo.src : 'NULL');

        if (!this.elements.mainVideo) {
            console.error('[IndoLens] [replaceVideo] ERROR: #mainVideo element not found in DOM!');
            return;
        }

        this.elements.mainVideo.classList.add('video-crossfade');
        if (this.elements.videoFallback) {
            this.elements.videoFallback.style.display = 'none';
        }
        
        // Fix: Make sure controls are shown so the timeline is visible!
        if (this.currentMode !== 'demo') {
            this.elements.mainVideo.controls = true;
        }

        this.elements.mainVideo.style.display = 'block';
        this.elements.mainVideo.muted = true;
        this.elements.mainVideo.src = videoUrl;
        
        console.log('[IndoLens] [replaceVideo] src AFTER:', this.elements.mainVideo.src);

        // Explicitly reload video element with new source
        this.elements.mainVideo.load();

        const playPromise = this.elements.mainVideo.play();
        if (playPromise !== undefined) {
            playPromise.then(() => {
                console.log('[IndoLens] [replaceVideo] video.play() SUCCESS!');
            }).catch(e => {
                console.warn('[IndoLens] [replaceVideo] video.play() rejected:', e);
            });
        }
        
        // Add left/right keyboard scrubbing just in case browser controls don't capture it
        if (!this._hasBoundVideoKeys) {
            this._hasBoundVideoKeys = true;
            document.addEventListener('keydown', (e) => {
                if (this.currentMode === 'demo' || !this.elements.mainVideo) return;
                // Ignore if typing in an input field
                if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;

                if (e.key === 'ArrowRight') {
                    e.preventDefault();
                    this.elements.mainVideo.currentTime = Math.min(this.elements.mainVideo.duration, this.elements.mainVideo.currentTime + 5);
                } else if (e.key === 'ArrowLeft') {
                    e.preventDefault();
                    this.elements.mainVideo.currentTime = Math.max(0, this.elements.mainVideo.currentTime - 5);
                }
            });
        }

        setTimeout(() => {
            this.elements.mainVideo.classList.remove('video-crossfade');
        }, 300);
    },

    /* =========================================================================
       RESERVED METHODS - UPLOAD & RECOGNITION FLOW
       ========================================================================= */

    initializeUpload() {
        if (this.elements.fileInput) {
            this.elements.fileInput.value = '';
        }
    },

    handleFileSelect(file) {
        if (!this.validateVideo(file)) return;
        this.startRecognition(file);
    },

    validateVideo(file) {
        const allowedExtensions = ['mp4', 'mov', 'avi', 'mkv'];
        const fileName = file.name || '';
        const ext = fileName.split('.').pop().toLowerCase();

        if (!allowedExtensions.includes(ext)) {
            this.showToast('Format video tidak didukung. Gunakan MP4, MOV, AVI, atau MKV.', 'error');
            return false;
        }

        // Max size 50MB (51200 KB) as configured in recognition.php
        const maxSizeMB = 50;
        if (file.size > maxSizeMB * 1024 * 1024) {
            this.showToast(`Ukuran video melebihi batas maksimum ${maxSizeMB}MB.`, 'error');
            return false;
        }

        return true;
    },

    pollTimer: null,

    startRecognition(file) {
        this.isProcessing = true;
        this.currentMode = 'user';
        this.toggleOverlay(false);

        if (this.elements.uploadSection) this.elements.uploadSection.style.display = 'none';
        if (this.elements.btnUploadNew) this.elements.btnUploadNew.style.display = 'none';

        // Show instant preview (paused)
        try {
            const previewUrl = URL.createObjectURL(file);
            this.replaceVideo(previewUrl);
            this.elements.mainVideo.pause();
        } catch (e) {
            console.warn('[IndoLens] Failed to create local preview URL:', e);
        }

        this.showProgress('Uploading Video...');

        const formData = new FormData();
        formData.append('video', file);

        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

        this.updateProgress('Uploading Video...', 15);

        fetch('/upload', {
            method: 'POST',
            headers: {
                'X-CSRF-TOKEN': csrfToken || '',
                'Accept': 'application/json'
            },
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.message || 'Gagal mengunggah video.'); });
            }
            return response.json();
        })
        .then(uploadData => {
            console.log('[IndoLens] Upload Success:', uploadData);
            
            // Show uploaded video from server (paused)
            if (uploadData.video_url) {
                this.replaceVideo(uploadData.video_url);
                this.elements.mainVideo.pause();
            }

            const videoToken = uploadData.video_token;
            this.updateProgress('Mengenali Wajah... (mohon tunggu)', 30);

            // Simulate progress to keep UI alive during synchronous wait
            let fakeProgress = 30;
            const progressTimer = setInterval(() => {
                if (fakeProgress < 90) {
                    fakeProgress += Math.random() * 5;
                    this.updateProgress('Mengenali Wajah... (mohon tunggu)', fakeProgress);
                }
            }, 1000);

            // Step 2: Run recognition synchronously - server will respond when done
            return fetch('/recognize', {
                method: 'POST',
                headers: {
                    'X-CSRF-TOKEN': csrfToken || '',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ video_token: videoToken })
            })
            .then(recResponse => {
                clearInterval(progressTimer);
                if (!recResponse.ok) {
                    return recResponse.json().then(err => { throw new Error(err.message || 'Terjadi kesalahan saat pengenalan.'); });
                }
                return recResponse.json();
            })
            .then(recData => {
                console.log('[IndoLens] Recognition Complete:', recData);
                this.receiveRecognition(recData);
            })
            .catch(err => {
                clearInterval(progressTimer);
                throw err;
            });
        })
        .catch(error => {
            console.error('Process Failed:', error);
            this.hideProgress();
            this.isProcessing = false;
            if (this.elements.uploadSection) this.elements.uploadSection.style.display = 'block';
            this.showToast(error.message || 'Gagal memproses video.', 'error');
        });
    },

    receiveRecognition(data) {
        this.updateProgress('Completed', 100);
        this.recognitionData = data;
        this.isProcessing = false;
        this.currentMode = 'user';

        if (this.elements.uploadSection) this.elements.uploadSection.style.display = 'none';
        if (this.elements.btnUploadNew) this.elements.btnUploadNew.style.display = 'inline-flex';

        setTimeout(() => {
            this.hideProgress();
            
            // Extract output video URL from root or nested data object
            const outputUrl = data.video_url || data.output_video || 
                             (data.data && (data.data.video_url || data.data.output_video));
            
            if (outputUrl) {
                const finalUrl = outputUrl.startsWith('http') || outputUrl.startsWith('/') 
                    ? outputUrl 
                    : `/results/${outputUrl.split(/[\/\\]/).pop()}`;
                this.replaceVideo(finalUrl);
                // Keep video paused - user clicks play manually
                this.elements.mainVideo.pause();
            }

            this.replaceOverlay(data);
            this.showToast('Pengenalan wajah selesai! Klik Play untuk memutar.', 'success');
        }, 400);
    },

    /* =========================================================================
       RESERVED METHODS - PROGRESS & OVERLAY CONTROLS
       ========================================================================= */

    showProgress(initialStatus = 'Processing...') {
        this.elements.progressContainer.classList.add('active');
        this.elements.statusText.innerHTML = `<div class="spinner"></div> <span>${initialStatus}</span>`;
        this.elements.progressBarFill.style.width = '10%';
    },

    hideProgress() {
        this.elements.progressContainer.classList.remove('active');
    },

    updateProgress(statusMessage, percentage = 0) {
        this.elements.statusText.innerHTML = `<div class="spinner"></div> <span>${statusMessage}</span>`;
        this.elements.progressBarFill.style.width = `${percentage}%`;
    },

    replaceOverlay(data) {
        this.toggleOverlay(true);
        
        // Extract detected actors if any
        if (data && data.actors && data.actors.length > 0) {
            const firstActor = data.actors[0];
            this.selectedActorId = firstActor.id || firstActor.name;
            this.enableActorButton();
        } else {
            this.disableActorButton();
        }
    },

    toggleOverlay(show) {
        if (show) {
            this.elements.overlayLayer.classList.add('active');
        } else {
            this.elements.overlayLayer.classList.remove('active');
            this.elements.pausePanel.classList.remove('active');
        }
    },

    /* =========================================================================
       RESERVED METHODS - PAUSE MODE & BUTTON STATES
       ========================================================================= */

    handleVideoPause() {
        if (this.currentMode === 'user' && this.recognitionData) {
            // Show metadata in pause mode
            if (this.recognitionData.actors && this.recognitionData.actors.length > 0) {
                const actor = this.recognitionData.actors[0];
                document.getElementById('metaActorName').textContent = actor.name || 'Terdeteksi';
                document.getElementById('metaCharacter').textContent = actor.character ? `Sebagai: ${actor.character}` : '';
                document.getElementById('metaAge').textContent = actor.age ? `Umur: ${actor.age} thn` : '';
                document.getElementById('metaFilmography').textContent = actor.filmography ? `Film: ${actor.filmography.join(', ')}` : '';
                
                this.elements.pausePanel.classList.add('active');
            }
        }
    },

    handleVideoPlay() {
        this.elements.pausePanel.classList.remove('active');
    },

    enableActorButton() {
        // Reserved stub (Actor List is always active)
    },

    disableActorButton() {
        // Reserved stub (Actor List is always active)
    },

    /* =========================================================================
       RESERVED METHODS - POPUP MODAL & TOAST
       ========================================================================= */

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;

        this.elements.toastContainer.appendChild(toast);

        setTimeout(() => toast.classList.add('show'), 10);

        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    },

    hideToast() {
        if (this.elements.toastContainer) {
            this.elements.toastContainer.innerHTML = '';
        }
    },

    handleVideoError() {
        console.warn('[IndoLens] [handleVideoError] Triggered. currentMode:', this.currentMode);
        if (this.currentMode === 'demo') {
            if (this.elements.mainVideo) this.elements.mainVideo.style.display = 'none';
            if (this.elements.videoFallback) this.elements.videoFallback.style.display = 'flex';
        }
    }
};
