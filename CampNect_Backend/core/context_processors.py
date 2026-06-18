from datetime import date
from .models import Event


def upcoming_events(request):
    if request.user.is_authenticated and hasattr(request.user, 'role'):
        events = Event.objects.filter(date__gte=date.today())[:5]
        return {'upcoming_events': events}
    return {'upcoming_events': []}
