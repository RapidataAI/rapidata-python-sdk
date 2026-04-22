// Rapids campaign preview embed.
// Mirrors the behavior of PhonePreview in app-frontend:
// - swaps iframe src based on which code-snippet tab is selected
// - refresh button increments &refreshCount=N to force a fresh session
// - on each src change, the iframe element is replaced (destroy + recreate),
//   matching `key={url}` in app-frontend so parent history stays clean
// - sends {viewable: true} postMessage to rapids.rapidata.ai on load

const RAPIDS_ORIGIN = 'https://rapids.rapidata.ai';

function buildPreviewUrl(campaignId, refreshCount) {
    const params = new URLSearchParams({
        id: campaignId,
        language: 'en',
        userSegment: '0',
        refreshCount: String(refreshCount),
    });
    return `${RAPIDS_ORIGIN}/preview/campaign?${params.toString()}`;
}

function findPrecedingTabbedSet(el) {
    // Walk previous siblings, then step up to parents if we run out.
    let cur = el.previousElementSibling;
    while (cur) {
        if (cur.classList && cur.classList.contains('tabbed-set')) return cur;
        // Occasionally the tabbed-set is nested inside a wrapper; look inside.
        const nested = cur.querySelector && cur.querySelector('.tabbed-set');
        if (nested) return nested;
        cur = cur.previousElementSibling;
    }
    if (el.parentElement && el.parentElement !== document.body) {
        return findPrecedingTabbedSet(el.parentElement);
    }
    return null;
}

function labelTextForInput(tabbedSet, input) {
    const label = tabbedSet.querySelector(`label[for="${input.id}"]`);
    if (!label) return null;
    return (label.textContent || '').trim();
}

function initPreviewEmbed(wrapper) {
    // Two modes:
    //   - data-preview-map='{"Image":"cmp_...",...}' — tab-synced; swap
    //     iframe when the preceding tabbed-set's active tab changes.
    //   - data-preview-campaign="cmp_..." — static; just the refresh
    //     button is wired up.
    const rawMap = wrapper.getAttribute('data-preview-map');
    const staticId = wrapper.getAttribute('data-preview-campaign');

    let campaignMap = null;
    if (rawMap) {
        try {
            campaignMap = JSON.parse(rawMap);
        } catch (err) {
            console.warn('[preview-embed] invalid data-preview-map JSON:', err);
        }
    }

    // Only bind to a tabbed-set when we have a mapping to drive.
    const tabbedSet = campaignMap ? findPrecedingTabbedSet(wrapper) : null;
    const refreshBtn = wrapper.querySelector('[data-preview-refresh]');
    let refreshCount = 0;

    function currentCampaignId() {
        if (tabbedSet && campaignMap) {
            const checked = tabbedSet.querySelector('input[type="radio"]:checked');
            if (checked) {
                const name = labelTextForInput(tabbedSet, checked);
                if (name && campaignMap[name]) return campaignMap[name];
            }
        }
        if (staticId) return staticId;
        // Final fallback: whatever id the iframe already has.
        const iframe = wrapper.querySelector('iframe.phone-preview__iframe');
        if (iframe && iframe.src) {
            try {
                return new URL(iframe.src).searchParams.get('id');
            } catch (_err) {
                return null;
            }
        }
        return null;
    }

    function attachIframeLoadHandler(iframe) {
        iframe.addEventListener('load', () => {
            try {
                iframe.contentWindow.postMessage(
                    { viewable: true, timestamp: Date.now() },
                    RAPIDS_ORIGIN,
                );
            } catch (_err) {
                // Cross-origin guard, shouldn't happen but ignore.
            }
        }, { once: false });
    }

    // Attach to the initial iframe rendered in HTML.
    const initialIframe = wrapper.querySelector('iframe.phone-preview__iframe');
    if (initialIframe) attachIframeLoadHandler(initialIframe);

    function renderIframe({ resetRefresh = false } = {}) {
        const id = currentCampaignId();
        if (!id) return;
        if (resetRefresh) refreshCount = 0;
        const url = buildPreviewUrl(id, refreshCount);
        const old = wrapper.querySelector('iframe.phone-preview__iframe');
        if (!old) return;
        if (old.src === url) return;

        // Destroy + recreate to avoid polluting parent history on src change.
        const fresh = old.cloneNode(false);
        fresh.src = url;
        attachIframeLoadHandler(fresh);
        old.replaceWith(fresh);
    }

    if (tabbedSet) {
        tabbedSet.querySelectorAll('input[type="radio"]').forEach((input) => {
            input.addEventListener('change', () => renderIframe({ resetRefresh: true }));
        });
    }

    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            refreshCount += 1;
            renderIframe();
            refreshBtn.classList.remove('is-refreshing');
            // Force reflow so the animation retriggers on each click.
            void refreshBtn.offsetWidth;
            refreshBtn.classList.add('is-refreshing');
        });
    }

    // Sync once in case the page loaded with a non-default tab (e.g. deep link).
    renderIframe();
}

function initAllPreviewEmbeds() {
    document.querySelectorAll('[data-preview-embed]').forEach((wrapper) => {
        if (wrapper.dataset.previewEmbedInit === '1') return;
        wrapper.dataset.previewEmbedInit = '1';
        initPreviewEmbed(wrapper);
    });
}

// Material for MkDocs exposes a `document$` RxJS subject that emits the
// current document on subscribe AND every time instant-navigation swaps
// the <main> content. Subscribing covers both the initial render and
// subsequent page navigations — a plain DOMContentLoaded listener would
// only fire on hard loads, leaving the embed unwired after nav swaps.
if (typeof window.document$ !== 'undefined'
    && typeof window.document$.subscribe === 'function') {
    window.document$.subscribe(initAllPreviewEmbeds);
} else {
    document.addEventListener('DOMContentLoaded', initAllPreviewEmbeds);
}
