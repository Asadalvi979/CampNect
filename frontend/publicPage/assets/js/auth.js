const ROLES = {
  STUDENT: 'student',
  SENIOR: 'senior',
  ALUMNI: 'alumni',
  ADMIN: 'admin'
};

function getCurrentUser() {
  if (window.currentUser) {
    return window.currentUser;
  }
  return null;
}

function isLoggedIn() {
  return getCurrentUser() !== null;
}

function logout() {
  window.location.href = '/logout/';
}

function getRoleLabel(role) {
  const labels = {
    student: 'Student',
    senior: 'Senior Student',
    alumni: 'Alumni',
    admin: 'Admin'
  };
  return labels[role] || role;
}

function getSemesterRange(semester) {
  if (semester >= 1 && semester <= 2) return '1-2';
  if (semester >= 3 && semester <= 5) return '3-5';
  if (semester >= 6 && semester <= 8) return '6-8';
  return '3-5';
}

function getSemesterBadgeColor(semester) {
  if (semester >= 1 && semester <= 2) return '#94A3B8';
  if (semester >= 3 && semester <= 5) return '#2563EB';
  if (semester >= 6 && semester <= 8) return '#10B981';
  return '#2563EB';
}

function canConnectWith(currentUser, targetUser) {
  if (!currentUser || !targetUser) return false;
  if (currentUser.role === ROLES.ALUMNI) return true;
  if (currentUser.role === ROLES.ADMIN) return true;
  const sem = currentUser.semester;
  if (sem >= 1 && sem <= 5) {
    return targetUser.role === ROLES.STUDENT || targetUser.role === ROLES.SENIOR;
  }
  if (sem >= 6 && sem <= 8) {
    return true;
  }
  return false;
}

document.addEventListener('DOMContentLoaded', function() {
  var profileImg = document.getElementById('profileImg');
  var dropdownMenu = document.getElementById('dropdownMenu');
  if (profileImg && dropdownMenu) {
    profileImg.addEventListener('click', function (e) {
      e.stopPropagation();
      dropdownMenu.classList.toggle('show');
    });
    document.addEventListener('click', function (e) {
      if (!profileImg.contains(e.target) && !dropdownMenu.contains(e.target)) {
        dropdownMenu.classList.remove('show');
      }
    });
  }
});
