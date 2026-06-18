document.addEventListener('DOMContentLoaded', function () {
  var currentUser = window.currentUser || getCurrentUser();
  if (!currentUser) return;
  initSidebarToggle();
  initProfileDropdown();
  initPage();
});

function initPage() {
  var user = window.currentUser || getCurrentUser();
  if (!user) return;
  updateUserProfile(user);
  filterSidebarNav(user);
  initFeedTabs();
  renderFeed('all');
  initPostInteractions();
  initInlineComments();
}

function updateUserProfile(user) {
  var nameEl = document.querySelector('.profile-card h3');
  var badgeEl = document.querySelector('.profile-badge');
  var imgEl = document.querySelector('.profile-card-avatar img');
  if (nameEl && user.name) nameEl.textContent = user.name;
  if (badgeEl) {
    if (user.role === 'alumni') {
      badgeEl.textContent = user.department + ' \u2022 Alumni';
      badgeEl.setAttribute('data-sem', 'alumni');
    } else if (user.role === 'admin') {
      badgeEl.textContent = 'Administrator';
      badgeEl.setAttribute('data-sem', 'admin');
    } else {
      var label = user.role === 'senior' ? 'Senior' : 'Student';
      badgeEl.textContent = user.department + ' - Semester ' + user.semester + ' (' + label + ')';
      badgeEl.setAttribute('data-sem', getSemesterRange(user.semester));
    }
  }
  if (imgEl && user.avatar) imgEl.src = user.avatar;
}

function filterSidebarNav(user) {
  var navItems = document.querySelectorAll('.sidebar-nav .nav-item');
  var role = user.role;
  navItems.forEach(function (item) {
    var text = item.textContent.trim();
    if (role === 'alumni') {
      if (text.includes('Notes') || text.includes('Collaboration')) { item.style.display = 'none'; }
      else if (text.includes('Mentorship')) { item.style.display = 'flex'; }
      else { item.style.display = 'flex'; }
      return;
    }
    if (role === 'senior') {
      if (text.includes('Mentorship')) { item.style.display = 'flex'; }
      return;
    }
    if (role === 'student') {
      if (text.includes('Mentorship')) { item.style.display = 'flex'; }
      return;
    }
    if (role === 'admin') { item.style.display = 'none'; }
  });
}

function initFeedTabs() {
  var feedTabs = document.querySelector('.feed-tabs');
  if (!feedTabs) return;
  document.querySelectorAll('.tab-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.tab-btn').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      renderFeed(btn.getAttribute('data-filter'));
    });
  });
}

function getTypeLabel(type) {
  var labels = { announcement: 'Announcement', notes: 'Notes Upload', collaboration: 'Collaboration', media: 'Media' };
  return labels[type] || type;
}

function makeAvatarHtml(avatar, name) {
  if (avatar) {
    return '<img src="' + avatar + '" alt="" class="post-user-img">';
  }
  var initials = name ? name.charAt(0).toUpperCase() : '?';
  return '<div class="post-avatar">' + initials + '</div>';
}

function sanitizeHtml(str) {
  var div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function renderFeed(filter) {
  var feedContainer = document.getElementById('feedContainer');
  if (!feedContainer) return;
  var feedData = Array.isArray(window.feedData) ? window.feedData : [];
  var filteredData = filter === 'all' ? feedData : feedData.filter(function (item) { return item.type === filter; });
  if (filteredData.length === 0) {
    feedContainer.innerHTML = '<div class="empty-state"><p>No posts yet.</p></div>';
    return;
  }
  feedContainer.innerHTML = filteredData.map(function (post) {
    var statsHtml = '';
    var actionsHtml = '';
    var extraHtml = '';
    var avatarHtml = makeAvatarHtml(post.avatar, post.author);
    var likedClass = post.liked ? 'liked' : '';
    var likeText = post.liked ? '<i class="fas fa-heart"></i> Liked' : 'Like';
    var safeDept = post.authorDept ? sanitizeHtml(post.authorDept) : '';
    var dept = safeDept ? '<span class="post-dept"> \u2014 ' + safeDept + '</span>' : '';
    var safeAuthor = sanitizeHtml(post.author || 'CampNect');
    var safeTime = sanitizeHtml(post.time || '');
    var safeTitle = sanitizeHtml(post.title || '');
    var safeContent = sanitizeHtml(post.content || '');
    var safeSubject = sanitizeHtml(post.subject || '');
    var safeFileUrl = post.fileUrl ? post.fileUrl.replace(/"/g, '&quot;') : '';

    if (post.type === 'notes') {
      extraHtml = '<span class="note-subject">' + safeSubject + '</span>';
      if (safeFileUrl) {
        extraHtml += '<br><a href="' + safeFileUrl + '" target="_blank" class="note-feed-link">Open Note</a>';
        extraHtml += ' <a href="' + safeFileUrl + '" download class="note-feed-link">Download</a>';
      }
      statsHtml = '<div class="post-stats"><span>0 likes</span><span>0 comments</span></div>';
      actionsHtml = '<div class="post-actions"><button class="action-btn ' + likedClass + '" data-type="' + post.type + '" data-id="' + post.id + '" data-liked="' + post.liked + '">' + likeText + '</button><button class="action-btn comment-btn" data-type="' + post.type + '" data-id="' + post.id + '">Comment</button></div>';
    } else if (post.type === 'collaboration') {
      statsHtml = '<div class="post-stats"><span>' + (post.likes || 0) + ' likes</span><span>' + (post.comments || 0) + ' comments</span></div>';
      actionsHtml = '<div class="post-actions"><button class="action-btn ' + likedClass + '" data-type="' + post.type + '" data-id="' + post.id + '" data-liked="' + post.liked + '">' + likeText + '</button><button class="action-btn comment-btn" data-type="' + post.type + '" data-id="' + post.id + '">Comment</button></div>';
    } else {
      statsHtml = '<div class="post-stats"><span>' + (post.likes || 0) + ' likes</span><span>' + (post.comments || 0) + ' comments</span></div>';
      actionsHtml = '<div class="post-actions"><button class="action-btn ' + likedClass + '" data-type="' + post.type + '" data-id="' + post.id + '" data-liked="' + post.liked + '">' + likeText + '</button><button class="action-btn comment-btn" data-type="' + post.type + '" data-id="' + post.id + '">Comment</button></div>';
    }

    return '<article class="feed-post" data-type="' + post.type + '" data-id="' + post.id + '">' +
      '<div class="post-header">' +
        '<div class="post-user">' +
          avatarHtml +
          '<div class="post-user-info">' +
            '<h4>' + safeAuthor + dept + '</h4>' +
            '<span class="post-time">' + safeTime + ' \u2014 ' + getTypeLabel(post.type) + '</span>' +
          '</div>' +
        '</div>' +
        '<button class="post-menu" aria-label="Post options">...</button>' +
      '</div>' +
      '<div class="post-content">' +
        '<h3>' + (post.isPinned ? '<span class="pin-badge">Pinned</span>' : '') + safeTitle + '</h3>' +
        '<p>' + safeContent + '</p>' +
        extraHtml +
      '</div>' +
      statsHtml +
      actionsHtml +
      '<div class="comments-section" style="display:none;">' +
        '<div class="comments-list"></div>' +
        '<div class="comment-input-wrap" style="display:flex;gap:8px;margin-top:8px;">' +
          '<input type="text" class="comment-input" placeholder="Write a comment..." style="flex:1;padding:8px 12px;border:1px solid #d0d8d4;border-radius:8px;font-size:13px;">' +
          '<button class="comment-submit-btn" style="padding:6px 14px;background:#1C3353;color:#fff;border:none;border-radius:8px;cursor:pointer;">Send</button>' +
        '</div>' +
      '</div>' +
    '</article>';
  }).join('');
}

function csrfToken() {
  var meta = document.querySelector('meta[name="csrf-token"]');
  if (meta) return meta.getAttribute('content');
  var input = document.querySelector('input[name="csrfmiddlewaretoken"]');
  if (input) return input.value;
  var cookie = document.cookie.match(/csrftoken=([^;]+)/);
  return cookie ? cookie[1] : '';
}

function initPostInteractions() {
  document.addEventListener('click', function (e) {
    var likeBtn = e.target.closest('.action-btn[data-type]');
    if (likeBtn && !likeBtn.classList.contains('comment-btn')) {
      e.preventDefault();
      var postType = likeBtn.dataset.type;
      var postId = likeBtn.dataset.id;
      var liked = likeBtn.dataset.liked === 'true';
      var action = liked ? (postType === 'announcement' ? 'unlike_announcement' : 'unlike_collab') : (postType === 'announcement' ? 'like_announcement' : 'like_collab');
      var params = 'action=' + action + '&' + (postType === 'announcement' ? 'announcement_id' : 'post_id') + '=' + postId + '&csrfmiddlewaretoken=' + encodeURIComponent(csrfToken());

      fetch(window.location.href, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest' },
        body: params
      })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.liked !== undefined) {
          likeBtn.dataset.liked = data.liked ? 'true' : 'false';
          likeBtn.innerHTML = data.liked ? '<i class="fas fa-heart"></i> Liked' : 'Like';
          likeBtn.classList.toggle('liked', data.liked);
          var statsEl = likeBtn.closest('.feed-post').querySelector('.post-stats');
          if (statsEl) {
            var likeSpan = statsEl.querySelector('span:first-child');
            if (likeSpan) likeSpan.textContent = data.count + ' likes';
          }
        }
      })
      .catch(function () {});
      return;
    }

    var commentBtn = e.target.closest('.comment-btn');
    if (commentBtn) {
      e.preventDefault();
      var postEl = commentBtn.closest('.feed-post');
      var section = postEl ? postEl.querySelector('.comments-section') : null;
      if (section) {
        if (section.style.display === 'block') {
          section.style.display = 'none';
          return;
        }
        section.style.display = 'block';
        var list = section.querySelector('.comments-list');
        if (list && list.children.length === 0) {
          loadCommentsInline(commentBtn.dataset.type, commentBtn.dataset.id, section);
        }
        var input = section.querySelector('.comment-input');
        if (input) { input.focus(); input.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
      }
      return;
    }

    var replyBtn = e.target.closest('.reply-btn');
    if (replyBtn) {
      e.preventDefault();
      var commentItem = replyBtn.closest('.comment-item, .reply-item');
      var replyWrap = commentItem ? commentItem.querySelector('.reply-input-wrap') : null;
      if (replyWrap) {
        replyWrap.style.display = replyWrap.style.display === 'none' ? 'flex' : 'none';
        if (replyWrap.style.display === 'flex') {
          var inp = replyWrap.querySelector('.reply-input');
          if (inp) inp.focus();
        }
      }
      return;
    }

    var joinBtn = e.target.closest('.join-btn, .connect-btn, .follow-btn');
    if (joinBtn) {
      if (joinBtn.classList.contains('joined') || joinBtn.textContent.trim() === 'Connected' || joinBtn.textContent.trim() === 'Following') return;
    }
  });
}

function initInlineComments() {
  document.addEventListener('click', function (e) {
    var submitBtn = e.target.closest('.comment-submit-btn') || e.target.closest('.reply-submit-btn');
    if (!submitBtn) return;
    var section = submitBtn.closest('.comments-section');
    if (!section) return;
    var isReply = submitBtn.classList.contains('reply-submit-btn');
    var input = isReply ? submitBtn.closest('.reply-input-wrap').querySelector('.reply-input') : section.querySelector('.comment-input');
    var text = input ? input.value.trim() : '';
    if (!text) return;
    var postEl = section.closest('.feed-post');
    if (!postEl) return;
    var type = postEl.dataset.type;
    var id = postEl.dataset.id;
    var parentId = isReply ? submitBtn.dataset.parentId : '';
    var params = 'action=add_comment&post_type=' + type + '&post_id=' + id + '&text=' + encodeURIComponent(text) + '&csrfmiddlewaretoken=' + encodeURIComponent(csrfToken());
    if (parentId) params += '&parent_id=' + parentId;
    fetch(window.location.href, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest' },
      body: params
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.error) { alert(data.error); return; }
      input.value = '';
      loadCommentsInline(type, id, section);
      var statsEl = postEl.querySelector('.post-stats');
      if (statsEl) {
        var countSpan = statsEl.querySelector('span:nth-child(2)');
        if (countSpan) {
          var current = parseInt(countSpan.textContent) || 0;
          countSpan.textContent = (current + 1) + ' comments';
        }
      }
    })
    .catch(function () {});
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter') return;
    var input = e.target.closest('.comment-input') || e.target.closest('.reply-input');
    if (!input) return;
    e.preventDefault();
    var section = input.closest('.comments-section');
    if (!section) return;
    var btn = input.closest('.comment-input-wrap, .reply-input-wrap').querySelector('.comment-submit-btn, .reply-submit-btn');
    if (btn) btn.click();
  });
}

function loadCommentsInline(type, id, section) {
  var list = section.querySelector('.comments-list');
  if (!list) return;
  list.innerHTML = '<p style="color:#8aa99b;text-align:center;">Loading...</p>';
  var params = 'action=get_comments&post_type=' + type + '&post_id=' + id + '&csrfmiddlewaretoken=' + encodeURIComponent(csrfToken());
  fetch(window.location.href, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest' },
    body: params
  })
  .then(function (r) { return r.json(); })
  .then(function (data) {
    if (!data.comments || data.comments.length === 0) {
      list.innerHTML = '<p style="color:#8aa99b;text-align:center;">No comments yet.</p>';
      return;
    }
    var tree = {};
    var topLevel = [];
    data.comments.forEach(function (c) {
      c.replies = [];
      tree[c.id] = c;
      if (c.parent_id) {
        if (!tree[c.parent_id]) tree[c.parent_id] = { replies: [] };
        tree[c.parent_id].replies.push(c);
      } else {
        topLevel.push(c);
      }
    });
    function renderComment(c, isReply) {
      var cls = isReply ? 'reply-item' : 'comment-item';
      var avatar = c.user ? c.user.charAt(0).toUpperCase() : '?';
      return '<div class="' + cls + '">'
        + '<div class="comment-avatar">' + avatar + '</div>'
        + '<div class="comment-body">'
          + '<span class="comment-author">' + escHtml(c.user) + '</span>'
          + '<span class="comment-text">' + escHtml(c.text) + '</span>'
          + '<div class="comment-footer">'
            + '<span class="comment-time">' + (c.created_at ? c.created_at.slice(0, 10) : '') + '</span>'
            + '<button class="reply-btn" data-id="' + c.id + '">Reply</button>'
          + '</div>'
          + '<div class="reply-input-wrap" style="display:none;margin-top:6px;">'
            + '<input type="text" class="reply-input" placeholder="Write a reply..." style="flex:1;padding:6px 10px;border:1px solid #d0d8d4;border-radius:6px;font-size:12px;width:100%;">'
            + '<button class="reply-submit-btn" data-parent-id="' + c.id + '" style="margin-top:4px;padding:4px 10px;background:#1C3353;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:12px;">Reply</button>'
          + '</div>'
          + (c.replies && c.replies.length ? c.replies.map(function (r) { return renderComment(r, true); }).join('') : '')
        + '</div>'
      + '</div>';
    }
    list.innerHTML = topLevel.map(function (c) { return renderComment(c, false); }).join('');
  })
  .catch(function () { list.innerHTML = '<p style="color:#cc4444;text-align:center;">Failed to load comments.</p>'; });
}

function escHtml(str) {
  var div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function initSidebarToggle() {
  var menuToggle = document.getElementById('menuToggle');
  var sidebar = document.getElementById('sidebar');
  var overlay = document.getElementById('overlay');
  if (menuToggle && sidebar) {
    menuToggle.addEventListener('click', function () {
      sidebar.classList.add('open');
      if (overlay) overlay.classList.add('show');
      document.body.style.overflow = 'hidden';
    });
  }
  if (overlay) {
    overlay.addEventListener('click', function () {
      sidebar.classList.remove('open');
      overlay.classList.remove('show');
      document.body.style.overflow = '';
    });
  }
}

function initProfileDropdown() {}
