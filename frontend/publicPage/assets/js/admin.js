function getCSRFToken() {
  var m = document.cookie.match(/csrftoken=([\w-]+)/);
  return m ? m[1] : '';
}

// HTML/safe escaping for all user-controlled content rendered via innerHTML.
function escHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str).replace(/[&<>"']/g, function (c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
  });
}

// Escape a value embedded as a JS string arg inside a double-quoted HTML
// attribute (e.g. onclick="fn('...')"). Escapes backslashes + single quotes
// for the JS layer and HTML-encodes the rest for the attribute layer.
function jsArg(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/\\/g, '\\\\')
    .replace(/'/g, "\\'")
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/* ── Modal helpers ── */
function openModal(id) {
  document.getElementById(id).classList.add('show');
}

function closeModal(id) {
  document.getElementById(id).classList.remove('show');
}

/* ── Toast ── */
function showToast(message, type) {
  type = type || 'success';
  var container = document.getElementById('adminToastContainer');
  if (!container) return;
  var t = document.createElement('div');
  t.className = 'admin-toast ' + type;
  var icon = type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle';
  t.innerHTML = '<i class="fas fa-' + icon + '"></i> ' + escHtml(message);
  container.appendChild(t);
  setTimeout(function () { t.style.opacity = '0'; t.style.transition = 'opacity 0.3s'; }, 3000);
  setTimeout(function () { t.remove(); }, 3500);
}

/* ── Tab switching (client-side) ── */
var _sections = {
  dashboard: 'section-dashboard',
  users: 'section-users',
  communities: 'section-communities',
  notes: 'section-notes',
  announcements: 'section-announcements',
  reports: 'section-reports',
};
var _titleMap = {
  dashboard: 'Admin Dashboard',
  users: 'Manage Users',
  communities: 'Manage Communities',
  notes: 'Manage Notes',
  announcements: 'Notice Board',
  reports: 'Analytics Center',
};

function switchToTab(name) {
  var titleEl = document.getElementById('adminPageTitle');
  var navItems = document.querySelectorAll('.admin-nav-item');
  Object.keys(_sections).forEach(function (k) {
    var el = document.getElementById(_sections[k]);
    if (el) el.style.display = k === name ? 'block' : 'none';
  });
  navItems.forEach(function (item) {
    item.classList.toggle('active', item.dataset.section === name);
  });
  if (titleEl && _titleMap[name]) titleEl.textContent = _titleMap[name];
  history.replaceState(null, '', '?tab=' + name);
}

/* ── Client-side table filtering ── */
function setupTableFilter(inputId, tableId, colIndexes) {
  var input = document.getElementById(inputId);
  var table = document.getElementById(tableId);
  if (!input || !table) return;
  input.addEventListener('keyup', function () {
    var q = input.value.toLowerCase().trim();
    var rows = table.querySelectorAll('tbody tr');
    rows.forEach(function (row) {
      var match = false;
      if (q === '') { match = true; }
      else {
        var cells = row.querySelectorAll('td');
        if (colIndexes) {
          colIndexes.forEach(function (i) {
            if (cells[i] && cells[i].textContent.toLowerCase().indexOf(q) !== -1) match = true;
          });
        } else {
          cells.forEach(function (c) {
            if (c.textContent.toLowerCase().indexOf(q) !== -1) match = true;
          });
        }
      }
      row.style.display = match ? '' : 'none';
    });
  });
}

document.addEventListener('DOMContentLoaded', function () {
  var user = window.currentUser || getCurrentUser();
  if (!user) return;
  var nameEl = document.getElementById('adminUserInfo');
  if (nameEl) nameEl.textContent = user.name;

  /* ── Tab navigation ── */
  var navItems = document.querySelectorAll('.admin-nav-item');
  navItems.forEach(function (item) {
    item.addEventListener('click', function (e) {
      if (!item.dataset.section) return;
      e.preventDefault();
      switchToTab(item.dataset.section);
    });
  });
  /* sync active tab from URL on page load */
  var params = new URLSearchParams(window.location.search);
  var initialTab = params.get('tab') || 'dashboard';
  switchToTab(initialTab);

  /* ── User search + filter (client-side) ── */
  setupUserFilters();
  setupCommunities();
  setupNotes();
  setupAnnouncements();

  /* ── Keyboard: ESC closes drawer too ── */
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeUserDrawer();
  });

  /* ── Keyboard: ESC to close modals ── */
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      var openModals = document.querySelectorAll('.admin-modal-overlay.show');
      openModals.forEach(function (m) { m.classList.remove('show'); });
    }
  });
});

/* ── User CRUD ── */
function openEditUserModal(id, name, role, isActive) {
  document.getElementById('editUserId').value = id;
  document.getElementById('editUserName').textContent = 'Editing: ' + name;
  document.getElementById('editUserRole').value = role;
  document.getElementById('editUserActive').value = String(isActive);
  openModal('editUserModal');
}

function submitEditUser() {
  var id = document.getElementById('editUserId').value;
  var role = document.getElementById('editUserRole').value;
  var isActive = document.getElementById('editUserActive').value;
  var params = 'action=update_user&user_id=' + id + '&role=' + encodeURIComponent(role) + '&is_active=' + isActive + '&csrfmiddlewaretoken=' + encodeURIComponent(getCSRFToken());
  fetch('/admin-api/', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: params })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.ok) {
        showToast('User updated successfully');
        closeModal('editUserModal');
        var row = document.querySelector('tr[data-user-id="' + id + '"]');
        if (row) {
          var pill = row.querySelector('.role-pill');
          if (pill) {
            pill.className = 'role-pill ' + d.role;
            pill.textContent = d.role.charAt(0).toUpperCase() + d.role.slice(1);
          }
          var dot = row.querySelector('.status-dot');
          if (dot) {
            dot.className = 'status-dot' + (d.is_active ? ' active' : '');
          }
        }
      } else {
        showToast(d.error || 'Failed to update user', 'error');
      }
    })
    .catch(function () { showToast('Network error', 'error'); });
}

/* ── Community CRUD ── */
function openCreateCommunityModal() {
  document.getElementById('editCommunityId').value = '';
  document.getElementById('communityName').value = '';
  document.getElementById('communityCategory').value = 'general';
  document.getElementById('communityDesc').value = '';
  document.getElementById('communityModalTitle').querySelector('span').textContent = 'New Community';
  document.getElementById('communitySaveBtn').textContent = 'Create';
  openModal('communityModal');
}

function openEditCommunityModal(id, name, desc, category) {
  document.getElementById('editCommunityId').value = id;
  document.getElementById('communityName').value = name;
  document.getElementById('communityCategory').value = category;
  document.getElementById('communityDesc').value = desc;
  document.getElementById('communityModalTitle').querySelector('span').textContent = 'Edit Community';
  document.getElementById('communitySaveBtn').textContent = 'Save Changes';
  openModal('communityModal');
}

function submitCommunity() {
  var id = document.getElementById('editCommunityId').value;
  var name = document.getElementById('communityName').value.trim();
  var category = document.getElementById('communityCategory').value;
  var desc = document.getElementById('communityDesc').value.trim();
  if (!name) { showToast('Community name is required', 'error'); return; }
  var isEdit = !!id;
  var action = isEdit ? 'update_community' : 'create_community';
  var params = 'action=' + action + '&name=' + encodeURIComponent(name) + '&category=' + encodeURIComponent(category) + '&description=' + encodeURIComponent(desc) + '&csrfmiddlewaretoken=' + encodeURIComponent(getCSRFToken());
  if (isEdit) params += '&community_id=' + id;
  fetch('/admin-api/', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: params })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.ok) {
        showToast(isEdit ? 'Community updated' : 'Community created');
        closeModal('communityModal');
        setTimeout(function () { window.location.reload(); }, 500);
      } else {
        showToast(d.error || 'Failed', 'error');
      }
    })
    .catch(function () { showToast('Network error', 'error'); });
}

/* ── Announcement CRUD ── */
function openCreateAnnouncementModal() {
  document.getElementById('editAnnouncementId').value = '';
  document.getElementById('announcementTitle').value = '';
  document.getElementById('announcementByLine').value = '';
  document.getElementById('announcementContent').value = '';
  document.getElementById('announcementModalTitle').querySelector('span').textContent = 'New Notice';
  document.getElementById('announcementSaveBtn').textContent = 'Post';
  openModal('announcementModal');
}

function openEditAnnouncementModal(id, title, content, byLine) {
  document.getElementById('editAnnouncementId').value = id;
  document.getElementById('announcementTitle').value = title;
  document.getElementById('announcementByLine').value = byLine || '';
  document.getElementById('announcementContent').value = content;
  document.getElementById('announcementModalTitle').querySelector('span').textContent = 'Edit Notice';
  document.getElementById('announcementSaveBtn').textContent = 'Update';
  openModal('announcementModal');
}

function submitAnnouncement() {
  var id = document.getElementById('editAnnouncementId').value;
  var title = document.getElementById('announcementTitle').value.trim();
  var byLine = document.getElementById('announcementByLine').value.trim();
  var content = document.getElementById('announcementContent').value.trim();
  if (!title || !content) { showToast('Title and content are required', 'error'); return; }
  var isEdit = !!id;
  var action = isEdit ? 'update_announcement' : 'create_announcement';
  var params = 'action=' + action + '&title=' + encodeURIComponent(title) + '&by_line=' + encodeURIComponent(byLine) + '&content=' + encodeURIComponent(content) + '&csrfmiddlewaretoken=' + encodeURIComponent(getCSRFToken());
  if (isEdit) params += '&announcement_id=' + id;
  fetch('/admin-api/', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: params })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.ok) {
        showToast(isEdit ? 'Notice updated' : 'Notice posted');
        closeModal('announcementModal');
        setTimeout(function () { window.location.reload(); }, 500);
      } else {
        showToast(d.error || 'Failed', 'error');
      }
    })
    .catch(function () { showToast('Network error', 'error'); });
}

/* ── Delete (generic) ── */
function openDeleteModal(type, id, label) {
  document.getElementById('deleteTargetType').value = type;
  document.getElementById('deleteTargetId').value = id;
  document.getElementById('deleteConfirmText').textContent = 'Are you sure you want to delete "' + label + '"? This action cannot be undone.';
  openModal('deleteConfirmModal');
}

function submitDelete() {
  var type = document.getElementById('deleteTargetType').value;
  var id = document.getElementById('deleteTargetId').value;
  var actionMap = { user: 'delete_user', community: 'delete_community', announcement: 'delete_announcement', note: 'delete_note' };
  var action = actionMap[type];
  if (!action) return;
  var idField = type + '_id';
  var params = 'action=' + action + '&' + idField + '=' + id + '&csrfmiddlewaretoken=' + encodeURIComponent(getCSRFToken());
  fetch('/admin-api/', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: params })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.ok) {
        showToast(type.charAt(0).toUpperCase() + type.slice(1) + ' deleted');
        closeModal('deleteConfirmModal');
        var attr = type === 'note' ? 'note' : type;
        var row = document.querySelector('tr[data-' + attr + '-id="' + id + '"]');
        if (row) row.remove();
        // Remove community list items if they exist
        if (type === 'community') {
          var item = document.querySelector('.comm-list-item[data-comm-id="' + id + '"]');
          if (item) {
            item.remove();
            document.getElementById('commDetailContent').style.display = 'none';
            document.getElementById('commDetailEmpty').style.display = '';
          }
        }
        // Remove note list items if they exist
        if (type === 'note') {
          var noteRow = document.querySelector('.notes-row[data-note-id="' + id + '"]');
          if (noteRow) {
            noteRow.remove();
            closeNoteDetail();
          }
        }
        // Remove announcement feed items if they exist
        if (type === 'announcement') {
          var annItem = document.querySelector('.ann-item[data-ann-id="' + id + '"]');
          if (annItem) annItem.remove();
        }
      } else {
        showToast(d.error || 'Failed to delete', 'error');
      }
    })
    .catch(function () { showToast('Network error', 'error'); });
}

/* ── User detail drawer ── */
function openUserDrawer(id) {
  var data = window.usersData[id];
  if (!data) return;
  var body = document.getElementById('drawerBody');
  var nameSafe = jsArg(data.name);
  body.innerHTML =
    '<div class="drawer-profile">' +
      (data.avatar ? '<img class="drawer-avatar" src="' + escHtml(data.avatar) + '" alt="">' : '<div class="drawer-avatar" style="background:#2563EB;">' + escHtml(data.initials) + '</div>') +
      '<h2>' + escHtml(data.name) + '</h2>' +
      '<span class="role-pill ' + data.role + '">' + escHtml(data.roleLabel) + '</span>' +
    '</div>' +
    '<div class="drawer-details">' +
      '<div class="drawer-field"><label>CMS ID</label><span>' + escHtml(data.cms) + '</span></div>' +
      '<div class="drawer-field"><label>Email</label><span>' + escHtml(data.email) + '</span></div>' +
      '<div class="drawer-field"><label>Department</label><span>' + escHtml(data.department || '\u2014') + '</span></div>' +
      '<div class="drawer-field"><label>Semester</label><span>' + (data.semester ? 'Semester ' + escHtml(data.semester) : '\u2014') + '</span></div>' +
      '<div class="drawer-field"><label>Bio</label><span>' + escHtml(data.bio || 'No bio') + '</span></div>' +
      '<div class="drawer-field"><label>Skills</label><span>' + escHtml(data.skills || '\u2014') + '</span></div>' +
      '<div class="drawer-field"><label>Status</label><span><span class="status-dot' + (data.isActive ? ' active' : '') + '" style="display:inline-block;margin-right:6px;vertical-align:middle;"></span>' + (data.isActive ? 'Active' : 'Inactive') + '</span></div>' +
      '<div class="drawer-field"><label>Joined</label><span>' + escHtml(data.dateJoined) + '</span></div>' +
    '</div>' +
    '<div class="drawer-actions">' +
      '<button class="admin-action-btn edit" onclick="closeUserDrawer();openEditUserModal(' + id + ',\'' + nameSafe + '\',\'' + jsArg(data.role) + '\',' + (data.isActive ? 1 : 0) + ')">Edit Role / Status</button>' +
      '<button class="admin-action-btn delete" onclick="closeUserDrawer();openDeleteModal(\'user\',' + id + ',\'' + nameSafe + '\')">Delete User</button>' +
    '</div>';
  document.getElementById('userDrawer').classList.add('open');
  document.getElementById('drawerOverlay').classList.add('show');
}

function closeUserDrawer() {
  document.getElementById('userDrawer').classList.remove('open');
  document.getElementById('drawerOverlay').classList.remove('show');
}

/* ── User table filters (role, dept, semester) ── */
function setupUserFilters() {
  var input = document.getElementById('userSearchInput');
  if (input) input.addEventListener('keyup', applyUserFilters);
}

function applyUserFilters() {
  var input = document.getElementById('userSearchInput');
  var role = document.getElementById('filterRole');
  var dept = document.getElementById('filterDept');
  var sem = document.getElementById('filterSem');
  var q = input ? input.value.toLowerCase().trim() : '';
  var rv = role ? role.value : '';
  var dv = dept ? dept.value : '';
  var sv = sem ? sem.value : '';
  Array.prototype.forEach.call(document.querySelectorAll('#usersTable tbody tr'), function (row) {
    if (row.cells.length < 8) return;
    var name = row.cells[0].textContent.toLowerCase();
    var cms = row.cells[1].textContent.toLowerCase();
    var email = row.cells[2].textContent.toLowerCase();
    var deptText = row.cells[3].textContent.toLowerCase();
    var semText = row.cells[4].textContent.trim();
    var roleText = row.cells[5].textContent.trim().toLowerCase();
    var textMatch = q === '' || name.indexOf(q) !== -1 || cms.indexOf(q) !== -1 || email.indexOf(q) !== -1 || deptText.indexOf(q) !== -1;
    var roleMatch = rv === '' || roleText === rv;
    var deptMatch = dv === '' || deptText === dv.toLowerCase();
    var semMatch = sv === '' || semText.indexOf('Sem ' + sv) !== -1;
    row.style.display = (textMatch && roleMatch && deptMatch && semMatch) ? '' : 'none';
  });
}

/* ═══════════════════════════════════════
   Community Management
   ═══════════════════════════════════════ */

function setupCommunities() {
  var input = document.getElementById('commSearchInput');
  if (input) input.addEventListener('keyup', filterCommunityList);
  Array.prototype.forEach.call(document.querySelectorAll('.comm-cat-tab'), function (tab) {
    tab.addEventListener('click', function () {
      document.querySelectorAll('.comm-cat-tab').forEach(function (t) { t.classList.remove('active'); });
      tab.classList.add('active');
      filterCommunityList();
    });
  });
}

function filterCommunityList() {
  var q = (document.getElementById('commSearchInput').value || '').toLowerCase().trim();
  var activeTab = document.querySelector('.comm-cat-tab.active');
  var cat = activeTab ? activeTab.getAttribute('data-cat') : '';
  Array.prototype.forEach.call(document.querySelectorAll('.comm-list-item'), function (item) {
    var name = item.querySelector('.comm-item-name').textContent.toLowerCase();
    var itemCat = item.getAttribute('data-cat');
    var textMatch = q === '' || name.indexOf(q) !== -1;
    var catMatch = cat === '' || itemCat === cat;
    item.style.display = (textMatch && catMatch) ? '' : 'none';
  });
}

function setCommunityDetail(data) {
  var colors = ['#2563EB','#10B981','#8B5CF6','#B8860B','#EF4444','#06B6D4','#1C3353','#F59E0B'];
  var color = colors[data.id % colors.length];
  document.getElementById('commDetailIcon').style.background = color;
  document.getElementById('commDetailIcon').textContent = data.name.charAt(0).toUpperCase();
  document.getElementById('commDetailName').textContent = data.name;
  document.getElementById('commDetailCat').textContent = data.categoryLabel;
  document.getElementById('commDetailCat').className = 'comm-cat-badge ' + data.category;
  document.getElementById('commDetailDesc').textContent = data.description || 'No description';
  document.getElementById('commDetailCreator').textContent = data.creator;
  document.getElementById('commDetailMemberCount').textContent = data.memberCount;
  document.getElementById('commDetailMemberCount2').textContent = data.memberCount;
  document.getElementById('commDetailDate').textContent = data.date;
  document.getElementById('commEditBtn').setAttribute('onclick', "openEditCommunityModal(" + data.id + ",'" + jsArg(data.name) + "','" + jsArg(data.description || '') + "','" + jsArg(data.category) + "')");
  document.getElementById('commDeleteBtn').setAttribute('onclick', "openDeleteModal('community'," + data.id + ",'" + jsArg(data.name) + "')");
  document.getElementById('commDetailEmpty').style.display = 'none';
  document.getElementById('commDetailContent').style.display = 'block';
}

function selectCommunity(id) {
  var data = window.communitiesData[id];
  if (!data) return;
  data.id = id;
  Array.prototype.forEach.call(document.querySelectorAll('.comm-list-item'), function (item) {
    item.classList.toggle('active', parseInt(item.getAttribute('data-comm-id')) === id);
  });
  setCommunityDetail(data);
  loadCommunityMembers(id);
}

function loadCommunityMembers(commId) {
  var list = document.getElementById('commMemberList');
  list.innerHTML = '<div class="comm-loading">Loading members...</div>';
  var params = 'action=get_community_members&community_id=' + commId + '&csrfmiddlewaretoken=' + encodeURIComponent(getCSRFToken());
  fetch('/admin-api/', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: params })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (!d.ok) { list.innerHTML = '<div class="comm-loading">Failed to load members</div>'; return; }
      if (d.members.length === 0) {
        list.innerHTML = '<div class="comm-loading">No members yet</div>';
        return;
      }
      var html = '';
      d.members.forEach(function (m) {
        html +=
          '<div class="comm-member-item">' +
            '<div class="comm-member-avatar" style="background:' + (m.is_admin ? '#F59E0B' : '#2563EB') + ';">' + escHtml(m.initials) + '</div>' +
            '<div class="comm-member-body">' +
              '<div class="comm-member-name">' + escHtml(m.name) + (m.is_admin ? ' <span class="comm-member-role">Admin</span>' : '') + '</div>' +
              '<div class="comm-member-cms">' + escHtml(m.cms) + ' &middot; Joined ' + escHtml(m.joined_at) + '</div>' +
            '</div>' +
            '<div class="comm-member-actions">' +
              '<button class="comm-member-btn promote" title="' + (m.is_admin ? 'Demote' : 'Promote to admin') + '" onclick="promoteMember(' + m.id + ', this)"><i class="fas fa-' + (m.is_admin ? 'user-minus' : 'user-shield') + '"></i></button>' +
              '<button class="comm-member-btn remove" title="Remove member" onclick="removeMember(' + m.id + ',\'' + jsArg(m.name) + '\')"><i class="fas fa-times"></i></button>' +
            '</div>' +
          '</div>';
      });
      list.innerHTML = html;
    })
    .catch(function () { list.innerHTML = '<div class="comm-loading">Network error</div>'; });
}

function promoteMember(memberId, btn) {
  var params = 'action=toggle_community_admin&member_id=' + memberId + '&csrfmiddlewaretoken=' + encodeURIComponent(getCSRFToken());
  fetch('/admin-api/', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: params })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.ok) {
        showToast(d.is_admin ? 'Member promoted to admin' : 'Admin demoted to member');
        // Reload the whole member list to keep UI consistent
        var commItem = document.querySelector('.comm-list-item.active');
        if (commItem) loadCommunityMembers(parseInt(commItem.getAttribute('data-comm-id')));
      } else {
        showToast(d.error || 'Failed', 'error');
      }
    })
    .catch(function () { showToast('Network error', 'error'); });
}

function removeMember(memberId, name) {
  if (!confirm('Remove ' + name + ' from this community?')) return;
  var params = 'action=remove_community_member&member_id=' + memberId + '&csrfmiddlewaretoken=' + encodeURIComponent(getCSRFToken());
  fetch('/admin-api/', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: params })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.ok) {
        showToast('Member removed');
        var commItem = document.querySelector('.comm-list-item.active');
        if (commItem) loadCommunityMembers(parseInt(commItem.getAttribute('data-comm-id')));
      } else {
        showToast(d.error || 'Failed', 'error');
      }
    })
    .catch(function () { showToast('Network error', 'error'); });
}

/* ═══════════════════════════════════════
   Notes Management — Google Drive Style
   ═══════════════════════════════════════ */

function setupNotes() {
  var input = document.getElementById('noteSearchInput');
  if (input) input.addEventListener('keyup', filterNotes);
  Array.prototype.forEach.call(document.querySelectorAll('.notes-sub-tab'), function (tab) {
    tab.addEventListener('click', function () {
      document.querySelectorAll('.notes-sub-tab').forEach(function (t) { t.classList.remove('active'); });
      tab.classList.add('active');
      filterNotes();
    });
  });
}

function filterNotes() {
  var q = (document.getElementById('noteSearchInput').value || '').toLowerCase().trim();
  var activeTab = document.querySelector('.notes-sub-tab.active');
  var subject = activeTab ? activeTab.getAttribute('data-subject') : '';
  Array.prototype.forEach.call(document.querySelectorAll('.notes-row'), function (row) {
    var title = row.querySelector('.notes-row-title').textContent.toLowerCase();
    var rowSubject = row.getAttribute('data-subject');
    var owner = (row.querySelector('.notes-row-owner') || {}).textContent.toLowerCase() || '';
    var textMatch = q === '' || title.indexOf(q) !== -1 || owner.indexOf(q) !== -1;
    var subjMatch = subject === '' || rowSubject === subject;
    row.style.display = (textMatch && subjMatch) ? '' : 'none';
  });
}

function selectNote(id) {
  var data = window.notesData[id];
  if (!data) return;
  Array.prototype.forEach.call(document.querySelectorAll('.notes-row'), function (row) {
    row.classList.toggle('selected', parseInt(row.getAttribute('data-note-id')) === id);
  });
  var panel = document.getElementById('notesDetailPanel');
  panel.classList.add('open');
  var colors = ['#2563EB','#10B981','#8B5CF6','#B8860B','#EF4444','#06B6D4'];
  document.getElementById('notesDetailIcon').style.color = colors[id % colors.length];
  document.getElementById('notesDetailTitle').textContent = data.title;
  var subjPill = document.getElementById('notesDetailSubject');
  subjPill.textContent = data.subject || 'General';
  subjPill.style.display = data.subject ? '' : 'none';
  document.getElementById('notesDetailDesc').textContent = data.description || 'No description';
  document.getElementById('notesDetailUploader').textContent = data.uploader;
  document.getElementById('notesDetailDate').textContent = data.date;
  document.getElementById('notesDetailCommunity').textContent = data.community || '\u2014';
  var dlLink = document.getElementById('notesDownloadLink');
  if (data.hasFile && data.fileUrl) {
    dlLink.style.display = '';
    dlLink.href = data.fileUrl;
  } else {
    dlLink.style.display = 'none';
  }
  document.getElementById('notesDetailDeleteBtn').setAttribute('onclick', "openDeleteModal('note'," + id + ",'" + jsArg(data.title) + "')");
  document.getElementById('notesDetailEmpty').style.display = 'none';
  document.getElementById('notesDetailBody').style.display = '';
}

function closeNoteDetail() {
  document.getElementById('notesDetailPanel').classList.remove('open');
  document.getElementById('notesDetailEmpty').style.display = '';
  document.getElementById('notesDetailBody').style.display = 'none';
  Array.prototype.forEach.call(document.querySelectorAll('.notes-row'), function (row) {
    row.classList.remove('selected');
  });
}

/* ═══════════════════════════════════════
   Announcements — Notice Board
   ═══════════════════════════════════════ */

function setupAnnouncements() {
  var input = document.getElementById('announcementSearchInput');
  if (input) input.addEventListener('keyup', filterAnnouncements);
}

function filterAnnouncements() {
  var q = (document.getElementById('announcementSearchInput').value || '').toLowerCase().trim();
  Array.prototype.forEach.call(document.querySelectorAll('.ann-item'), function (item) {
    var title = (item.querySelector('.ann-title') || {}).textContent.toLowerCase() || '';
    var byline = (item.querySelector('.ann-byline') || {}).textContent.toLowerCase() || '';
    var content = (item.querySelector('.ann-content') || {}).textContent.toLowerCase() || '';
    var match = q === '' || title.indexOf(q) !== -1 || byline.indexOf(q) !== -1 || content.indexOf(q) !== -1;
    item.style.display = match ? '' : 'none';
  });
}

function togglePin(annId, btn) {
  var params = 'action=toggle_pin_announcement&announcement_id=' + annId + '&csrfmiddlewaretoken=' + encodeURIComponent(getCSRFToken());
  fetch('/admin-api/', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: params })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.ok) {
        showToast(d.is_pinned ? 'Notice pinned' : 'Notice unpinned');
        setTimeout(function () { window.location.reload(); }, 400);
      } else {
        showToast(d.error || 'Failed', 'error');
      }
    })
    .catch(function () { showToast('Network error', 'error'); });
}

/* ── Analytics Charts ── */
var _analyticsCharts = [];

function renderAnalyticsCharts() {
  var el = document.getElementById('analyticsData');
  if (!el) return;
  var data = JSON.parse(el.textContent);

  _analyticsCharts.forEach(function (c) { c.destroy(); });
  _analyticsCharts = [];

  var blue = '#2563EB', green = '#10B981', purple = '#8B5CF6', gold = '#B8860B', red = '#EF4444', cyan = '#06B6D4', indigo = '#6366F1', dark = '#1C3353';
  var darkText = '#1C3353', gridColor = '#e8ece8';

  function makeChart(id, labels, datasets) {
    var canvas = document.getElementById(id);
    if (!canvas) return;
    var c = new Chart(canvas.getContext('2d'), {
      type: 'line',
      data: { labels: labels, datasets: datasets },
      options: {
        responsive: true, maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: { legend: { position: 'top', labels: { font: { size: 10 }, color: darkText, boxWidth: 12, padding: 12, usePointStyle: true } } },
        scales: {
          x: { ticks: { font: { size: 10 }, color: darkText }, grid: { color: gridColor } },
          y: { beginAtZero: true, ticks: { font: { size: 10 }, color: darkText }, grid: { color: gridColor } }
        }
      }
    });
    _analyticsCharts.push(c);
  }

  /* ── 1. Growth Trends ── */
  var ug = data.userGrowth;
  if (ug && ug.labels && ug.labels.length) {
    makeChart('chartGrowth', ug.labels, [
      {
        label: 'New Users', data: ug.monthly, borderColor: blue, backgroundColor: 'rgba(37,99,235,0.06)',
        fill: true, tension: 0.35, pointRadius: 3, pointBackgroundColor: blue, borderWidth: 2
      },
      {
        label: 'Cumulative', data: ug.cumulative, borderColor: '#1C3353', backgroundColor: 'rgba(28,51,83,0.04)',
        fill: true, tension: 0.35, pointRadius: 2, pointBackgroundColor: '#1C3353', borderWidth: 2, borderDash: [4, 3]
      }
    ]);
  }

  /* ── 2. Engagement Trends ── */
  var eg = data.engagementTrends;
  if (eg && eg.labels && eg.labels.length) {
    makeChart('chartEngagement', eg.labels, [
      {
        label: 'Notes', data: eg.notes, borderColor: gold, backgroundColor: 'rgba(184,134,11,0.06)',
        fill: true, tension: 0.35, pointRadius: 3, pointBackgroundColor: gold, borderWidth: 2
      },
      {
        label: 'Collaborations', data: eg.collab, borderColor: red, backgroundColor: 'rgba(239,68,68,0.06)',
        fill: true, tension: 0.35, pointRadius: 3, pointBackgroundColor: red, borderWidth: 2
      }
    ]);
  }

  /* ── 3. Top Communities Leaderboard ── */
  var tc = data.topCommunities;
  var lbc = document.getElementById('lbCommunities');
  if (lbc && tc && tc.length) {
    var maxMembers = tc[0].members;
    var html = '<table class="lb-table"><thead><tr><th></th><th>Community</th><th>Category</th><th>Creator</th><th>Members</th><th></th></tr></thead><tbody>';
    tc.forEach(function (c, i) {
      var rankClass = i === 0 ? 'top1' : i === 1 ? 'top2' : i === 2 ? 'top3' : '';
      var barW = Math.round((c.members / maxMembers) * 100);
      html += '<tr><td class="lb-rank ' + rankClass + '">#' + (i + 1) + '</td>'
        + '<td class="lb-name">' + escHtml(c.name) + '</td>'
        + '<td><span class="lb-badge">' + escHtml(c.category) + '</span></td>'
        + '<td class="lb-sub">' + escHtml(c.creator) + '</td>'
        + '<td class="lb-num">' + c.members + '</td>'
        + '<td class="lb-bar-cell"><div class="lb-bar"><div class="lb-bar-fill" style="width:' + barW + '%"></div></div></td>'
        + '</tr>';
    });
    html += '</tbody></table>';
    lbc.innerHTML = html;
  }

  /* ── 4. Top Departments Leaderboard ── */
  var td = data.topDepartments;
  var lbd = document.getElementById('lbDepartments');
  if (lbd && td && td.length) {
    var maxTotal = td[0].total;
    var html2 = '<table class="lb-table"><thead><tr><th></th><th>Department</th><th>Students</th><th>Seniors</th><th>Alumni</th><th>Total</th><th></th></tr></thead><tbody>';
    td.forEach(function (d, i) {
      var rankClass2 = i === 0 ? 'top1' : i === 1 ? 'top2' : i === 2 ? 'top3' : '';
      var barW2 = Math.round((d.total / maxTotal) * 100);
      html2 += '<tr><td class="lb-rank ' + rankClass2 + '">#' + (i + 1) + '</td>'
        + '<td class="lb-name">' + escHtml(d.department) + '</td>'
        + '<td class="lb-num">' + d.students + '</td>'
        + '<td class="lb-num">' + d.seniors + '</td>'
        + '<td class="lb-num">' + d.alumni + '</td>'
        + '<td class="lb-num">' + d.total + '</td>'
        + '<td class="lb-bar-cell"><div class="lb-bar"><div class="lb-bar-fill green" style="width:' + barW2 + '%"></div></div></td>'
        + '</tr>';
    });
    html2 += '</tbody></table>';
    lbd.innerHTML = html2;
  }

  /* ── 5. Platform Insights ── */
  var ins = data.insights;
  var iw = document.getElementById('insightsWrap');
  if (iw && ins && ins.length) {
    var icons = ['fa-chart-line', 'fa-users', 'fa-book', 'fa-handshake', 'fa-graduation-cap', 'fa-user-graduate', 'fa-lightbulb'];
    var html3 = '';
    ins.forEach(function (t, i) {
      var icon = icons[i % icons.length];
      html3 += '<div class="insight-card"><div class="insight-icon"><i class="fas ' + icon + '"></i></div><div class="insight-text">' + escHtml(t) + '</div></div>';
    });
    iw.innerHTML = html3;
  }
}

/* hook into existing switchToTab */
var _origSwitchToTab = window.switchToTab || function () {};
switchToTab = function (name) {
  _origSwitchToTab(name);
  if (name === 'reports') {
    setTimeout(renderAnalyticsCharts, 50);
  }
};

document.addEventListener('DOMContentLoaded', function () {
  var sr = document.getElementById('section-reports');
  if (sr && sr.style.display !== 'none') {
    setTimeout(renderAnalyticsCharts, 100);
  }
});