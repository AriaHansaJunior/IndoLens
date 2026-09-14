/**
 * IndoLens - Camp Administration Module (Session 6)
 * Handles client-side confirmations, multiple face image preview, age calculation, and modal workflows.
 */

document.addEventListener('DOMContentLoaded', () => {
    CampManager.init();
});

const CampManager = {
    init() {
        this.initDeleteActorModal();
        this.initCreateConfirmation();
        this.initEditConfirmation();
        this.initFaceImageManagement();
        this.initAgeCalculator();
        this.initPhotoPreview();
    },

    /**
     * 1. Delete Actor Confirmation Modal
     */
    initDeleteActorModal() {
        const backdrop = document.getElementById('deleteModalBackdrop');
        const targetNameEl = document.getElementById('deleteTargetActorName');
        const deleteForm = document.getElementById('deleteActorForm');
        const btnCancel = document.getElementById('btnCancelDelete');

        if (!backdrop || !deleteForm) return;

        document.querySelectorAll('.js-btn-delete').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const actorId = btn.getAttribute('data-actor-id');
                const actorName = btn.getAttribute('data-actor-name');

                deleteForm.action = `/camp/${actorId}`;
                if (targetNameEl) {
                    targetNameEl.textContent = actorName;
                }

                backdrop.style.display = 'flex';
            });
        });

        if (btnCancel) {
            btnCancel.addEventListener('click', () => {
                backdrop.style.display = 'none';
            });
        }

        backdrop.addEventListener('click', (e) => {
            if (e.target === backdrop) {
                backdrop.style.display = 'none';
            }
        });
    },

    /**
     * 2. Create Actor Confirmation Modal
     */
    initCreateConfirmation() {
        const form = document.getElementById('createActorForm');
        const btnTrigger = document.getElementById('btnTriggerCreateConfirm');
        const modal = document.getElementById('createConfirmModal');
        const btnCancel = document.getElementById('btnCancelCreate');
        const btnProceed = document.getElementById('btnProceedCreate');

        if (!form || !btnTrigger || !modal) return;

        btnTrigger.addEventListener('click', (e) => {
            e.preventDefault();
            // Trigger native HTML5 validation first
            if (!form.checkValidity()) {
                form.reportValidity();
                return;
            }
            modal.style.display = 'flex';
        });

        if (btnCancel) {
            btnCancel.addEventListener('click', () => {
                modal.style.display = 'none';
            });
        }

        if (btnProceed) {
            btnProceed.addEventListener('click', () => {
                modal.style.display = 'none';
                form.submit();
            });
        }

        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.style.display = 'none';
        });
    },

    /**
     * 3. Edit Actor Confirmation Modal
     */
    initEditConfirmation() {
        const form = document.getElementById('editActorForm');
        const btnTrigger = document.getElementById('btnTriggerEditConfirm');
        const modal = document.getElementById('editConfirmModal');
        const btnCancel = document.getElementById('btnCancelEdit');
        const btnProceed = document.getElementById('btnProceedEdit');

        if (!form || !btnTrigger || !modal) return;

        btnTrigger.addEventListener('click', (e) => {
            e.preventDefault();
            if (!form.checkValidity()) {
                form.reportValidity();
                return;
            }
            modal.style.display = 'flex';
        });

        if (btnCancel) {
            btnCancel.addEventListener('click', () => {
                modal.style.display = 'none';
            });
        }

        if (btnProceed) {
            btnProceed.addEventListener('click', () => {
                modal.style.display = 'none';
                form.submit();
            });
        }

        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.style.display = 'none';
        });
    },

    /**
     * 4. Multiple Face Image Selection & Management
     */
    initFaceImageManagement() {
        const fileInput = document.getElementById('faceImagesInput');
        const dropzone = document.getElementById('facesDropzone');
        const previewContainer = document.getElementById('selectedFilesContainer');
        const countText = document.getElementById('selectedCountText');
        const grid = document.getElementById('selectedThumbnailsGrid');
        const btnClear = document.getElementById('btnClearSelection');
        const btnUploadTrigger = document.getElementById('btnTriggerUploadConfirm');
        const uploadModal = document.getElementById('uploadConfirmModal');
        const uploadCountSummary = document.getElementById('uploadCountSummary');
        const btnCancelUpload = document.getElementById('btnCancelUpload');
        const btnProceedUpload = document.getElementById('btnProceedUpload');
        const uploadForm = document.getElementById('uploadFacesForm');

        // Delete face image modal elements
        const deleteFaceModal = document.getElementById('deleteFaceModal');
        const deleteTargetFaceName = document.getElementById('deleteTargetFaceName');
        const deleteFaceForm = document.getElementById('deleteFaceForm');
        const btnCancelDeleteFace = document.getElementById('btnCancelDeleteFace');

        if (fileInput) {
            fileInput.addEventListener('change', () => {
                this.renderSelectedFiles(fileInput.files, previewContainer, countText, grid, btnUploadTrigger);
            });

            if (btnClear) {
                btnClear.addEventListener('click', () => {
                    fileInput.value = '';
                    this.renderSelectedFiles([], previewContainer, countText, grid, btnUploadTrigger);
                });
            }

            // Drag & Drop visual state
            if (dropzone) {
                ['dragenter', 'dragover'].forEach(eventName => {
                    dropzone.addEventListener(eventName, (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        dropzone.classList.add('dragover');
                    });
                });

                ['dragleave', 'drop'].forEach(eventName => {
                    dropzone.addEventListener(eventName, (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        dropzone.classList.remove('dragover');
                    });
                });
            }

            // Upload confirmation modal
            if (btnUploadTrigger && uploadModal && uploadForm) {
                btnUploadTrigger.addEventListener('click', (e) => {
                    e.preventDefault();
                    const count = fileInput.files ? fileInput.files.length : 0;
                    if (count === 0) return;

                    if (uploadCountSummary) {
                        uploadCountSummary.textContent = `${count} ${count === 1 ? 'image' : 'images'} will be uploaded.`;
                    }
                    uploadModal.style.display = 'flex';
                });

                if (btnCancelUpload) {
                    btnCancelUpload.addEventListener('click', () => {
                        uploadModal.style.display = 'none';
                    });
                }

                if (btnProceedUpload) {
                    btnProceedUpload.addEventListener('click', () => {
                        uploadModal.style.display = 'none';
                        uploadForm.submit();
                    });
                }

                uploadModal.addEventListener('click', (e) => {
                    if (e.target === uploadModal) uploadModal.style.display = 'none';
                });
            }
        }

        // Handle Delete Face Image modal
        if (deleteFaceModal && deleteFaceForm) {
            document.querySelectorAll('.js-btn-delete-face').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    const actorId = btn.getAttribute('data-actor-id');
                    const imageId = btn.getAttribute('data-image-id');
                    const imageName = btn.getAttribute('data-image-name');

                    deleteFaceForm.action = `/camp/${actorId}/faces/${imageId}`;
                    if (deleteTargetFaceName) {
                        deleteTargetFaceName.textContent = imageName;
                    }
                    deleteFaceModal.style.display = 'flex';
                });
            });

            if (btnCancelDeleteFace) {
                btnCancelDeleteFace.addEventListener('click', () => {
                    deleteFaceModal.style.display = 'none';
                });
            }

            deleteFaceModal.addEventListener('click', (e) => {
                if (e.target === deleteFaceModal) deleteFaceModal.style.display = 'none';
            });
        }
    },

    renderSelectedFiles(files, container, countText, grid, btnTrigger) {
        if (!container || !countText || !grid) return;

        grid.innerHTML = '';
        const count = files ? files.length : 0;

        if (count === 0) {
            container.style.display = 'none';
            if (btnTrigger) btnTrigger.disabled = true;
            return;
        }

        container.style.display = 'block';
        countText.textContent = `${count} ${count === 1 ? 'image' : 'images'} selected`;
        if (btnTrigger) btnTrigger.disabled = false;

        Array.from(files).forEach(file => {
            const item = document.createElement('div');
            item.className = 'selected-thumb-item';

            const img = document.createElement('img');
            img.src = URL.createObjectURL(file);
            img.alt = file.name;
            img.title = file.name;

            item.appendChild(img);
            grid.appendChild(item);
        });
    },

    /**
     * 5. Age Calculator from Birth Date
     */
    initAgeCalculator() {
        const birthDateInput = document.getElementById('birth_date');
        const ageInput = document.getElementById('age');

        if (!birthDateInput || !ageInput) return;

        birthDateInput.addEventListener('change', () => {
            const dateVal = birthDateInput.value;
            if (!dateVal) return;

            const birthDate = new Date(dateVal);
            const today = new Date();

            let age = today.getFullYear() - birthDate.getFullYear();
            const monthDiff = today.getMonth() - birthDate.getMonth();

            if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
                age--;
            }

            if (age >= 0 && age <= 150) {
                ageInput.value = age;
            }
        });
    },

    /**
     * 6. Profile Photo Preview
     */
    initPhotoPreview() {
        const photoInput = document.getElementById('photo');
        const previewWrap = document.getElementById('photoPreviewContainer');
        const previewImg = document.getElementById('photoPreviewImg');
        const previewName = document.getElementById('photoPreviewName');

        if (!photoInput || !previewWrap || !previewImg) return;

        photoInput.addEventListener('change', () => {
            const file = photoInput.files && photoInput.files[0];
            if (file) {
                previewImg.src = URL.createObjectURL(file);
                if (previewName) previewName.textContent = file.name;
                previewWrap.style.display = 'flex';
            } else {
                previewWrap.style.display = 'none';
            }
        });
    }
};
