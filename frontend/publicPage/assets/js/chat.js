if (typeof window.escHtml !== 'function') {
    window.escHtml = function (str) { if (str == null) return ''; return String(str).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
}

function readJSONData(id) {
    var el = document.getElementById(id);
    if (!el) return [];
    try { return JSON.parse(el.textContent); } catch (e) { return []; }
}
var conversationsData = readJSONData('conversations-data');
var allUsersData = readJSONData('all-users-data');

var conversationsList = document.getElementById('conversationsList');
var chatMessages = document.getElementById('chatMessages');
var chatInput = document.getElementById('chatInput');
var sendBtn = document.getElementById('sendBtn');
var chatUserName = document.getElementById('chatUserName');
var chatStatus = document.getElementById('chatStatus');
var chatSearch = document.getElementById('chatSearch');
var newMsgBtn = document.getElementById('newMsgBtn');
var newMsgModal = document.getElementById('newMsgModal');
var newMsgClose = document.getElementById('newMsgClose');
var newMsgSearch = document.getElementById('newMsgSearch');
var newMsgUserList = document.getElementById('newMsgUserList');
var chatFileInput = document.getElementById('chatFileInput');
var chatPlusBtn = document.getElementById('chatPlusBtn');

var activeConversation = null;
var activeUserId = null;
var searchTerm = '';
var selectedFile = null;

function avatarHtml(pic, initials) {
    return pic ? '<img src="' + escHtml(pic) + '" alt="" class="avatar-img">' : '<span class="avatar-initials">' + escHtml(initials) + '</span>';
}

function renderConversations() {
    var filtered = conversationsData;
    if (searchTerm) {
        var term = searchTerm.toLowerCase();
        filtered = filtered.filter(function (c) { return c.name.toLowerCase().includes(term); });
    }

    conversationsList.innerHTML = filtered.map(function (c) {
        return '<div class="conversation-item ' + (activeConversation === c.id ? 'active' : '') + '" data-id="' + c.id + '">' +
            '<div class="conversation-avatar">' + avatarHtml(c.profile_pic, c.avatar_initials) + '</div>' +
            '<div class="conversation-info">' +
                '<h4>' + escHtml(c.name) + '</h4>' +
                '<p>' + escHtml(c.last_message || '') + '</p>' +
            '</div>' +
            '<div class="conversation-meta">' +
                '<span>' + (c.last_time ? new Date(c.last_time).toLocaleDateString() : '') + '</span>' +
            '</div>' +
        '</div>';
    }).join('');

    document.querySelectorAll('.conversation-item').forEach(function (item) {
        item.addEventListener('click', function () {
            var id = parseInt(item.dataset.id);
            openConversation(id);
        });
    });
}

function openConversation(id) {
    activeConversation = id;
    activeUserId = id;
    try { sessionStorage.setItem('activeChatId', id); } catch(e) {};
    var conv = null;
    for (var i = 0; i < conversationsData.length; i++) {
        if (conversationsData[i].id === id) {
            conv = conversationsData[i];
            break;
        }
    }
    if (!conv) return;

    chatUserName.textContent = conv.name;
    chatStatus.textContent = '';
    var infoEl = document.getElementById('chatUserInfo');
    if (infoEl) infoEl.setAttribute('data-user-id', id);
    chatInput.disabled = false;
    sendBtn.disabled = false;
    chatInput.focus();

    if (typeof connectChatSocket === 'function') connectChatSocket(id);

    if (window.innerWidth <= 768) {
        document.querySelector('.conversations-panel').classList.add('hide');
        document.getElementById('chatWindow').classList.add('show');
    }

    renderConversations();
    renderChatMessages(conv);
}

function renderChatMessages(conv) {
    var partnerPic = conv.profile_pic;
    var partnerInitials = conv.avatar_initials;
    var seen = {};
    var msgs = (conv.messages || []).filter(function (m) {
        var id = m.id;
        if (id === undefined || id === null) return true;
        if (seen[id]) return false;
        seen[id] = true;
        return true;
    });
    if (msgs.length === 0) {
        chatMessages.innerHTML = '<div class="no-conversation-selected"><p><i class="fas fa-comments"></i> No messages yet. Say hello!</p></div>';
    } else {
        chatMessages.innerHTML = msgs.map(function (m) {
            var content = '';
            if (m.text) content += escHtml(m.text);
            if (m.file) {
                var isImg = /\.(jpg|jpeg|png|webp|gif)$/i.test(m.file);
                if (isImg) {
                    content += '<img src="' + escHtml(m.file) + '" class="msg-img-preview" alt="" onclick="openImageLightbox(\'' + jsArg(m.file) + '\')" loading="lazy">';
                } else {
                    content += '<a href="' + escHtml(m.file) + '" class="msg-file" target="_blank" style="display:block;margin-top:6px;color:inherit;"><i class="fas fa-paperclip"></i> ' + escHtml(m.file.split('/').pop()) + '</a>';
                }
            }
            var avatar = avatarHtml(partnerPic, partnerInitials);
            var deleteForm = m.sender_id === window.currentUser.id
                ? '<button class="msg-delete-btn msg-delete-ajax" data-msg-id="' + m.id + '" title="Delete">&times;</button>'
                : '';
            return '<div class="message ' + (m.sender_id === window.currentUser.id ? 'sent' : 'received') + '">' +
                (m.sender_id !== window.currentUser.id ? '<div class="msg-avatar">' + avatar + '</div>' : '') +
                '<div class="msg-bubble">' +
                    deleteForm +
                    content +
                    '<span class="message-time">' + new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + '</span>' +
                '</div>' +
            '</div>';
        }).join('');
    }

    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function getCSRFToken() {
    var match = document.cookie.match(/\bcsrftoken=([^;]+)/);
    if (match) return match[1];
    var el = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return el ? el.value : '';
}

function sendMessage() {
    if (!activeConversation) return;
    var text = chatInput.value.trim();
    if (!text && !selectedFile) return;

    var fd = new FormData();
    fd.append('csrfmiddlewaretoken', getCSRFToken());
    fd.append('receiver_id', activeConversation);
    fd.append('_ajax', '1');
    if (text) fd.append('text', text);
    if (selectedFile) fd.append('file', selectedFile);

    fetch('', {
        method: 'POST',
        body: fd,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCSRFToken()
        }
    })
    .then(function (r) {
        var ct = r.headers.get('content-type') || '';
        if (!r.ok || ct.indexOf('json') === -1) {
            return r.text().then(function (t) {
                throw new Error('Status ' + r.status + ' - ' + t.substring(0, 300));
            });
        }
        return r.json();
    })
    .then(function (data) {
        if (data.ok) {
            var convId = activeConversation;
            var conv = null;
            for (var i = 0; i < conversationsData.length; i++) {
                if (conversationsData[i].id === convId) {
                    conv = conversationsData[i];
                    break;
                }
            }
            if (conv) {
                if (!conv.messages) conv.messages = [];
                if (!(chatSocket && chatSocket.readyState === 1)) {
                    conv.messages.push(data.message);
                }
            }
            chatInput.value = '';
            chatInput.placeholder = 'Type a message...';
            if (selectedFile) {
                selectedFile = null;
                if (chatFileInput) chatFileInput.value = '';
            }
            renderChatMessages(conv);
        } else {
            alert(data.error);
        }
    })
    .catch(function (err) {
        console.error('sendMessage error:', err);
        alert('Failed to send message.\n' + err.message);
    });
}

if (chatFileInput && chatPlusBtn) {
    chatPlusBtn.addEventListener('click', function () {
        chatFileInput.click();
    });
    chatFileInput.addEventListener('change', function () {
        if (chatFileInput.files.length > 0) {
            selectedFile = chatFileInput.files[0];
            chatInput.placeholder = 'File selected: ' + selectedFile.name;
        }
    });
}

if (sendBtn) {
    sendBtn.addEventListener('click', function (e) {
        e.preventDefault();
        sendMessage();
    });
}

if (chatInput) {
    chatInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

document.getElementById('chatMessages').addEventListener('click', function (e) {
    var btn = e.target.closest('.msg-delete-ajax');
    if (!btn) return;
    var msgId = btn.dataset.msgId;
    if (!confirm('Delete this message?')) return;
    var fd = new FormData();
    fd.append('csrfmiddlewaretoken', getCSRFToken());
    fd.append('action', 'delete_message');
    fd.append('message_id', msgId);
    fd.append('_ajax', '1');
    fetch('', {
        method: 'POST',
        body: fd,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCSRFToken()
        }
    })
    .then(function (r) {
        var ct = r.headers.get('content-type') || '';
        if (!r.ok || ct.indexOf('json') === -1) {
            return r.text().then(function (t) {
                throw new Error('Status ' + r.status + ' - ' + t.substring(0, 300));
            });
        }
        return r.json();
    })
    .then(function (data) {
        if (data.ok) {
            var convId = activeConversation;
            var conv = null;
            for (var i = 0; i < conversationsData.length; i++) {
                if (conversationsData[i].id === convId) {
                    conv = conversationsData[i];
                    if (conv.messages) {
                        conv.messages = conv.messages.filter(function (m) { return m.id != msgId; });
                    }
                    break;
                }
            }
            if (conv) renderChatMessages(conv);
        } else {
            alert(data.error);
        }
    })
    .catch(function (err) {
        console.error('delete error:', err);
        alert('Failed to delete message.\n' + err.message);
    });
});

if (chatSearch) {
    chatSearch.addEventListener('input', function () {
        searchTerm = chatSearch.value;
        renderConversations();
    });
}

function renderUserList(filter) {
    var term = (filter || '').toLowerCase();
    var filtered = allUsersData;
    if (term) {
        filtered = filtered.filter(function (u) { return u.name.toLowerCase().includes(term); });
    }

    newMsgUserList.innerHTML = filtered.map(function (u) {
        return '<div class="new-msg-user-item" data-id="' + u.id + '">' +
            '<div class="conversation-avatar" onclick="event.stopPropagation();showUserQuickView(' + u.id + ');return false;">' + avatarHtml(u.profile_pic, u.avatar_initials) + '</div>' +
            '<div class="conversation-info">' +
                '<h4><a href="#" onclick="event.stopPropagation();showUserQuickView(' + u.id + ');return false;" style="color:inherit;text-decoration:none;">' + escHtml(u.name) + '</a></h4>' +
                '<p>' + escHtml(u.department) + (u.role ? ' \u2022 ' + escHtml(u.role) : '') + '</p>' +
            '</div>' +
        '</div>';
    }).join('');

    document.querySelectorAll('.new-msg-user-item').forEach(function (item) {
        item.addEventListener('click', function () {
            var uid = parseInt(item.dataset.id);
            var existing = null;
            for (var i = 0; i < conversationsData.length; i++) {
                if (conversationsData[i].id === uid) {
                    existing = conversationsData[i];
                    break;
                }
            }
            if (!existing) {
                var user = null;
                for (var j = 0; j < allUsersData.length; j++) {
                    if (allUsersData[j].id === uid) {
                        user = allUsersData[j];
                        break;
                    }
                }
                if (user) {
                    conversationsData.unshift({
                        id: user.id,
                        name: user.name,
                        avatar_initials: user.avatar_initials,
                        last_message: '',
                        last_time: null,
                        messages: [],
                    });
                }
            }
            closeNewMsgModal();
            openConversation(uid);
        });
    });
}

function closeNewMsgModal() {
    if (newMsgModal) {
        newMsgModal.classList.remove('show');
    }
}

if (newMsgBtn && newMsgModal) {
    newMsgBtn.addEventListener('click', function () {
        renderUserList(newMsgSearch ? newMsgSearch.value : '');
        newMsgModal.classList.add('show');
        if (newMsgSearch) {
            newMsgSearch.value = '';
            newMsgSearch.focus();
        }
    });
}

if (newMsgClose) {
    newMsgClose.addEventListener('click', closeNewMsgModal);
}

if (newMsgModal) {
    newMsgModal.addEventListener('click', function (e) {
        if (e.target === newMsgModal) {
            closeNewMsgModal();
        }
    });
}

if (newMsgSearch) {
    newMsgSearch.addEventListener('input', function () {
        renderUserList(newMsgSearch.value);
    });
}

function renderSuggestions() {
    var convIds = {};
    for (var i = 0; i < conversationsData.length; i++) {
        convIds[conversationsData[i].id] = true;
    }
    var suggested = allUsersData.filter(function (u) { return !convIds[u.id]; });
    var section = document.getElementById('suggestionsSection');
    var list = document.getElementById('suggestionsList');
    if (!section || !list) return;
    if (suggested.length === 0) {
        section.style.display = 'none';
        return;
    }
    section.style.display = 'block';
    list.innerHTML = suggested.map(function (u) {
        var avatar = u.profile_pic
            ? '<img src="' + escHtml(u.profile_pic) + '" alt="" class="avatar-img">'
            : '<span>' + escHtml(u.avatar_initials) + '</span>';
        return '<div class="suggestion-item" data-id="' + u.id + '">' +
            '<div class="suggestion-avatar" onclick="event.stopPropagation();showUserQuickView(' + u.id + ');return false;">' + avatar + '</div>' +
            '<div class="suggestion-info">' +
                '<h4><a href="#" onclick="event.stopPropagation();showUserQuickView(' + u.id + ');return false;" style="color:inherit;text-decoration:none;">' + escHtml(u.name) + '</a></h4>' +
                '<p>' + escHtml(u.department || '') + (u.role ? ' \u2022 ' + escHtml(u.role) : '') + '</p>' +
            '</div>' +
        '</div>';
    }).join('');
    document.querySelectorAll('.suggestion-item').forEach(function (item) {
        item.addEventListener('click', function () {
            var uid = parseInt(item.dataset.id);
            var existing = null;
            for (var i = 0; i < conversationsData.length; i++) {
                if (conversationsData[i].id === uid) { existing = conversationsData[i]; break; }
            }
            if (!existing) {
                var user = null;
                for (var j = 0; j < allUsersData.length; j++) {
                    if (allUsersData[j].id === uid) { user = allUsersData[j]; break; }
                }
                if (user) {
                    conversationsData.unshift({
                        id: user.id, name: user.name, avatar_initials: user.avatar_initials,
                        profile_pic: user.profile_pic, last_message: '', last_time: null, messages: [],
                    });
                }
            }
            renderSuggestions();
            renderConversations();
            openConversation(uid);
        });
    });
}

document.addEventListener('click', function(e) {
    var chatInfo = document.getElementById('chatUserInfo');
    if (chatInfo && chatInfo.contains(e.target)) {
        var uid = chatInfo.getAttribute('data-user-id');
        if (uid && typeof showUserQuickView === 'function') {
            showUserQuickView(parseInt(uid));
        }
    }
});

renderConversations();
renderSuggestions();

var urlParams = new URLSearchParams(window.location.search);
var openUserId = urlParams.get('user_id');
if (openUserId) {
    openUserId = parseInt(openUserId);
    var found = false;
    for (var i = 0; i < conversationsData.length; i++) {
        if (conversationsData[i].id === openUserId) {
            openConversation(openUserId);
            found = true;
            break;
        }
    }
    if (!found) {
        var user = null;
        for (var j = 0; j < allUsersData.length; j++) {
            if (allUsersData[j].id === openUserId) {
                user = allUsersData[j];
                break;
            }
        }
        if (user) {
            conversationsData.unshift({
                id: user.id,
                name: user.name,
                avatar_initials: user.avatar_initials,
                profile_pic: user.profile_pic,
                last_message: '',
                last_time: null,
                messages: [],
            });
            openConversation(openUserId);
        }
    }
} else {
    var savedId = null;
    try { savedId = parseInt(sessionStorage.getItem('activeChatId')); } catch(e) {}
    if (savedId) {
        var found = false;
        for (var i = 0; i < conversationsData.length; i++) {
            if (conversationsData[i].id === savedId) { found = true; break; }
        }
        if (found) {
            openConversation(savedId);
        } else if (conversationsData.length > 0 && window.innerWidth > 768) {
            openConversation(conversationsData[0].id);
        }
    } else if (conversationsData.length > 0 && window.innerWidth > 768) {
        openConversation(conversationsData[0].id);
    }
}

var chatBackBtn = document.getElementById('chatBackBtn');
if (chatBackBtn) {
    chatBackBtn.addEventListener('click', function() {
        document.querySelector('.conversations-panel').classList.remove('hide');
        document.getElementById('chatWindow').classList.remove('show');
        try { sessionStorage.removeItem('activeChatId'); } catch(e) {}
    });
}

window.addEventListener('resize', function() {
    if (window.innerWidth > 768) {
        document.querySelector('.conversations-panel').classList.remove('hide');
        document.getElementById('chatWindow').classList.remove('show');
    }
});

function openImageLightbox(src) {
    var lb = document.getElementById('imgLightbox');
    var img = document.getElementById('lightboxImg');
    var dl = document.getElementById('lightboxDownload');
    if (!lb || !img) return;
    img.src = src;
    img.classList.remove('zoomed');
    if (dl) dl.setAttribute('href', src);
    lb.classList.add('show');
}

document.addEventListener('click', function(e) {
    var lb = document.getElementById('imgLightbox');
    if (lb && e.target === lb) {
        lb.classList.remove('show');
    }
});

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        var lb = document.getElementById('imgLightbox');
        if (lb) lb.classList.remove('show');
    }
});

var _lbInit = false;
document.addEventListener('DOMContentLoaded', function() {
    if (_lbInit) return;
    _lbInit = true;
    var closeBtn = document.getElementById('lightboxClose');
    var dlBtn = document.getElementById('lightboxDownload');
    var lbImg = document.getElementById('lightboxImg');
    if (closeBtn) closeBtn.addEventListener('click', function() {
        document.getElementById('imgLightbox').classList.remove('show');
    });
    if (dlBtn) dlBtn.addEventListener('click', function(e) {
        e.preventDefault();
        var a = document.createElement('a');
        a.href = document.getElementById('lightboxImg').src;
        a.download = '';
        document.body.appendChild(a);
        a.click();
        a.remove();
    });
    if (lbImg) lbImg.addEventListener('click', function() {
        this.classList.toggle('zoomed');
    });
});

function loadChatMessages(userId) {
    if (!userId) return;
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/chat/?ajax=1&user_id=' + userId, true);
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4 && xhr.status === 200) {
            try {
                var data = JSON.parse(xhr.responseText);
                if (data.ok) {
                    var conv = null;
                    for (var i = 0; i < conversationsData.length; i++) {
                        if (conversationsData[i].id === userId) {
                            conv = conversationsData[i];
                            break;
                        }
                    }
                    if (conv) {
                        var oldLen = conv.messages ? conv.messages.length : 0;
                        conv.messages = data.messages;
                        if (data.messages.length !== oldLen) {
                            renderChatMessages(conv);
                        }
                    }
                }
            } catch(e) {}
        }
    };
    xhr.send();
}

function removeDeletedMessage(userId, msgId) {
    var conv = null;
    for (var i = 0; i < conversationsData.length; i++) {
        if (conversationsData[i].id === userId) {
            conv = conversationsData[i];
            break;
        }
    }
    if (!conv || !conv.messages) return;
    var before = conv.messages.length;
    conv.messages = conv.messages.filter(function (m) { return m.id != msgId; });
    if (conv.messages.length !== before) renderChatMessages(conv);
}

var chatSocket = null;
var chatPollTimer = null;

function startChatPolling() {
    if (chatPollTimer) return;
    chatPollTimer = setInterval(function () {
        if (activeUserId) loadChatMessages(activeUserId);
    }, 3000);
}

function stopChatPolling() {
    if (chatPollTimer) {
        clearInterval(chatPollTimer);
        chatPollTimer = null;
    }
}

function connectChatSocket(userId) {
    if (!userId) return;
    if (chatSocket) { try { chatSocket.close(); } catch (e) {} chatSocket = null; }
    if (!window.WebSocket) { startChatPolling(); return; }
    var proto = location.protocol === 'https:' ? 'wss://' : 'ws://';
    try {
        chatSocket = new WebSocket(proto + location.host + '/ws/chat/' + userId + '/');
    } catch (e) { startChatPolling(); return; }
    chatSocket.onopen = function () { stopChatPolling(); };
    chatSocket.onmessage = function (e) {
        try {
            var data = JSON.parse(e.data);
            if (data.type === 'chat_message') loadChatMessages(userId);
            else if (data.type === 'chat_message_deleted') removeDeletedMessage(userId, data.message_id);
        } catch (err) {}
    };
    chatSocket.onclose = function () { chatSocket = null; startChatPolling(); };
    chatSocket.onerror = function () { try { chatSocket.close(); } catch (e) {} };
}

if (window.currentUser) {
    connectChatSocket(activeUserId);
    startChatPolling();
}
