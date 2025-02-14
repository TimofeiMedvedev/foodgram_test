from recipes.models import Ingredient


def counting_shop_list(ingredients):
    download_cart_list = ('customer order\n'
                          'Ингредиенты:\n')
    for ingredient in ingredients:
        download_cart_list += (
                f"{ingredient['ingredient__name']}"
                f"{ingredient['amount']}"
                f"{ingredient['ingredient__measurement_unit']}\n"
            )
        return download_cart_list
