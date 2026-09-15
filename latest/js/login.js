document.addEventListener('DOMContentLoaded', () => {
  const nav = document.querySelector('.md-header__inner')
  if (!nav) return;
  const btn = document.createElement('a');
  btn.href = 'https://app.rapidata.ai';
  btn.target = '_blank'
  btn.className = 'login-button';
  btn.textContent = 'Login';
  btn.title = 'Login to rapidata'
  nav.appendChild(btn);
});
