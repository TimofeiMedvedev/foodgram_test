from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

User = get_user_model()


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Админка пользователей."""
    list_display = ('username', 'email', 'first_name',
                    'last_name', 'follow_amount')
    search_fields = ('username',)
    list_filter = ('username', 'email')
    empty_value_display = '-пусто-'

    def follow_amount(self, obj):
        return obj.following.count()