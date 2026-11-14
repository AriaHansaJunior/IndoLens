/**
 * IndoLens - Actor List Module
 */

document.addEventListener('DOMContentLoaded', () => {
    ActorList.init();
});

const ActorList = {
    // State
    elements: {},
    cards: [],

    /**
     * Entry Point
     */
    init() {
        this.cacheDOM();
        this.initializeCards();
        this.initializeSearch();
        this.initializeRealtimeSync();
    },

    /**
     * Cache DOM Elements
     */
    cacheDOM() {
        this.elements = {
            searchInput: document.getElementById('actorSearchInput'),
            gridContainer: document.getElementById('actorsGrid'),
            emptyState: document.getElementById('emptyStateMessage'),
        };
    },

    initializeCards() {
        if (!this.elements.gridContainer) return;
        
        const cardElements = this.elements.gridContainer.querySelectorAll('.actor-card');
        this.cards = Array.from(cardElements).map(card => {
            const name = card.getAttribute('data-name') || '';
            const uuid = card.getAttribute('data-uuid') || '';

            card.addEventListener('click', (e) => {
                if (!e.target.closest('.btn-detail')) {
                    this.openActor(uuid);
                }
            });

            return {
                element: card,
                name: name.toLowerCase(),
                uuid: uuid,
            };
        });
    },

    /**
     * Initialize search input event listeners.
     */
    initializeSearch() {
        if (this.elements.searchInput) {
            this.elements.searchInput.addEventListener('input', (e) => {
                const query = e.target.value.toLowerCase().trim();
                this.filterActors(query);
            });
            
            // Clear search on ESC key
            this.elements.searchInput.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    this.clearSearch();
                }
            });
        }
    },

    /**
     * Filter cards based on search query (DOM Filtering).
     */
    filterActors(query) {
        let visibleCount = 0;

        this.cards.forEach(card => {
            if (query === '' || card.name.includes(query)) {
                card.element.classList.remove('hidden');
                visibleCount++;
            } else {
                card.element.classList.add('hidden');
            }
        });

        this.renderCards(visibleCount);
    },

    /**
     * Manage grid display state (e.g., show empty state message if no cards visible).
     */
    renderCards(visibleCount) {
        if (this.elements.emptyState) {
            if (visibleCount === 0) {
                this.elements.emptyState.style.display = 'block';
            } else {
                this.elements.emptyState.style.display = 'none';
            }
        }
    },

    openActor(uuid) {
        if (uuid) {
            window.location.href = `/actors/${uuid}`;
        }
    },

    /**
     * Reset search input and show all cards.
     */
    clearSearch() {
        if (this.elements.searchInput) {
            this.elements.searchInput.value = '';
            this.filterActors('');
        }
    },

    /**
     * Navigate back to Home page.
     */
    goBack() {
        window.location.href = '/';
    },

    /**
     * Start real-time sync with backend for actor detection status.
     */
    initializeRealtimeSync() {
        // Poll every 2 seconds
        setInterval(() => {
            this.fetchActiveActors();
        }, 2000);
    },

    async fetchActiveActors() {
        try {
            const response = await fetch('/api/actors/active');
            if (!response.ok) return;
            
            const data = await response.json();
            const activeActors = data.detected_actors || [];
            const characterMap = data.character_map || {};
            
            this.updateDOMStatus(activeActors, characterMap);
        } catch (error) {
            console.error('Failed to sync actor status:', error);
        }
    },

    updateDOMStatus(activeNames, characterMap = {}) {
        let hasChanges = false;

        // Normalisasi list nama aktif ke lowercase & trimmed
        const lowerActiveNames = (activeNames || []).map(n => String(n).toLowerCase().trim());
        
        // Normalisasi characterMap key ke lowercase & trimmed
        const lowerCharacterMap = {};
        Object.keys(characterMap || {}).forEach(k => {
            lowerCharacterMap[String(k).toLowerCase().trim()] = characterMap[k];
        });

        this.cards.forEach(card => {
            const originalName = card.element.getAttribute('data-name') || '';
            const lowerName = originalName.toLowerCase().trim();
            const isKnown = lowerActiveNames.includes(lowerName);
            
            const badge = card.element.querySelector('.status-badge');
            const roleLabel = card.element.querySelector('.actor-role-label');
            if (!badge) return;

            const currentStatus = badge.textContent.trim().toUpperCase();
            const newStatus = isKnown ? 'KNOWN' : 'UNKNOWN';

            if (currentStatus !== newStatus) {
                hasChanges = true;
                badge.textContent = newStatus;
                
                if (isKnown) {
                    badge.classList.remove('status-unknown');
                    badge.classList.add('status-known');
                    card.element.setAttribute('data-is-known', '1');
                } else {
                    badge.classList.remove('status-known');
                    badge.classList.add('status-unknown');
                    card.element.setAttribute('data-is-known', '0');
                }
            }

            // Update "Sebagai: ..." label dynamically (case-insensitive lookup)
            if (roleLabel) {
                const charName = lowerCharacterMap[lowerName];
                if (isKnown && charName) {
                    roleLabel.textContent = `Role: ${charName}`;
                    roleLabel.style.display = '';
                } else {
                    roleLabel.style.display = 'none';
                }
            }
        });

        if (hasChanges) {
            this.reorderGrid();
        }
    },

    reorderGrid() {
        if (!this.elements.gridContainer) return;
        
        // Pisahkan menjadi 2 grup: known dan unknown, masing-masing tetap sesuai urutan aslinya (alphabetical)
        const knownCards = [];
        const unknownCards = [];
        
        // Iterasi berdasarkan urutan saat ini di array cards
        this.cards.forEach(card => {
            if (card.element.getAttribute('data-is-known') === '1') {
                knownCards.push(card.element);
            } else {
                unknownCards.push(card.element);
            }
        });
        
        // Pindahkan elemen 'empty state' jika ada agar tidak tertimpa
        let defaultEmptyState = document.getElementById('emptyStateMessageDefault');
        let searchEmptyState = document.getElementById('emptyStateMessage');
        
        // Kosongkan grid (hapus card saja, jangan hapus empty state dari memory)
        knownCards.forEach(el => this.elements.gridContainer.appendChild(el));
        unknownCards.forEach(el => this.elements.gridContainer.appendChild(el));
        
        if (defaultEmptyState) this.elements.gridContainer.appendChild(defaultEmptyState);
        if (searchEmptyState) this.elements.gridContainer.appendChild(searchEmptyState);
    }
};
