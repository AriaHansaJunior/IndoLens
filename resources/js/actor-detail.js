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
        this.initializeRealtimeSync();
    },

    /**
     * Cache DOM Elements
     */
    cacheDOM() {
        this.elements = {
            filmographyList: document.getElementById('filmographyList'),
            charLabel: document.getElementById('actorCharacterLabel'),
            nameGroup: document.querySelector('.actor-name-group'),
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
     * Real-time sync with API to update character / hint dynamically.
     */
    initializeRealtimeSync() {
        if (!this.elements.nameGroup) return;

        const actorName = (this.elements.nameGroup.getAttribute('data-actor-name') || '').toLowerCase().trim();

        setInterval(async () => {
            try {
                const response = await fetch('/api/actors/active');
                if (!response.ok) return;

                const data = await response.json();
                const activeActors = (data.detected_actors || []).map(n => String(n).toLowerCase().trim());
                const charMap = {};
                Object.keys(data.character_map || {}).forEach(k => {
                    charMap[String(k).toLowerCase().trim()] = data.character_map[k];
                });

                const isDetected = activeActors.includes(actorName);
                const charName = charMap[actorName];

                if (isDetected && charName) {
                    if (this.elements.charLabel) {
                        this.elements.charLabel.textContent = `Role: ${charName}`;
                        this.elements.charLabel.style.display = '';
                    }
                } else {
                    if (this.elements.charLabel) {
                        this.elements.charLabel.style.display = 'none';
                    }
                }
            } catch (err) {
                // Ignore background polling errors
            }
        }, 2000);
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
        if (this.elements.filmographyList) {
            const items = this.elements.filmographyList.querySelectorAll('li');
            items.forEach((item, index) => {
                item.style.animation = `fadeIn 0.3s ease forwards ${index * 0.08}s`;
            });
        }
    }
};
