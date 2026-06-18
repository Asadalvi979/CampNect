document.addEventListener('DOMContentLoaded', function () {
    var editAboutBtn = document.getElementById('editAboutBtn');
    var aboutModal = document.getElementById('aboutModal');
    var aboutInput = document.getElementById('aboutInput');
    var aboutText = document.getElementById('aboutText');
    var aboutCancel = document.getElementById('aboutCancel');
    var aboutSave = document.getElementById('aboutSave');

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

    if (aboutSave && aboutModal) {
        aboutSave.addEventListener('click', function () {
            var newBio = aboutInput.value.trim();
            if (newBio) {
                aboutText.textContent = newBio;
            }
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

    if (editProfilePicInput && editProfilePreview) {
        editProfilePicInput.addEventListener('change', function (e) {
            var file = e.target.files[0];
            if (file) {
                var reader = new FileReader();
                reader.onload = function (ev) {
                    editProfilePreview.src = ev.target.result;
                };
                reader.readAsDataURL(file);
            }
        });
    }
});
