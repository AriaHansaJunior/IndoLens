/**
 * IndoLens - Actor Detail Script
 * Implementation of Session 11 Workflow & Reserved Methods
 */

document.addEventListener('DOMContentLoaded', () => {
    ActorDetail.init();
});

const ActorDetail = {
    // State
    elements: {},

    /**
     * Entry Point
     */
    init() {
        this.cacheDOM();
        this.initializePage();
    },

    /**
     * Cache DOM Elements
     */
    cacheDOM() {
        this.elements = {
            btnBack: document.getElementById('btnBack'),
            filmographyList: document.getElementById('filmographyList'),
        };
    },

    /* =========================================================================
       RESERVED METHODS
       ========================================================================= */

    /**
     * Initialize page components.
     */
    initializePage() {
        this.bindBackButton();
        this.renderFilmography();
    },

    /**
     * Bind Back Button Event.
     * Hardlink is preferred per requirement, but this method is reserved for future dynamic handling.
     */
    bindBackButton() {
        if (this.elements.btnBack) {
            // Already handled via native href="/actors"
            // Adding a visual ripple or custom event could be placed here.
        }
    },

    /**
     * Render filmography items if additional client-side parsing is needed.
     * Currently rendered via Blade, but this is reserved for future enhancements (e.g. infinite scroll).
     */
    renderFilmography() {
        // Example: add animation delay to each list item for a cascade effect
        if (this.elements.filmographyList) {
            const items = this.elements.filmographyList.querySelectorAll('li');
            items.forEach((item, index) => {
                item.style.opacity = '0';
                item.style.animation = `fadeIn 0.3s ease forwards ${index * 0.1}s`;
            });
        }
    }
};
