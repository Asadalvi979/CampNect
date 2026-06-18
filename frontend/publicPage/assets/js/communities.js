const communityData = Array.isArray(window.communityData) ? window.communityData : [];

const communitiesGrid = document.getElementById('communitiesGrid');
const catTabs = document.querySelectorAll('.cat-tab');
const createBtn = document.getElementById('createCommunityBtn');
const createModal = document.getElementById('createModal');
const createForm = document.getElementById('createCommunityForm');
const createCancel = document.getElementById('createCancel');
const communitySearch = document.getElementById('communitySearch');

let joinedCommunities = new Set(communityData.filter(c => c.joined).map(c => c.id));
let currentFilter = 'all';
let searchTerm = '';

var leaveModal = document.getElementById('leaveConfirmModal');
var leaveConfirmBtn = document.getElementById('leaveConfirmBtn');
var leaveCancelBtn = document.getElementById('leaveCancelBtn');
var leaveCloseBtn = document.getElementById('leaveCloseBtn');
var pendingLeaveId = null;

function submitAction(action, communityId) {
    var csrfVal = getCSRFToken();
    if (window.joinCommunityUrl && csrfVal) {
        var form = document.createElement('form');
        form.method = 'POST';
        form.action = window.joinCommunityUrl;
        form.innerHTML =
            '<input type="hidden" name="csrfmiddlewaretoken" value="' + csrfVal + '">' +
            '<input type="hidden" name="action" value="' + action + '">' +
            '<input type="hidden" name="community_id" value="' + communityId + '">';
        document.body.appendChild(form);
        form.submit();
    }
}

function closeLeaveModal() {
    if (leaveModal) leaveModal.classList.remove('show');
    pendingLeaveId = null;
}

if (leaveCancelBtn) leaveCancelBtn.addEventListener('click', closeLeaveModal);
if (leaveCloseBtn) leaveCloseBtn.addEventListener('click', closeLeaveModal);
if (leaveModal) {
    leaveModal.addEventListener('click', function(e) {
        if (e.target === leaveModal) closeLeaveModal();
    });
}
if (leaveConfirmBtn && leaveModal) {
    leaveConfirmBtn.addEventListener('click', function() {
        if (pendingLeaveId !== null) {
            submitAction('leave_community', pendingLeaveId);
        }
    });
}

function renderCommunities() {
    let filtered = communityData;

    if (currentFilter !== 'all') {
        filtered = filtered.filter(c => c.category === currentFilter);
    }

    if (searchTerm) {
        const term = searchTerm.toLowerCase();
        filtered = filtered.filter(c =>
            c.name.toLowerCase().includes(term) ||
            c.desc.toLowerCase().includes(term)
        );
    }

    if (filtered.length === 0) {
        communitiesGrid.innerHTML = '<div class="empty-state"><p>No communities found. Create one!</p></div>';
        return;
    }

    communitiesGrid.innerHTML = filtered.map(c => {
        const isJoined = joinedCommunities.has(c.id);
        const catLabels = { cs:'Computer Science', se:'Software Engineering', ai:'AI & ML', general:'General' };
        const catLabel = catLabels[c.category] || c.category;
        return `
            <div class="community-card">
                <div class="community-card-top">
                    <div class="community-card-icon"><i class="fas fa-users"></i></div>
                    <div class="community-card-info">
                        <h3>${c.name}</h3>
                        <div class="community-card-meta">
                            <span class="comm-cat-badge cat-${c.category}">${catLabel}</span>
                            <span><i class="fas fa-user-friends"></i> ${c.members.toLocaleString()} members</span>
                        </div>
                    </div>
                    ${isJoined ? '<a href="' + c.chat_url + '" class="chat-comm-btn"><i class="fas fa-comments"></i> Chat</a>' : ''}
                    <button class="join-comm-btn ${isJoined ? 'joined' : ''}" data-id="${c.id}">
                        ${isJoined ? '✓ Joined' : 'Join'}
                    </button>
                </div>
                <p class="community-card-desc">${c.desc}</p>
            </div>
        `;
    }).join('');

    document.querySelectorAll('.join-comm-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = parseInt(btn.dataset.id);
            if (joinedCommunities.has(id)) {
                pendingLeaveId = id;
                if (leaveModal) leaveModal.classList.add('show');
            } else {
                submitAction('join_community', id);
            }
        });
    });
}

catTabs.forEach(tab => {
    tab.addEventListener('click', () => {
        catTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        currentFilter = tab.dataset.cat;
        renderCommunities();
    });
});

if (communitySearch) {
    communitySearch.addEventListener('input', () => {
        searchTerm = communitySearch.value;
        renderCommunities();
    });
}

var createClose = document.getElementById('createClose');

if (createBtn) {
    createBtn.addEventListener('click', function () {
        createModal.classList.add('show');
    });
}

function closeCreateModal() {
    if (createModal) {
        createModal.classList.remove('show');
    }
}

if (createCancel) {
    createCancel.addEventListener('click', closeCreateModal);
}

if (createClose) {
    createClose.addEventListener('click', closeCreateModal);
}

if (createForm) {
    createForm.addEventListener('submit', closeCreateModal);
}

if (createModal) {
    createModal.addEventListener('click', function (e) {
        if (e.target === createModal) {
            closeCreateModal();
        }
    });
}

renderCommunities();
