// Ctrl/Cmd+K opens search, as in the dashboard
document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('.md-search__form');
    if (form) {
        const isMac = /Mac|iPhone|iPad/.test(navigator.platform);
        const hint = document.createElement('span');
        hint.className = 'search-kbd';
        hint.innerHTML = `<kbd>${isMac ? '⌘' : 'Ctrl'}</kbd><kbd>K</kbd>`;
        form.appendChild(hint);
    }

    document.addEventListener('keydown', (event) => {
        if (event.key.toLowerCase() !== 'k' || !(event.metaKey || event.ctrlKey)) return;
        const toggle = document.querySelector('[data-md-toggle="search"]');
        const input = document.querySelector('.md-search__input');
        if (!toggle || !input) return;
        event.preventDefault();
        toggle.checked = true;
        toggle.dispatchEvent(new Event('change'));
        input.focus();
    });
});
