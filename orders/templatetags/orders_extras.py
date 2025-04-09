from django import template

register = template.Library()

@register.filter
def get_month_name(month_num, months):
    """Возвращает русское название месяца по его номеру"""
    for num, name in months:
        if num == month_num:
            return name
    return month_num

@register.filter
def get_item(dictionary, key):
    """Возвращает значение из словаря по ключу"""
    return dictionary.get(key, key) 