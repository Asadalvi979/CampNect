var chatMessages = document.getElementById('chatMessages');
var msgInput = document.getElementById('msgInput');
var fileInput = document.getElementById('fileInput');
var plusBtn = document.getElementById('plusBtn');

if (plusBtn && fileInput) {
    plusBtn.addEventListener('click', function () {
        fileInput.click();
    });
}

if (fileInput && msgInput) {
    fileInput.addEventListener('change', function () {
        if (fileInput.files.length > 0) {
            msgInput.placeholder = 'File selected: ' + fileInput.files[0].name;
        }
    });
}

function scrollToBottom() {
    if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

function convertImageLinks(container) {
    if (!container) container = document;
    var links = container.querySelectorAll('.msg-file');
    var imgExt = /\.(jpg|jpeg|png|webp|gif)$/i;
    [].forEach.call(links, function(link) {
        if (imgExt.test(link.getAttribute('href'))) {
            var img = document.createElement('img');
            img.src = link.getAttribute('href');
            img.className = 'msg-img-preview';
            img.alt = '';
            img.loading = 'lazy';
            img.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                openImageLightbox(this.src);
            });
            link.parentNode.replaceChild(img, link);
        }
    });
}

scrollToBottom();
convertImageLinks(chatMessages);

function loadMentorshipMessages() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/mentorship/' + window.mentorshipId + '/chat/?ajax=1', true);
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            try {
                var data = JSON.parse(xhr.responseText);
                if (data.html) {
                    var oldScrollTop = chatMessages.scrollTop;
                    var oldHeight = chatMessages.scrollHeight;
                    chatMessages.innerHTML = data.html;
                    convertImageLinks(chatMessages);
                    if (chatMessages.scrollHeight > oldHeight) {
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    } else {
                        chatMessages.scrollTop = oldScrollTop;
                    }
                }
            } catch (e) {}
        }
    };
    xhr.send();
}

var mentorshipSocket = null;
var mentorshipPollTimer = null;

function startMentorshipPolling() {
    if (mentorshipPollTimer) return;
    mentorshipPollTimer = setInterval(loadMentorshipMessages, 3000);
}

function stopMentorshipPolling() {
    if (mentorshipPollTimer) {
        clearInterval(mentorshipPollTimer);
        mentorshipPollTimer = null;
    }
}

function connectMentorshipSocket() {
    if (!window.mentorshipId) return;
    if (mentorshipSocket) { try { mentorshipSocket.close(); } catch (e) {} mentorshipSocket = null; }
    if (!window.WebSocket) { startMentorshipPolling(); return; }
    var proto = location.protocol === 'https:' ? 'wss://' : 'ws://';
    try {
        mentorshipSocket = new WebSocket(proto + location.host + '/ws/mentorship/' + window.mentorshipId + '/');
    } catch (e) { startMentorshipPolling(); return; }
    mentorshipSocket.onopen = function () { stopMentorshipPolling(); };
    mentorshipSocket.onmessage = function (e) {
        try {
            var data = JSON.parse(e.data);
            if (data.type === 'chat_message') loadMentorshipMessages();
        } catch (err) {}
    };
    mentorshipSocket.onclose = function () { mentorshipSocket = null; startMentorshipPolling(); };
    mentorshipSocket.onerror = function () { try { mentorshipSocket.close(); } catch (e) {} };
}

if (window.mentorshipId) {
    connectMentorshipSocket();
    startMentorshipPolling();
}
