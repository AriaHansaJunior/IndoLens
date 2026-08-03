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
            uploadCard: document.getElementById('uploadCard'),
            fileInput: document.getElementById('fileInput'),
            
            // Progress
            progressContainer: document.getElementById('progressContainer'),
            statusText: document.getElementById('statusText'),
            progressBarFill: document.getElementById('progressBarFill'),
            
            // Buttons
            btnActorList: document.getElementById('btnActorList'),
            
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

        }
    },

    /* =========================================================================
       RESERVED METHODS - VIDEO PLAYER CONTROLS
       ========================================================================= */

    initializeVideo() {
        this.playDemo();
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
        this.elements.mainVideo.classList.add('video-crossfade');
        this.elements.videoFallback.style.display = 'none';
        this.elements.mainVideo.style.display = 'block';
        this.elements.mainVideo.src = videoUrl;
        this.elements.mainVideo.loop = true;
        this.elements.mainVideo.play().catch(e => console.warn('Autoplay error:', e));

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

    startRecognition(file) {
        this.isProcessing = true;
        this.toggleOverlay(false); // Hide overlay during processing
        this.showProgress('Uploading...');

        const formData = new FormData();
        formData.append('video', file);

        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

        // Step 1: Uploading...
        this.updateProgress('Uploading...', 25);

        fetch('/recognize', {
            method: 'POST',
            headers: {
                'X-CSRF-TOKEN': csrfToken || '',
                'Accept': 'application/json'
            },
            body: formData
        })
        .then(response => {
            this.updateProgress('Recognizing Faces...', 65);
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.message || 'Terjadi kesalahan saat pengenalan.'); });
            }
            return response.json();
        })
        .then(data => {
            this.updateProgress('Rendering Overlay...', 90);
            setTimeout(() => {
                this.receiveRecognition(data);
            }, 500);
        })
        .catch(error => {
            console.error('Recognition Failed:', error);
            this.hideProgress();
            this.isProcessing = false;
            this.showToast(error.message || 'Gagal memproses video.', 'error');
        });
    },

    receiveRecognition(data) {
        this.updateProgress('Completed', 100);
        this.recognitionData = data;
        this.isProcessing = false;
        this.currentMode = 'user';

        setTimeout(() => {
            this.hideProgress();
            if (data.output_video) {
                // Serve output video path
                const outputUrl = `/storage/ai/results/${data.output_video.split('/').pop()}`;
                this.replaceVideo(outputUrl);
            } else if (data.video_url) {
                this.replaceVideo(data.video_url);
            }

            this.replaceOverlay(data);
            this.showToast('Pengenalan wajah selesai!', 'success');
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
        this.elements.mainVideo.style.display = 'none';
        this.elements.videoFallback.style.display = 'flex';
    }
};
