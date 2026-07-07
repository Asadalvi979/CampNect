const notesData = Array.isArray(window.notesData) ? window.notesData : [];

const notesGrid = document.getElementById('notesGrid');
const semTabs = document.querySelectorAll('.sem-tab');
const uploadBtn = document.getElementById('uploadNotesBtn');
const uploadModal = document.getElementById('uploadModal');
const uploadForm = document.getElementById('uploadNotesForm');
const uploadCancel = document.getElementById('uploadCancel');
const notesSearch = document.getElementById('notesSearch');

let currentSem = 'all';
let searchTerm = '';

function renderNotes() {
    let filtered = notesData;

    if (currentSem !== 'all') {
        filtered = filtered.filter(n => String(n.semester) === currentSem);
    }

    if (searchTerm) {
        const term = searchTerm.toLowerCase();
        filtered = filtered.filter(n =>
            n.title.toLowerCase().includes(term) ||
            n.subject.toLowerCase().includes(term) ||
            n.uploader.toLowerCase().includes(term)
        );
    }

    if (filtered.length === 0) {
        notesGrid.innerHTML = '<div class="empty-state"><p>No notes uploaded yet. Be the first to share!</p></div>';
        return;
    }

    notesGrid.innerHTML = filtered.map(n => `
        <div class="note-card" data-id="${n.id}" data-url="${n.url || ''}" data-uploader="${n.uploaderId}" data-title="${n.title.replace(/"/g, '&quot;')}" data-desc="${(n.desc || '').replace(/"/g, '&quot;')}">
            <div class="note-card-icon"><i class="fas fa-file"></i></div>
            <h3>${n.title}</h3>
            <p class="note-subject">${n.subject} ${n.semester ? '• Semester ' + n.semester : ''}</p>
            <p class="note-desc">${n.desc}</p>
            <div class="note-meta">
                <span><i class="fas fa-user"></i> <a href="#" onclick="showUserQuickView(${n.uploaderId}); return false;" style="color:inherit;text-decoration:none;">${n.uploader}</a> ${n.downloads ? '• <i class="fas fa-inbox"></i> ' + n.downloads + ' downloads' : ''}</span>
                ${n.url ? `<a class="download-note-btn" href="${n.url}" download>Download</a>` : ''}
            </div>
        </div>
    `).join('');

    document.querySelectorAll('.note-card').forEach(function(card) {
        card.addEventListener('click', function(e) {
            if (e.target.closest('.download-note-btn')) return;
            var url = card.dataset.url;
            if (url) window.open(url, '_blank');
        });
    });
}

semTabs.forEach(tab => {
    tab.addEventListener('click', () => {
        semTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        currentSem = tab.dataset.sem;
        renderNotes();
    });
});

if (notesSearch) {
    notesSearch.addEventListener('input', () => {
        searchTerm = notesSearch.value;
        renderNotes();
    });
}

var uploadClose = document.getElementById('uploadClose');

if (uploadBtn) {
    uploadBtn.addEventListener('click', function () {
        uploadModal.classList.add('show');
    });
}

function closeUploadModal() {
    if (uploadModal) {
        uploadModal.classList.remove('show');
    }
}

if (uploadCancel) {
    uploadCancel.addEventListener('click', closeUploadModal);
}

if (uploadClose) {
    uploadClose.addEventListener('click', closeUploadModal);
}

if (uploadForm) {
    uploadForm.addEventListener('submit', closeUploadModal);
}

if (uploadModal) {
    uploadModal.addEventListener('click', function (e) {
        if (e.target === uploadModal) {
            closeUploadModal();
        }
    });
}

renderNotes();
