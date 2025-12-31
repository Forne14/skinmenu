from django import template

register = template.Library()

@register.filter
def hex_to_rgb(value: str) -> str:
    """
    "#e5e0d6" -> "229 224 214"
    """
    if not value:
        return ""
    v = value.strip().lstrip("#")
    if len(v) == 3:
        v = "".join([c * 2 for c in v])
    try:
        r = int(v[0:2], 16)
        g = int(v[2:4], 16)
        b = int(v[4:6], 16)
        return f"{r} {g} {b}"
    except Exception:
        return ""
