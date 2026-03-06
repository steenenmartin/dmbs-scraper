from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    if mapping is None:
        return None
    return mapping.get(key)


@register.filter
def contains(values, candidate):
    if values is None:
        return False
    return str(candidate) in {str(v) for v in values}
