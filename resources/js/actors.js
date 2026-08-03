/**
 * IndoLens - Actor List Script
 * Implementation of Session 10 Workflow & Reserved Methods
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

    /* =========================================================================
       RESERVED METHODS
       ========================================================================= */

    /**
     * Initialize card elements and bind click events.
     */
    initializeCards() {
        if (!this.elements.gridContainer) return;
        
        // Cache all actor cards for quick filtering
        const cardElements = this.elements.gridContainer.querySelectorAll('.actor-card');
        this.cards = Array.from(cardElements).map(card => {
            // Get actor name from data attribute or fallback to text content
            const name = card.getAttribute('data-name') || '';
            const id = card.getAttribute('data-id') || '';
            
            // Bind click event for the whole card if needed
            card.addEventListener('click', (e) => {
                // Prevent opening twice if they clicked the button directly
                if (!e.target.closest('.btn-detail')) {
                    this.openActor(id);
                }
            });

            return {
                element: card,
                name: name.toLowerCase(),
                id: id
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

    /**
     * Navigate to Actor Detail page.
     */
    openActor(id) {
        if (id) {
            window.location.href = `/actors/${id}`;
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
    }
};
