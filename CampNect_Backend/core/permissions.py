def is_admin(user):
    return user.is_authenticated and user.role == 'admin' and user.is_staff


def is_alumni(user):
    return user.is_authenticated and user.role == 'alumni'


def is_sem1to4_student(user):
    return user.is_authenticated and user.role == 'student' and user.semester is not None and user.semester < 5


def is_senior_student(user):
    return user.is_authenticated and user.is_student_or_senior() and user.semester is not None and user.semester >= 5


def can_access_alumni_features(user):
    return user.is_authenticated and (user.role != 'student' or (user.semester is not None and user.semester >= 5))


def is_student_to_alumni(user1, user2):
    return (user1.role == 'student' and user2.role == 'alumni') or (user1.role == 'alumni' and user2.role == 'student')


def user_can_message_alumni(user, receiver):
    if is_sem1to4_student(user) and receiver.role == 'alumni':
        return False
    return True
