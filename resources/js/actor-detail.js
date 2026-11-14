/**
 * IndoLens - Actor Detail Module
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
            statusBadge: document.getElementById('actorDetailStatusBadge'),
            nameGroup: document.querySelector('.actor-name-group'),
        };
    },

    initializePage() {
        this.renderFilmography();
    },

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

                if (this.elements.statusBadge) {
                    this.elements.statusBadge.textContent = isDetected ? 'KNOWN' : 'UNKNOWN';
                    this.elements.statusBadge.classList.toggle('status-known', isDetected);
                    this.elements.statusBadge.classList.toggle('status-unknown', !isDetected);
                }

                if (this.elements.charLabel) {
                    if (isDetected && charName) {
                        this.elements.charLabel.textContent = `Role: ${charName}`;
                        this.elements.charLabel.style.display = '';
                    } else {
                        this.elements.charLabel.style.display = 'none';
                    }
                }
            } catch (err) {
                // Ignore transient polling errors
            }
        }, 2000);
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
