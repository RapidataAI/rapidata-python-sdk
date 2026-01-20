// AI Agent copy button enhancements
document.addEventListener('DOMContentLoaded', function() {
    const copyButton = document.getElementById('llms-copy-button');
    if (!copyButton) return;

    // Move button into content area for proper alignment
    const contentInner = document.querySelector('.md-content__inner');
    if (contentInner) {
        contentInner.style.position = 'relative';
        contentInner.insertBefore(copyButton, contentInner.firstChild);
    }

    const button = copyButton.querySelector('button');
    if (!button) return;

    // Replace button content with SVG icon
    const copyIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`;
    const checkIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
    const errorIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`;

    button.innerHTML = copyIcon;

    // Override the click handler to show checkmark
    const originalOnclick = button.onclick;
    button.onclick = async function(e) {
        try {
            const currentPath = window.location.pathname;
            const mdPath = currentPath.endsWith('/') ? currentPath + 'index.md' : currentPath.replace(/\.html$/, '.md');

            const response = await fetch(mdPath);
            if (response.ok) {
                const markdown = await response.text();
                await navigator.clipboard.writeText(markdown);

                // Show checkmark
                button.innerHTML = checkIcon;
                button.classList.add('copied');

                setTimeout(() => {
                    button.innerHTML = copyIcon;
                    button.classList.remove('copied');
                }, 2000);
            } else {
                throw new Error('Markdown file not found');
            }
        } catch (err) {
            console.error('Failed to copy markdown:', err);
            button.innerHTML = errorIcon;
            button.classList.add('error');
            setTimeout(() => {
                button.innerHTML = copyIcon;
                button.classList.remove('error');
            }, 2000);
        }
    };
});
