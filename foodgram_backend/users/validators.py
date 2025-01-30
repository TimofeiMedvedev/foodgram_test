import re

from django.core.exceptions import ValidationError


PATTERN = r'^[\w.@+-]+\Z'


def username_validator(value):

    if value.lower() == 'me':
        raise ValidationError('Неверное имя')

    forbidden_char = ''.join(set(re.sub(PATTERN, '', value)))
    if forbidden_char:
        raise ValidationError(
            f'Эти символы запрещены в имени '
            f'{forbidden_char}'
        )
