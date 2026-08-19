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

function loadCommunityMessages() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/communities/' + window.communityId + '/chat/?ajax=1', true);
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

var communitySocket = null;
var communityPollTimer = null;

function startCommunityPolling() {
    if (communityPollTimer) return;
    communityPollTimer = setInterval(loadCommunityMessages, 3000);
}

function stopCommunityPolling() {
    if (communityPollTimer) {
        clearInterval(communityPollTimer);
        communityPollTimer = null;
    }
}

function connectCommunitySocket() {
    if (!window.communityId) return;
    if (communitySocket) { try { communitySocket.close(); } catch (e) {} communitySocket = null; }
    if (!window.WebSocket) { startCommunityPolling(); return; }
    var proto = location.protocol === 'https:' ? 'wss://' : 'ws://';
    try {
        communitySocket = new WebSocket(proto + location.host + '/ws/community/' + window.communityId + '/');
    } catch (e) { startCommunityPolling(); return; }
    communitySocket.onopen = function () { stopCommunityPolling(); };
    communitySocket.onmessage = function (e) {
        try {
            var data = JSON.parse(e.data);
            if (data.type === 'chat_message') loadCommunityMessages();
        } catch (err) {}
    };
    communitySocket.onclose = function () { communitySocket = null; startCommunityPolling(); };
    communitySocket.onerror = function () { try { communitySocket.close(); } catch (e) {} };
}

if (window.communityId) {
    connectCommunitySocket();
    startCommunityPolling();
}
