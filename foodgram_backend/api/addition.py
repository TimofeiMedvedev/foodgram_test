from recipes.models import Ingredient


def counting_shop_list(ingredients):
    download_cart_list = ('customer order\n'
                          'Ингредиенты:\n')
    for item in ingredients:
        ingredient = Ingredient.objects.get(pk=item['ingredient'])
        amount = item['amount']
        download_cart_list += (
            f'{ingredient.name}  - '
            f'{amount}'
            f'{ingredient.measurement_unit}\n'
        )
        return download_cart_list
