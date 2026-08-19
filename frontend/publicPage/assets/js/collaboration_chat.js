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

function loadCollabMessages() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/collaboration/' + window.postId + '/chat/?ajax=1', true);
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

var collabSocket = null;
var collabPollTimer = null;

function startCollabPolling() {
    if (collabPollTimer) return;
    collabPollTimer = setInterval(loadCollabMessages, 3000);
}

function stopCollabPolling() {
    if (collabPollTimer) {
        clearInterval(collabPollTimer);
        collabPollTimer = null;
    }
}

function connectCollabSocket() {
    if (!window.postId) return;
    if (collabSocket) { try { collabSocket.close(); } catch (e) {} collabSocket = null; }
    if (!window.WebSocket) { startCollabPolling(); return; }
    var proto = location.protocol === 'https:' ? 'wss://' : 'ws://';
    try {
        collabSocket = new WebSocket(proto + location.host + '/ws/collaboration/' + window.postId + '/');
    } catch (e) { startCollabPolling(); return; }
    collabSocket.onopen = function () { stopCollabPolling(); };
    collabSocket.onmessage = function (e) {
        try {
            var data = JSON.parse(e.data);
            if (data.type === 'chat_message') loadCollabMessages();
        } catch (err) {}
    };
    collabSocket.onclose = function () { collabSocket = null; startCollabPolling(); };
    collabSocket.onerror = function () { try { collabSocket.close(); } catch (e) {} };
}

if (window.postId) {
    connectCollabSocket();
    startCollabPolling();
}
