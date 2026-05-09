// ─── Fade out alerts ────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.alert').forEach(a => {
        setTimeout(() => {
            a.style.transition = 'opacity .5s';
            a.style.opacity = '0';
            setTimeout(() => a.remove(), 500);
        }, 3500);
    });
});

// ─── Menu hamburger (mobile) ─────────────────────────────────────
function toggleMenu() {
    const drawer  = document.getElementById('nav-drawer');
    const overlay = document.getElementById('nav-overlay');
    const burger  = document.getElementById('hamburger');
    if (!drawer) return;
    const open = drawer.classList.toggle('open');
    overlay.classList.toggle('open', open);
    burger.classList.toggle('open', open);
    // animar spans do hamburger → X
    const spans = burger.querySelectorAll('span');
    if (open) {
        spans[0].style.transform = 'translateY(7px) rotate(45deg)';
        spans[1].style.opacity   = '0';
        spans[2].style.transform = 'translateY(-7px) rotate(-45deg)';
    } else {
        spans.forEach(s => { s.style.transform = ''; s.style.opacity = ''; });
    }
}

// fechar drawer ao navegar (SPA-like)
document.addEventListener('click', e => {
    const link = e.target.closest('.drawer-link');
    if (link) {
        const drawer = document.getElementById('nav-drawer');
        if (drawer && drawer.classList.contains('open')) toggleMenu();
    }
});
