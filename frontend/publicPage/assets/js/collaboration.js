if (typeof window.escHtml !== 'function') {
    window.escHtml = function (str) { if (str == null) return ''; return String(str).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
}

const projectsData = Array.isArray(window.projectsData) ? window.projectsData : [];

const projectGrid = document.getElementById('projectGrid');
const postProjectBtn = document.getElementById('postProjectBtn');
const projectModal = document.getElementById('projectModal');
const projectForm = document.getElementById('postProjectForm');
const projectCancel = document.getElementById('projectCancel');
const projectSearch = document.getElementById('projectSearch');

let interestedProjects = new Set((() => {
    const el = document.getElementById('interested-ids');
    if (!el) return [];
    try { return JSON.parse(el.textContent); } catch (e) { return []; }
})());
let searchTerm = '';

function renderProjects() {
    let filtered = projectsData;

    if (searchTerm) {
        const term = searchTerm.toLowerCase();
        filtered = filtered.filter(p =>
            p.title.toLowerCase().includes(term) ||
            p.desc.toLowerCase().includes(term) ||
            (p.tags || []).some(t => t.toLowerCase().includes(term))
        );
    }

    if (filtered.length === 0) {
        projectGrid.innerHTML = '<div class="empty-state"><p>No projects yet. Post one!</p></div>';
        return;
    }

    projectGrid.innerHTML = filtered.map(p => {
        const isInterested = interestedProjects.has(p.id);
        const tags = p.tags || [];
        const roles = p.roles || [];
        return `
            <div class="project-card">
                <div class="project-card-header">
                    <div class="project-card-icon"><i class="fas fa-rocket"></i></div>
                    <div>
                        <h3>${escHtml(p.title)}</h3>
                        <p>${p.postedById ? `<a href="#" onclick="showUserQuickView(${p.postedById}); return false;" style="color:inherit;text-decoration:none;">${escHtml(p.postedBy || '')}</a>` : escHtml(p.postedBy || '')} ${p.postedByInfo ? '• ' + escHtml(p.postedByInfo) : ''}</p>
                    </div>
                </div>
                <p class="project-desc">${escHtml(p.desc)}</p>
                ${roles.length ? '<div class="project-roles">' + roles.map(r => `<span class="role-tag">${escHtml(r)}</span>`).join('') + '</div>' : ''}
                ${tags.length ? '<div class="project-tags">' + tags.map(t => `<span class="project-tag">#${escHtml(t)}</span>`).join('') + '</div>' : ''}
                <div class="project-card-footer">
                    <span><i class="fas fa-handshake"></i> <span class="interest-count-${p.id}">${p.interested}</span> interested</span>
                    <div>
                        <a href="${escHtml(p.chat_url)}" class="chat-comm-btn" style="margin-right:6px;text-decoration:none;padding:0.3rem 0.8rem;border-radius:var(--radius-xl);font-size:var(--fs-sm);background:#1C3353;color:#F6F0D6;"><i class="fas fa-comments"></i> Chat</a>
                        <button class="interest-btn ${isInterested ? 'interested' : ''}" data-id="${p.id}">
                            ${isInterested ? '✓ Interested' : '<i class="fas fa-handshake"></i> Interested'}
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    document.querySelectorAll('.interest-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const id = parseInt(this.dataset.id);
            const params = 'action=toggle_interest&post_id=' + id + '&csrfmiddlewaretoken=' + encodeURIComponent(csrfToken());
            fetch(window.location.href, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest' },
                body: params
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.interested !== undefined) {
                    if (data.interested) {
                        interestedProjects.add(id);
                    } else {
                        interestedProjects.delete(id);
                    }
                    var p = projectsData.find(function(pj) { return pj.id === id; });
                    if (p) p.interested = data.count;
                    renderProjects();
                }
            })
            .catch(function() {});
        });
    });
}

if (projectSearch) {
    projectSearch.addEventListener('input', () => {
        searchTerm = projectSearch.value;
        renderProjects();
    });
}

var projectClose = document.getElementById('projectClose');

if (postProjectBtn) {
    postProjectBtn.addEventListener('click', function () {
        projectModal.classList.add('show');
    });
}

function closeProjectModal() {
    if (projectModal) {
        projectModal.classList.remove('show');
    }
}

if (projectCancel) {
    projectCancel.addEventListener('click', closeProjectModal);
}

if (projectClose) {
    projectClose.addEventListener('click', closeProjectModal);
}

if (projectForm) {
    projectForm.addEventListener('submit', closeProjectModal);
}

if (projectModal) {
    projectModal.addEventListener('click', function (e) {
        if (e.target === projectModal) {
            closeProjectModal();
        }
    });
}

renderProjects();
