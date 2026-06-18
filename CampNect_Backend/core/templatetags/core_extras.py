from django import template

register = template.Library()

IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp', 'gif']


@register.filter
def split(value, delimiter=','):
    if not value:
        return []
    return [s.strip() for s in value.split(delimiter)]


@register.filter
def endswith(value, suffix):
    if not value:
        return False
    return value.lower().endswith(suffix.lower())


@register.filter
def is_image(value):
    if not value:
        return False
    ext = value.lower().rsplit('.', 1)[-1]
    return ext in IMAGE_EXTENSIONS
