document.addEventListener('DOMContentLoaded', function () {
    var user = window.currentUser || getCurrentUser();
    if (!user) return;
    initSidebarToggle();
    initProfileDropdown();

    var searchInput = document.getElementById('alumniSearchInput');
    var filterDept = document.getElementById('filterDepartment');
    var filterIndustry = document.getElementById('filterIndustry');
    var filterGradYear = document.getElementById('filterGradYear');
    var clearBtn = document.getElementById('clearFilters');
    var grid = document.getElementById('alumniGrid');
    var empty = document.getElementById('alumniEmpty');
    var resultCount = document.getElementById('resultCount');

    var debounceTimer;

    function loadAlumni() {
        var params = new URLSearchParams();
        var q = searchInput ? searchInput.value.trim() : '';
        var dept = filterDept ? filterDept.value : '';
        var industry = filterIndustry ? filterIndustry.value : '';
        var gradYear = filterGradYear ? filterGradYear.value : '';
        if (q) params.set('q', q);
        if (dept) params.set('department', dept);
        if (industry) params.set('industry', industry);
        if (gradYear) params.set('grad_year', gradYear);

        grid.innerHTML = '<div class="ad-loading"><i class="fas fa-spinner fa-spin"></i> Loading...</div>';
        empty.style.display = 'none';

        fetch('/api/alumni-list/?' + params.toString(), {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (!data.alumni || data.alumni.length === 0) {
                grid.innerHTML = '';
                empty.style.display = 'block';
                resultCount.textContent = '0 alumni found';
                return;
            }
            renderAlumni(data.alumni);
            resultCount.textContent = data.alumni.length + ' alumni found';
        })
        .catch(function () {
            grid.innerHTML = '<div class="ad-empty"><p>Failed to load alumni. Try again.</p></div>';
        });
    }

    function renderAlumni(alumni) {
        grid.innerHTML = alumni.map(function (a) {
            var avatarHtml = a.profile_pic
                ? '<img src="' + a.profile_pic + '" alt="' + escHtml(a.name) + '">'
                : '<span class="ad-initials">' + escHtml(a.initials) + '</span>';

            var companyHtml = '';
            if (a.current_position || a.current_company) {
                companyHtml = '<div class="ad-card-company">' +
                    (a.current_position ? '<span class="ad-card-position">' + escHtml(a.current_position) + '</span>' : '') +
                    (a.current_company ? '<span>' + (a.current_position ? 'at ' : '') + escHtml(a.current_company) + '</span>' : '') +
                '</div>';
            }

            var bioHtml = a.bio ? '<p class="ad-card-bio">' + escHtml(a.bio) + '</p>' : '';

            var skillsHtml = '';
            if (a.skills && a.skills.length) {
                skillsHtml = '<div class="ad-card-skills">' +
                    a.skills.slice(0, 4).map(function (s) { return '<span class="ad-card-skill">' + escHtml(s.trim()) + '</span>'; }).join('') +
                    (a.skills.length > 4 ? '<span class="ad-card-skill">+' + (a.skills.length - 4) + '</span>' : '') +
                '</div>';
            }

            var industryHtml = a.industry ? '<span>' + escHtml(a.industry) + '</span>' : '';
            var deptDisplay = a.department + (industryHtml ? ' \u2022 ' + industryHtml : '');

            var actionsHtml = '';
            var canRequest = (user.role === 'student' || user.role === 'senior') && user.semester !== null && user.semester >= 5;
            if (canRequest) {
                if (!a.mentorship_request_status) {
                    actionsHtml = '<button class="ad-request-btn" data-id="' + a.id + '" data-name="' + escHtml(a.name) + '" data-dept="' + escHtml(deptDisplay) + '"><i class="fas fa-paper-plane"></i> Request Mentorship</button>';
                } else if (a.mentorship_request_status === 'pending') {
                    actionsHtml = '<button class="ad-request-btn pending" disabled><i class="fas fa-hourglass-half"></i> Pending</button>';
                } else if (a.mentorship_request_status === 'accepted') {
                    actionsHtml = '<button class="ad-request-btn accepted" disabled><i class="fas fa-check"></i> Connected</button>';
                } else if (a.mentorship_request_status === 'rejected') {
                    actionsHtml = '<button class="ad-request-btn rejected" disabled><i class="fas fa-times"></i> Rejected</button>';
                }
            } else if (user.role === 'alumni') {
                actionsHtml = '';
            } else {
                actionsHtml = '';
            }
            actionsHtml += ' <button class="ad-view-btn" data-view-id="' + a.id + '" data-req-status="' + (a.mentorship_request_status || '') + '"><i class="fas fa-user"></i> View</button>';

            var gradYearHtml = a.graduation_year ? '<span class="ad-card-year"><i class="fas fa-calendar-alt"></i> Class of ' + a.graduation_year + '</span>' : '';

            return '<div class="ad-card">' +
                '<div class="ad-card-top">' +
                    '<div class="ad-card-avatar">' + avatarHtml + '</div>' +
                    '<div class="ad-card-info">' +
                        '<h3 class="ad-card-name"><a href="/user/' + a.id + '/">' + escHtml(a.name) + '</a></h3>' +
                        '<span class="ad-card-role">Alumni</span>' +
                        '<span class="ad-card-dept">' + deptDisplay + '</span>' +
                    '</div>' +
                '</div>' +
                companyHtml +
                bioHtml +
                skillsHtml +
                '<div class="ad-card-footer">' +
                    gradYearHtml +
                    '<div class="ad-card-actions">' + actionsHtml + '</div>' +
                '</div>' +
            '</div>';
        }).join('');

        document.querySelectorAll('.ad-request-btn[data-id]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var alumniId = btn.dataset.id;
                var alumniName = btn.dataset.name;
                var alumniDept = btn.dataset.dept;
                openMentorshipModal(alumniId, alumniName, alumniDept);
            });
        });
        document.querySelectorAll('.ad-view-btn[data-view-id]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                openAlumniViewModal(btn.dataset.viewId, btn.dataset.reqStatus);
            });
        });
    }

    var uvModal = document.getElementById('alumniViewModal');
    var uvClose = document.getElementById('alumniViewClose');

    function openAlumniViewModal(userId, reqStatus) {
        if (!uvModal) return;
        uvModal.classList.add('show');
        document.getElementById('uvAvatar').innerHTML = '<div class="uv-loading" style="width:100px;height:100px;border-radius:50%;background:#e8eef0;animation:pulse 1.2s infinite;"></div>';
        document.getElementById('uvName').textContent = 'Loading...';
        document.getElementById('uvBadges').innerHTML = '';
        document.getElementById('uvCms').textContent = '';
        document.getElementById('uvActions').innerHTML = '';
        document.getElementById('uvStats').innerHTML = '';
        document.getElementById('uvBody').innerHTML = '';

        fetch('/api/user/' + userId + '/', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(function (r) { return r.json(); })
            .then(function (d) {
                if (d.error) { document.getElementById('uvName').textContent = 'Error loading profile'; return; }
                var name = d.name;
                var initial = name ? name.charAt(0).toUpperCase() : 'U';
                var avatarHtml = d.profile_pic
                    ? '<img src="' + d.profile_pic + '" alt="' + escHtml(name) + '">'
                    : '<div style="width:100px;height:100px;border-radius:50%;background:linear-gradient(135deg,#1C3353,#3a7a5e);color:#F6F0D6;display:flex;align-items:center;justify-content:center;font-size:2.2rem;font-weight:700;border:3px solid #F6F0D6;">' + initial + '</div>';
                document.getElementById('uvAvatar').innerHTML = avatarHtml;
                document.getElementById('uvName').textContent = name;
                var badges = '<span class="uv-badge role">' + escHtml(d.role_slug) + '</span>';
                badges += '<span class="uv-badge dept">' + escHtml(d.department) + '</span>';
                if (d.semester) badges += '<span class="uv-badge sem">Semester ' + d.semester + '</span>';
                document.getElementById('uvBadges').innerHTML = badges;
                document.getElementById('uvCms').innerHTML = '<i class="fas fa-hashtag"></i> ' + escHtml(d.cms) + ' <i class="fas fa-university" style="margin-left:1rem;"></i> Riphah Sahiwal';

                var actionHtml = '';
                if ((user.role === 'student' || user.role === 'senior') && user.semester !== null && user.semester >= 5) {
                    if (!reqStatus) {
                        actionHtml = '<button class="uv-connect-btn" id="uvRequestBtn" data-id="' + userId + '" data-name="' + escHtml(name) + '" data-dept="' + escHtml(d.department) + '"><i class="fas fa-paper-plane"></i> Request Mentorship</button>';
                    } else if (reqStatus === 'pending') {
                        actionHtml = '<button class="uv-connect-btn" style="background:#b45309;" disabled><i class="fas fa-hourglass-half"></i> Pending</button>';
                    } else if (reqStatus === 'accepted') {
                        actionHtml = '<form method="POST" action="/dashboard/" style="margin:0;"><input type="hidden" name="csrfmiddlewaretoken" value="' + getCSRFToken() + '"><input type="hidden" name="action" value="connect"><input type="hidden" name="user_id" value="' + userId + '"><button type="submit" class="uv-connect-btn"><i class="fas fa-user-plus"></i> Connect</button></form>';
                    } else if (reqStatus === 'rejected') {
                        actionHtml = '<button class="uv-connect-btn" id="uvRequestBtn" data-id="' + userId + '" data-name="' + escHtml(name) + '" data-dept="' + escHtml(d.department) + '"><i class="fas fa-paper-plane"></i> Request Again</button>';
                    }
                }
                document.getElementById('uvActions').innerHTML = actionHtml;

                var requestBtn = document.getElementById('uvRequestBtn');
                if (requestBtn) {
                    requestBtn.addEventListener('click', function() {
                        openMentorshipModal(requestBtn.dataset.id, requestBtn.dataset.name, requestBtn.dataset.dept);
                    });
                }

                document.getElementById('uvStats').innerHTML =
                    '<div class="uv-stat"><span class="uv-stat-num">' + d.connections_count + '</span><span class="uv-stat-lbl">Connections</span></div>' +
                    '<div class="uv-stat"><span class="uv-stat-num">' + d.communities_count + '</span><span class="uv-stat-lbl">Communities</span></div>' +
                    '<div class="uv-stat"><span class="uv-stat-num">' + d.projects_count + '</span><span class="uv-stat-lbl">Projects</span></div>' +
                    '<div class="uv-stat"><span class="uv-stat-num">' + d.notes_count + '</span><span class="uv-stat-lbl">Notes Shared</span></div>';

                var bodyHtml = '';
                if (d.bio) bodyHtml += '<div class="uv-section"><h3><i class="fas fa-info-circle"></i> About</h3><p>' + escHtml(d.bio) + '</p></div>';
                bodyHtml += '<div class="uv-section"><h3><i class="fas fa-graduation-cap"></i> Academic Info</h3><div class="uv-info-grid">' +
                    '<div class="uv-info-item"><span class="uv-info-lbl">Department</span><span>' + escHtml(d.department) + '</span></div>' +
                    (d.semester ? '<div class="uv-info-item"><span class="uv-info-lbl">Semester</span><span>' + d.semester + '</span></div>' : '') +
                    '<div class="uv-info-item"><span class="uv-info-lbl">CMS</span><span>' + escHtml(d.cms) + '</span></div>' +
                    '<div class="uv-info-item"><span class="uv-info-lbl">Email</span><span>' + escHtml(d.email) + '</span></div>' +
                    '</div></div>';
                if (d.role_slug === 'alumni') {
                    var profHtml = '<div class="uv-section"><h3><i class="fas fa-briefcase"></i> Professional Info</h3><div class="uv-info-grid">';
                    if (d.graduation_year) profHtml += '<div class="uv-info-item"><span class="uv-info-lbl">Graduation</span><span>Class of ' + d.graduation_year + '</span></div>';
                    if (d.current_company) profHtml += '<div class="uv-info-item"><span class="uv-info-lbl">Company</span><span>' + escHtml(d.current_company) + '</span></div>';
                    if (d.current_position) profHtml += '<div class="uv-info-item"><span class="uv-info-lbl">Position</span><span>' + escHtml(d.current_position) + '</span></div>';
                    if (d.industry) profHtml += '<div class="uv-info-item"><span class="uv-info-lbl">Industry</span><span>' + escHtml(d.industry) + '</span></div>';
                    profHtml += '</div></div>';
                    bodyHtml += profHtml;
                }
                if (d.skills && d.skills.length) {
                    bodyHtml += '<div class="uv-section"><h3><i class="fas fa-bolt"></i> Skills</h3><div class="uv-skills">' +
                        d.skills.map(function (s) { return '<span class="skill-tag">' + escHtml(s) + '</span>'; }).join('') +
                        '</div></div>';
                }
                document.getElementById('uvBody').innerHTML = bodyHtml;
            })
            .catch(function () {
                document.getElementById('uvName').textContent = 'Failed to load profile';
            });
    }

    if (uvClose) {
        uvClose.addEventListener('click', function () { uvModal.classList.remove('show'); });
    }
    if (uvModal) {
        uvModal.addEventListener('click', function (e) {
            if (e.target === uvModal) uvModal.classList.remove('show');
        });
    }

    function escHtml(str) {
        if (!str) return '';
        var div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    if (searchInput) {
        searchInput.addEventListener('input', function () {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(loadAlumni, 300);
        });
    }
    if (filterDept) filterDept.addEventListener('change', loadAlumni);
    if (filterIndustry) filterIndustry.addEventListener('change', loadAlumni);
    if (filterGradYear) filterGradYear.addEventListener('change', loadAlumni);
    if (clearBtn) clearBtn.addEventListener('click', function () {
        if (searchInput) searchInput.value = '';
        if (filterDept) filterDept.value = '';
        if (filterIndustry) filterIndustry.value = '';
        if (filterGradYear) filterGradYear.value = '';
        loadAlumni();
    });

    loadAlumni();

    var mentorshipModal = document.getElementById('mentorshipModal');
    var mentorshipClose = document.getElementById('mentorshipModalClose');
    var mentorshipCancel = document.getElementById('mentorshipModalCancel');

    function openMentorshipModal(alumniId, alumniName, alumniDept) {
        document.getElementById('mentorshipAlumniId').value = alumniId;
        document.getElementById('mentorshipModalName').textContent = alumniName;
        document.getElementById('mentorshipModalDept').textContent = alumniDept;
        document.getElementById('mentorshipSubject').value = '';
        document.getElementById('mentorshipReason').value = '';
        if (mentorshipModal) mentorshipModal.classList.add('show');
    }

    if (mentorshipClose) {
        mentorshipClose.addEventListener('click', function () { mentorshipModal.classList.remove('show'); });
    }
    if (mentorshipCancel) {
        mentorshipCancel.addEventListener('click', function () { mentorshipModal.classList.remove('show'); });
    }
    if (mentorshipModal) {
        mentorshipModal.addEventListener('click', function (e) {
            if (e.target === mentorshipModal) mentorshipModal.classList.remove('show');
        });
    }

    var mentorshipForm = document.getElementById('mentorshipRequestForm');
    if (mentorshipForm) {
        mentorshipForm.addEventListener('submit', function (e) {
            e.preventDefault();
            var alumniId = document.getElementById('mentorshipAlumniId').value;
            var subject = document.getElementById('mentorshipSubject').value.trim();
            var reason = document.getElementById('mentorshipReason').value.trim();
            if (!subject || !reason) { alert('Please fill in all fields.'); return; }

            var params = 'alumni_id=' + encodeURIComponent(alumniId) +
                '&subject=' + encodeURIComponent(subject) +
                '&reason=' + encodeURIComponent(reason) +
                '&csrfmiddlewaretoken=' + encodeURIComponent(getCSRFToken());

            fetch('/api/send-mentorship-request/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest' },
                body: params
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) { alert(data.error); return; }
                mentorshipModal.classList.remove('show');
                loadAlumni();
            })
            .catch(function () { alert('Failed to send request. Try again.'); });
        });
    }

    var professionalModal = document.getElementById('professionalModal');
    var professionalClose = document.getElementById('professionalModalClose');
    var professionalCancel = document.getElementById('professionalModalCancel');
    var editProfessionalBtn = document.getElementById('editProfessionalBtn');

    if (editProfessionalBtn) {
        editProfessionalBtn.addEventListener('click', function () {
            if (user.graduation_year) document.getElementById('profGradYear').value = user.graduation_year;
            if (user.current_company) document.getElementById('profCompany').value = user.current_company;
            if (user.current_position) document.getElementById('profPosition').value = user.current_position;
            if (user.industry) document.getElementById('profIndustry').value = user.industry;
            if (professionalModal) professionalModal.classList.add('show');
        });
    }

    if (professionalClose) {
        professionalClose.addEventListener('click', function () { professionalModal.classList.remove('show'); });
    }
    if (professionalCancel) {
        professionalCancel.addEventListener('click', function () { professionalModal.classList.remove('show'); });
    }
    if (professionalModal) {
        professionalModal.addEventListener('click', function (e) {
            if (e.target === professionalModal) professionalModal.classList.remove('show');
        });
    }

    var professionalForm = document.getElementById('professionalInfoForm');
    if (professionalForm) {
        professionalForm.addEventListener('submit', function (e) {
            e.preventDefault();
            var params = 'graduation_year=' + encodeURIComponent(document.getElementById('profGradYear').value) +
                '&current_company=' + encodeURIComponent(document.getElementById('profCompany').value.trim()) +
                '&current_position=' + encodeURIComponent(document.getElementById('profPosition').value.trim()) +
                '&industry=' + encodeURIComponent(document.getElementById('profIndustry').value.trim()) +
                '&csrfmiddlewaretoken=' + encodeURIComponent(getCSRFToken());

            fetch('/api/update-alumni-profile/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest' },
                body: params
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) { alert(data.error); return; }
                user.graduation_year = document.getElementById('profGradYear').value;
                user.current_company = document.getElementById('profCompany').value.trim();
                user.current_position = document.getElementById('profPosition').value.trim();
                user.industry = document.getElementById('profIndustry').value.trim();
                professionalModal.classList.remove('show');
            })
            .catch(function () { alert('Failed to update. Try again.'); });
        });
    }
});
