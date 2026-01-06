from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Dictionary dan qiymat olish.
    Template da: {{ my_dict|get_item:key }}
    """
    if dictionary:
        return dictionary.get(key, '-')
    return '-'


@register.filter
def subtract(value, arg):
    """
    Ayirish.
    Template da: {{ total|subtract:completed }}
    """
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """
    Foiz hisoblash.
    Template da: {{ completed|percentage:total }}
    """
    try:
        if total == 0:
            return 0
        return int((value / total) * 100)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0


@register.filter
def multiply(value, arg):
    """
    Ko'paytirish.
    Template da: {{ value|multiply:2 }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def divide(value, arg):
    """
    Bo'lish.
    Template da: {{ value|divide:2 }}
    """
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.simple_tag
def status_color(status):
    """
    Status uchun rang qaytarish.
    Template da: {% status_color task.status %}
    """
    colors = {
        'draft': '#95A5A6',
        'active': '#27AE60',
        'paused': '#F39C12',
        'completed': '#3498DB',
        'cancelled': '#E74C3C',
        'archived': '#7F8C8D',
        'pending': '#95A5A6',
        'seen': '#3498DB',
        'in_progress': '#F39C12',
        'low': '#27AE60',
        'medium': '#F39C12',
        'high': '#E67E22',
        'urgent': '#E74C3C',
    }
    return colors.get(status, '#95A5A6')


@register.simple_tag
def status_icon(status):
    """
    Status uchun icon qaytarish.
    Template da: {% status_icon task.status %}
    """
    icons = {
        'draft': 'bi-pencil',
        'active': 'bi-play-circle',
        'paused': 'bi-pause-circle',
        'completed': 'bi-check-circle',
        'cancelled': 'bi-x-circle',
        'archived': 'bi-archive',
        'pending': 'bi-clock',
        'seen': 'bi-eye',
        'in_progress': 'bi-arrow-repeat',
    }
    return icons.get(status, 'bi-circle')


@register.filter
def truncate_middle(value, length=30):
    """
    Matnni o'rtasidan qisqartirish.
    Template da: {{ long_text|truncate_middle:20 }}
    """
    value = str(value)
    if len(value) <= length:
        return value

    half = length // 2
    return f"{value[:half]}...{value[-half:]}"


@register.filter
def phone_format(value):
    """
    Telefon raqamni formatlash.
    Template da: {{ phone|phone_format }}
    +998901234567 -> +998 90 123 45 67
    """
    if not value:
        return '-'

    value = str(value).replace(' ', '').replace('-', '')

    if len(value) == 13 and value.startswith('+998'):
        return f"{value[:4]} {value[4:6]} {value[6:9]} {value[9:11]} {value[11:]}"

    return value


@register.filter
def time_ago(value):
    """
    Vaqtni "... oldin" formatida ko'rsatish.
    Template da: {{ created_at|time_ago }}
    """
    from django.utils import timezone

    if not value:
        return '-'

    now = timezone.now()
    diff = now - value

    seconds = diff.total_seconds()

    if seconds < 60:
        return 'Hozirgina'
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f'{minutes} daqiqa oldin'
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f'{hours} soat oldin'
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f'{days} kun oldin'
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f'{weeks} hafta oldin'
    else:
        return value.strftime('%d.%m.%Y')


@register.inclusion_tag('components/progress_bar.html')
def progress_bar(value, max_value=100, color='primary', height=8):
    """
    Progress bar komponenti.
    Template da: {% progress_bar 75 100 'success' 10 %}
    """
    try:
        percentage = int((value / max_value) * 100) if max_value > 0 else 0
    except (ValueError, TypeError):
        percentage = 0

    return {
        'percentage': percentage,
        'color': color,
        'height': height,
    }