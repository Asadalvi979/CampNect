document.addEventListener('DOMContentLoaded', function () {
  var user = window.currentUser || getCurrentUser();
  if (!user) { return; }
  var mentorData = window.mentorsData || [];
  var requestData = window.mentorshipRequestsData || [];
  initMentorshipTabs(mentorData, requestData);
  var initialFilter = user.role === 'alumni' ? 'requests' : 'available';
  renderMentors(initialFilter, mentorData, requestData);

  var menuToggle = document.getElementById('menuToggle');
  var sidebar = document.getElementById('sidebar');
  var overlay = document.getElementById('overlay');
  if (menuToggle && sidebar && overlay) {
    menuToggle.addEventListener('click', function () {
      sidebar.classList.add('open');
      overlay.classList.add('show');
      document.body.style.overflow = 'hidden';
    });
    overlay.addEventListener('click', function () {
      sidebar.classList.remove('open');
      overlay.classList.remove('show');
      document.body.style.overflow = '';
    });
  }

  var newMentorshipBtn = document.getElementById('newMentorshipBtn');
  var newMentorshipModal = document.getElementById('newMentorshipModal');
  var newMentorshipClose = document.getElementById('newMentorshipClose');
  var newMentorshipSearch = document.getElementById('newMentorshipSearch');
  var newMentorshipList = document.getElementById('newMentorshipList');

  function renderMentorList(filter) {
    var term = (filter || '').toLowerCase();
    var list = mentorData.filter(function (m) {
      return (m.role === 'alumni' || m.role === 'senior')
        && (!m.mentorship || m.mentorship.status === 'rejected');
    });
    if (term) { list = list.filter(function (m) { return m.name.toLowerCase().includes(term); }); }
    newMentorshipList.innerHTML = list.map(function (m) {
      var avatar = m.profile_pic
        ? '<img src="' + m.profile_pic + '" alt="" style="width:40px;height:40px;object-fit:cover;border-radius:50%;">'
        : '<div style="width:40px;height:40px;border-radius:50%;background:#1C3353;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:0.8rem;">' + (m.name ? m.name.split(' ').map(function (s) { return s[0]; }).join('').substring(0, 2).toUpperCase() : '?') + '</div>';
      return '<div class="new-msg-user-item" data-id="' + m.id + '" style="cursor:pointer;">' +
        avatar +
        '<div class="conversation-info"><h4>' + m.name + '</h4><p>' + (m.dept || '') + ' \u2022 ' + (m.badge || m.role) + '</p></div>' +
      '</div>';
    }).join('');
    document.querySelectorAll('#newMentorshipList .new-msg-user-item').forEach(function (item) {
      item.addEventListener('click', function () {
        var mid = parseInt(item.dataset.id);
        var form = document.createElement('form');
        form.method = 'POST';
        form.action = '';
        form.innerHTML = '<input type="hidden" name="csrfmiddlewaretoken" value="' + getCSRFToken() + '">' +
          '<input type="hidden" name="action" value="start">' +
          '<input type="hidden" name="mentor_id" value="' + mid + '">';
        document.body.appendChild(form);
        form.submit();
      });
    });
  }

  if (newMentorshipBtn && newMentorshipModal) {
    newMentorshipBtn.addEventListener('click', function () {
      renderMentorList('');
      newMentorshipModal.classList.add('show');
    });
  }
  if (newMentorshipClose) {
    newMentorshipClose.addEventListener('click', function () { newMentorshipModal.classList.remove('show'); });
  }
  if (newMentorshipModal) {
    newMentorshipModal.addEventListener('click', function (e) { if (e.target === newMentorshipModal) newMentorshipModal.classList.remove('show'); });
  }
  if (newMentorshipSearch) {
    newMentorshipSearch.addEventListener('input', function () { renderMentorList(newMentorshipSearch.value); });
  }
});

function initMentorshipTabs(mentorData, requestData) {
  var tabs = document.querySelectorAll('.mentorship-tabs .tab-btn');
  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      tabs.forEach(function (t) { return t.classList.remove('active'); });
      tab.classList.add('active');
      renderMentors(tab.getAttribute('data-filter'), mentorData, requestData);
    });
  });
}

function getCSRFToken() {
  var m = document.cookie.match(/\bcsrftoken=([^;]+)/);
  return m ? m[1] : '';
}

function escHtml(str) {
  if (!str) return '';
  var div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function renderMentors(filter, mentorData, requestData) {
  var grid = document.getElementById('mentorshipGrid');
  if (!grid) return;

  if (filter === 'requests') {
    var oldRequests = mentorData.filter(function (m) {
      return m.mentorship && m.mentorship.status === 'pending';
    });
    var newRequests = requestData.filter(function (r) {
      return r.status === 'pending';
    });
    var oldIds = {};
    oldRequests.forEach(function (m) { oldIds[m.id] = true; });
    newRequests = newRequests.filter(function (r) { return !oldIds[r.other_id]; });
    if (oldRequests.length === 0 && newRequests.length === 0) {
      grid.innerHTML = '<div class="empty-state"><p>No pending requests.</p></div>';
      return;
    }
    var html = '';
    oldRequests.forEach(function (mentor) {
      html += renderOldMentorCard(mentor, 'pending');
    });
    newRequests.forEach(function (req) {
      html += renderRequestCard(req);
    });
    grid.innerHTML = html;
    return;
  }

  if (filter === 'sessions') {
    var oldSessions = mentorData.filter(function (m) {
      return m.mentorship && m.mentorship.status === 'accepted';
    });
    if (oldSessions.length === 0) {
      grid.innerHTML = '<div class="empty-state"><p>No active mentorship sessions.</p></div>';
      return;
    }
    grid.innerHTML = oldSessions.map(function (mentor) {
      return renderOldMentorCard(mentor, 'accepted');
    }).join('');
    return;
  }

  var filtered = mentorData.filter(function (m) {
    return (m.role === 'alumni' || m.role === 'senior')
      && (!m.mentorship || m.mentorship.status !== 'accepted');
  });

  if (filtered.length === 0) {
    grid.innerHTML = '<div class="empty-state"><p>No mentors available yet.</p></div>';
    return;
  }

  grid.innerHTML = filtered.map(function (mentor) {
    return renderOldMentorCard(mentor, null);
  }).join('');
}

function renderOldMentorCard(mentor, statusFilter) {
  var avatarHtml = mentor.profile_pic
    ? '<img src="' + mentor.profile_pic + '" alt="" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">'
    : (mentor.name ? mentor.name.split(' ').map(function (s) { return s[0]; }).join('').substring(0, 2).toUpperCase() : '?');

  var actionHtml = '';
  var ms = mentor.mentorship;

  if (!ms) {
    actionHtml = '<form method="POST" action="" style="display:inline;margin:0;">' +
      '<input type="hidden" name="csrfmiddlewaretoken" value="' + getCSRFToken() + '">' +
      '<input type="hidden" name="action" value="start">' +
      '<input type="hidden" name="mentor_id" value="' + mentor.id + '">' +
      '<button type="submit" class="mentor-connect-btn"><i class="fas fa-paper-plane"></i> Request</button></form>';
  } else if (ms.status === 'pending') {
    if (ms.is_mentor) {
      actionHtml = '<div style="display:flex;gap:6px;">' +
        '<form method="POST" action="" style="display:inline;margin:0;">' +
        '<input type="hidden" name="csrfmiddlewaretoken" value="' + getCSRFToken() + '">' +
        '<input type="hidden" name="action" value="accept">' +
        '<input type="hidden" name="mentorship_id" value="' + ms.id + '">' +
        '<button type="submit" class="mentor-connect-btn" style="background:#10B981;"><i class="fas fa-check"></i> Accept</button></form>' +
        '<form method="POST" action="" style="display:inline;margin:0;">' +
        '<input type="hidden" name="csrfmiddlewaretoken" value="' + getCSRFToken() + '">' +
        '<input type="hidden" name="action" value="reject">' +
        '<input type="hidden" name="mentorship_id" value="' + ms.id + '">' +
        '<button type="submit" class="mentor-connect-btn" style="background:#b91c1c;"><i class="fas fa-times"></i> Reject</button></form>' +
      '</div>';
    } else {
      actionHtml = '<span class="mentor-status-badge pending">Pending</span>';
    }
  } else if (ms.status === 'accepted') {
    actionHtml = '<a href="' + ms.id + '/chat/" class="mentor-connect-btn" style="text-decoration:none;display:inline-block;"><i class="fas fa-comments"></i> Chat</a>';
  } else if (ms.status === 'rejected') {
    if (!ms.is_mentor) {
      actionHtml = '<form method="POST" action="" style="display:inline;margin:0;">' +
        '<input type="hidden" name="csrfmiddlewaretoken" value="' + getCSRFToken() + '">' +
        '<input type="hidden" name="action" value="start">' +
        '<input type="hidden" name="mentor_id" value="' + mentor.id + '">' +
        '<button type="submit" class="mentor-connect-btn"><i class="fas fa-paper-plane"></i> Request Again</button></form>';
    } else {
      actionHtml = '<span class="mentor-status-badge rejected">Rejected</span>';
    }
  }

  var badgeText = mentor.badge || mentor.role;

  return '<div class="mentor-card">' +
    '<div class="mentor-card-header">' +
      '<div class="mentor-avatar ' + mentor.role + '" style="overflow:hidden;">' + avatarHtml + '</div>' +
      '<div>' +
        '<h4>' + escHtml(mentor.name) + '</h4>' +
        '<span class="mentor-badge ' + mentor.role + '">' + badgeText + '</span>' +
      '</div>' +
    '</div>' +
    '<p>' + (mentor.bio || 'No bio yet.') + '</p>' +
    (mentor.skills && mentor.skills.length ? '<div class="mentor-skills">' + mentor.skills.map(function (s) { return '<span class="mentor-skill">' + escHtml(s) + '</span>'; }).join('') + '</div>' : '') +
    '<div class="mentor-card-footer">' +
      '<span>' + (mentor.dept || '') + (mentor.semester ? ' \u2022 Sem ' + mentor.semester : '') + '</span>' +
      actionHtml +
    '</div>' +
  '</div>';
}

function renderRequestCard(req) {
  var avatarHtml = req.other_profile_pic
    ? '<img src="' + req.other_profile_pic + '" alt="" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">'
    : '<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:#1C3353;color:#fff;font-weight:700;font-size:1rem;">' + escHtml(req.other_initials) + '</div>';

  var actionHtml = '';
  if (req.status === 'pending' && req.is_received) {
    actionHtml = '<div style="display:flex;gap:6px;">' +
      '<button class="mentor-connect-btn request-accept" data-id="' + req.id + '" style="background:#10B981;"><i class="fas fa-check"></i> Accept</button>' +
      '<button class="mentor-connect-btn request-reject" data-id="' + req.id + '" style="background:#b91c1c;"><i class="fas fa-times"></i> Reject</button>' +
    '</div>';
  } else if (req.status === 'pending') {
    actionHtml = '<span class="mentor-status-badge pending">Pending</span>';
  } else if (req.status === 'accepted') {
    actionHtml = '<span class="mentor-status-badge" style="background:rgba(16,185,129,0.1);color:#10B981;"><i class="fas fa-check-circle"></i> Connected</span>';
  } else if (req.status === 'rejected') {
    actionHtml = '<span class="mentor-status-badge rejected">Rejected</span>';
  }

  var html = '<div class="mentor-card" style="border-left:3px solid #D4AF37;">' +
    '<div class="mentor-card-header">' +
      '<div class="mentor-avatar alumni" style="overflow:hidden;">' + avatarHtml + '</div>' +
      '<div>' +
        '<h4>' + escHtml(req.other_name) + '</h4>' +
        '<span class="mentor-badge alumni">' + escHtml(req.other_dept) + '</span>' +
      '</div>' +
    '</div>' +
    '<div style="margin-bottom:0.6rem;">' +
      '<strong style="font-size:0.85rem;color:#1C3353;">' + escHtml(req.subject) + '</strong>' +
      '<p style="font-size:0.8rem;color:#5a7a8c;margin:0.3rem 0 0;line-height:1.5;">' + escHtml(req.reason) + '</p>' +
    '</div>' +
    '<div class="mentor-card-footer">' +
      '<span>' + req.created_at + '</span>' +
      actionHtml +
    '</div>' +
  '</div>';

  return html;
}

document.addEventListener('click', function (e) {
  var acceptBtn = e.target.closest('.request-accept');
  if (acceptBtn) {
    e.preventDefault();
    var reqId = acceptBtn.dataset.id;
    var params = 'request_id=' + reqId + '&action=accept&csrfmiddlewaretoken=' + encodeURIComponent(getCSRFToken());
    fetch('/api/handle-mentorship-request/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest' },
      body: params
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.ok) { location.reload(); }
      else { alert(data.error || 'Failed to accept.'); }
    })
    .catch(function () { alert('Failed to accept request.'); });
    return;
  }

  var rejectBtn = e.target.closest('.request-reject');
  if (rejectBtn) {
    e.preventDefault();
    var reqId = rejectBtn.dataset.id;
    var params = 'request_id=' + reqId + '&action=reject&csrfmiddlewaretoken=' + encodeURIComponent(getCSRFToken());
    fetch('/api/handle-mentorship-request/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest' },
      body: params
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.ok) { location.reload(); }
      else { alert(data.error || 'Failed to reject.'); }
    })
    .catch(function () { alert('Failed to reject request.'); });
    return;
  }
});
