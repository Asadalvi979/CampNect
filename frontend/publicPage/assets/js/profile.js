document.addEventListener('DOMContentLoaded', function () {
    var editAboutBtn = document.getElementById('editAboutBtn');
    var aboutModal = document.getElementById('aboutModal');
    var aboutInput = document.getElementById('aboutInput');
    var aboutText = document.getElementById('aboutText');
    var aboutCancel = document.getElementById('aboutCancel');

    if (editAboutBtn && aboutModal && aboutInput && aboutText) {
        editAboutBtn.addEventListener('click', function () {
            aboutInput.value = aboutText.textContent;
            aboutModal.classList.add('show');
        });
    }

    if (aboutCancel && aboutModal) {
        aboutCancel.addEventListener('click', function () {
            aboutModal.classList.remove('show');
        });
    }

    if (aboutModal) {
        aboutModal.addEventListener('click', function (e) {
            if (e.target === aboutModal) {
                aboutModal.classList.remove('show');
            }
        });
    }

    var editProfileBtn = document.getElementById('editProfileBtn');
    var editProfileModal = document.getElementById('editProfileModal');
    var editProfileCancel = document.getElementById('editProfileCancel');
    var editProfileClose = document.getElementById('editProfileClose');
    var editProfilePicInput = document.getElementById('editProfilePicInput');
    var editProfilePreview = document.getElementById('editProfilePreview');

    if (editProfileBtn && editProfileModal) {
        editProfileBtn.addEventListener('click', function () {
            editProfileModal.classList.add('show');
        });
    }

    function closeEditProfile() {
        if (editProfileModal) {
            editProfileModal.classList.remove('show');
        }
    }

    if (editProfileCancel) {
        editProfileCancel.addEventListener('click', closeEditProfile);
    }

    if (editProfileClose) {
        editProfileClose.addEventListener('click', closeEditProfile);
    }

    if (editProfileModal) {
        editProfileModal.addEventListener('click', function (e) {
            if (e.target === editProfileModal) {
                closeEditProfile();
            }
        });
    }

    if (editProfilePicInput) {
        editProfilePicInput.addEventListener('change', function (e) {
            var file = e.target.files[0];
            if (!file) return;

            var allowedTypes = ['image/png', 'image/jpeg', 'image/gif', 'image/webp'];
            if (allowedTypes.indexOf(file.type) === -1) {
                alert('Only PNG, JPG, GIF and WebP files are allowed.');
                editProfilePicInput.value = '';
                return;
            }
            if (file.size > 5 * 1024 * 1024) {
                alert('File size must be under 5MB.');
                editProfilePicInput.value = '';
                return;
            }

            var reader = new FileReader();
            reader.onload = function (ev) {
                if (editProfilePreview.tagName === 'IMG') {
                    editProfilePreview.src = ev.target.result;
                } else {
                    var img = document.createElement('img');
                    img.src = ev.target.result;
                    img.alt = 'Profile';
                    img.id = 'editProfilePreview';
                    img.style.cssText = 'width:120px;height:120px;border-radius:50%;object-fit:cover;border:4px solid #F6F0D6;box-shadow:0 4px 20px rgba(28,51,83,0.15);';
                    editProfilePreview.parentNode.replaceChild(img, editProfilePreview);
                    editProfilePreview = img;
                }
            };
            reader.readAsDataURL(file);

            var formData = new FormData();
            formData.append('profile_pic', file);
            formData.append('csrfmiddlewaretoken', getCSRFToken());

            var uploadBtn = document.querySelector('.edit-upload-btn');
            var originalText = uploadBtn ? uploadBtn.textContent : '';
            if (uploadBtn) {
                uploadBtn.textContent = 'Uploading...';
                uploadBtn.style.pointerEvents = 'none';
                uploadBtn.style.opacity = '0.6';
            }

            fetch('/api/upload-profile-pic/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCSRFToken()
                }
            })
            .then(function (r) {
                return r.text().then(function (text) {
                    if (!r.ok) {
                        if (r.status === 403) {
                            throw new Error('Session expired. Please refresh the page and try again.');
                        }
                        var errMsg = 'Server error (' + r.status + ')';
                        try {
                            var j = JSON.parse(text);
                            if (j.error) errMsg = j.error;
                        } catch (e) {}
                        throw new Error(errMsg);
                    }
                    var data;
                    try {
                        data = JSON.parse(text);
                    } catch (e) {
                        throw new Error('Invalid response from server');
                    }
                    return data;
                });
            })
            .then(function (data) {
                if (data.success && data.url) {
                    if (editProfilePreview.tagName === 'IMG') {
                        editProfilePreview.src = data.url + '?t=' + Date.now();
                    }
                    var bannerContainer = document.querySelector('.banner-avatar');
                    if (bannerContainer) {
                        var bannerImg = bannerContainer.querySelector('img');
                        if (bannerImg) {
                            bannerImg.src = data.url + '?t=' + Date.now();
                        } else {
                            var newImg = document.createElement('img');
                            newImg.src = data.url + '?t=' + Date.now();
                            newImg.alt = 'Profile';
                            bannerContainer.innerHTML = '';
                            bannerContainer.appendChild(newImg);
                        }
                    }
                    var navbarImg = document.getElementById('profileImg');
                    if (navbarImg) {
                        if (navbarImg.tagName === 'IMG') {
                            navbarImg.src = data.url + '?t=' + Date.now();
                        } else {
                            var navNewImg = document.createElement('img');
                            navNewImg.src = data.url + '?t=' + Date.now();
                            navNewImg.alt = 'Profile';
                            navNewImg.className = 'profile-img';
                            navNewImg.id = 'profileImg';
                            navNewImg.width = 40;
                            navNewImg.height = 40;
                            navbarImg.parentNode.replaceChild(navNewImg, navbarImg);
                        }
                    }
                    var sidebarImg = document.querySelector('.profile-card-avatar img');
                    if (sidebarImg) {
                        sidebarImg.src = data.url + '?t=' + Date.now();
                    } else {
                        var sidebarAvatar = document.querySelector('.profile-card-avatar');
                        if (sidebarAvatar) {
                            var sidebarNewImg = document.createElement('img');
                            sidebarNewImg.src = data.url + '?t=' + Date.now();
                            sidebarNewImg.alt = 'Profile';
                            sidebarNewImg.width = 60;
                            sidebarNewImg.height = 60;
                            sidebarAvatar.innerHTML = '';
                            sidebarAvatar.appendChild(sidebarNewImg);
                        }
                    }
                } else if (data.error) {
                    alert(data.error);
                    editProfilePicInput.value = '';
                }
            })
            .catch(function (err) {
                alert(err.message || 'Upload failed. Please try again.');
                editProfilePicInput.value = '';
            })
            .finally(function () {
                if (uploadBtn) {
                    uploadBtn.textContent = originalText;
                    uploadBtn.style.pointerEvents = '';
                    uploadBtn.style.opacity = '';
                }
            });
        });
    }
});
