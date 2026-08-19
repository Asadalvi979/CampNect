(function() {
    if (typeof window.escHtml !== 'function') {
        window.escHtml = function (str) { if (str == null) return ''; return String(str).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
    }
    var bell = document.getElementById('notificationBell');
    var dropdown = document.getElementById('notificationDropdown');
    var badge = document.getElementById('notificationBadge');
    var list = document.getElementById('notificationList');
    var markAllBtn = document.getElementById('markAllRead');

    if (!bell) return;

    function fetchCount() {
        fetch('/api/notifications/unread-count/')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.count > 0) {
                    badge.textContent = data.count > 99 ? '99+' : data.count;
                    badge.style.display = 'flex';
                } else {
                    badge.style.display = 'none';
                }
            })
            .catch(function() {});
    }

    function handleMentorshipAction(notifId, requestId, action) {
        var params = 'request_id=' + requestId + '&action=' + action + '&csrfmiddlewaretoken=' + encodeURIComponent(getCSRFToken());
        fetch('/api/handle-mentorship-request/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest' },
            body: params
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.ok) {
                var formData = new FormData();
                formData.append('notification_id', notifId);
                formData.append('csrfmiddlewaretoken', getCSRFToken());
                fetch('/api/notifications/', { method: 'POST', body: formData }).then(fetchNotifications).catch(fetchNotifications);
            } else {
                alert(data.error || 'Failed to ' + action);
            }
        })
        .catch(function() { alert('Failed to ' + action); });
    }

    function markAsReadAndRemove(el) {
        var id = el.dataset.id;
        var formData = new FormData();
        formData.append('notification_id', id);
        formData.append('csrfmiddlewaretoken', getCSRFToken());
        fetch('/api/notifications/', { method: 'POST', body: formData })
            .then(function() {
                el.remove();
                fetchCount();
                var remaining = list.querySelectorAll('.notification-item').length;
                if (remaining === 0) {
                    list.innerHTML = '<div class="notification-empty"><i class="fas fa-bell-slash"></i><p>No notifications</p></div>';
                }
            })
            .catch(function() {});
    }

    function fetchNotifications() {
        list.innerHTML = '<div class="notification-loading">Loading...</div>';
        fetch('/api/notifications/')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (!data.notifications || data.notifications.length === 0) {
                    list.innerHTML = '<div class="notification-empty"><i class="fas fa-bell-slash"></i><p>No notifications</p></div>';
                    return;
                }
                var html = '';
                for (var i = 0; i < data.notifications.length; i++) {
                    var n = data.notifications[i];
                    var cls = n.is_read ? 'notification-item' : 'notification-item unread';
                    html += '<div class="' + cls + '" data-id="' + n.id + '" data-type="' + escHtml(n.type) + '" data-related="' + escHtml(n.related_object_id || '') + '">';
                    html += '<div class="notification-icon"><i class="fas fa-' + (n.type.indexOf('mentorship') !== -1 ? 'graduation-cap' : 'bell') + '"></i></div>';
                    html += '<div class="notification-body">';
                    html += '<div class="notification-title">' + escHtml(n.title) + '</div>';
                    if (n.message) html += '<div class="notification-msg">' + escHtml(n.message) + '</div>';
                    html += '<div class="notification-time">' + escHtml(n.created_at) + '</div>';
                    if (n.type === 'mentorship_request' && !n.is_read) {
                        html += '<div class="notification-actions">' +
                            '<button class="notif-accept" data-notif-id="' + n.id + '" data-req-id="' + escHtml(n.related_object_id || '') + '"><i class="fas fa-check"></i> Accept</button>' +
                            '<button class="notif-reject" data-notif-id="' + n.id + '" data-req-id="' + escHtml(n.related_object_id || '') + '"><i class="fas fa-times"></i> Reject</button>' +
                        '</div>';
                    }
                    html += '</div></div>';
                }
                list.innerHTML = html;

                list.querySelectorAll('.notif-accept').forEach(function(btn) {
                    btn.addEventListener('click', function(e) {
                        e.stopPropagation();
                        handleMentorshipAction(btn.dataset.notifId, btn.dataset.reqId, 'accept');
                    });
                });
                list.querySelectorAll('.notif-reject').forEach(function(btn) {
                    btn.addEventListener('click', function(e) {
                        e.stopPropagation();
                        handleMentorshipAction(btn.dataset.notifId, btn.dataset.reqId, 'reject');
                    });
                });
                list.querySelectorAll('.notification-item.unread').forEach(function(el) {
                    el.addEventListener('click', function() {
                        markAsReadAndRemove(el);
                    });
                });
                fetchCount();
            })
            .catch(function() {
                list.innerHTML = '<div class="notification-empty"><p>Failed to load</p></div>';
            });
    }

    bell.addEventListener('click', function(e) {
        e.stopPropagation();
        var isOpen = dropdown.classList.contains('show');
        dropdown.classList.toggle('show');
        if (!isOpen) fetchNotifications();
    });

    document.addEventListener('click', function(e) {
        if (!bell.contains(e.target)) dropdown.classList.remove('show');
    });

    if (markAllBtn) {
        markAllBtn.addEventListener('click', function() {
            var formData = new FormData();
            formData.append('csrfmiddlewaretoken', getCSRFToken());
            fetch('/api/notifications/', { method: 'POST', body: formData })
                .then(function() {
                    list.innerHTML = '<div class="notification-empty"><i class="fas fa-bell-slash"></i><p>No notifications</p></div>';
                    fetchCount();
                })
                .catch(function() {});
        });
    }

    fetchCount();
    setInterval(fetchCount, 30000);
})();
