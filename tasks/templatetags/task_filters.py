from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Dictionary dan key bo'yicha qiymat olish"""
    if dictionary is None:
        return None

    if isinstance(dictionary, dict):
        # String key bilan qidirish
        result = dictionary.get(str(key))
        if result is not None:
            return result
        # Original key bilan qidirish
        return dictionary.get(key)

    return None


@register.filter
def get_value(response):
    """TaskResponse dan qiymatni olish"""
    if response is None:
        return ''

    if hasattr(response, 'value_text') and response.value_text:
        return response.value_text
    if hasattr(response, 'value_number') and response.value_number is not None:
        return response.value_number
    if hasattr(response, 'value_date') and response.value_date:
        return response.value_date
    if hasattr(response, 'value_boolean') and response.value_boolean is not None:
        return response.value_boolean
    if hasattr(response, 'value_choice') and response.value_choice:
        return response.value_choice

    return ''


@register.filter
def multiply(value, arg):
    """Ko'paytirish"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """Foiz hisoblash"""
    try:
        if total == 0:
            return 0
        return round((float(value) / float(total)) * 100, 1)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0