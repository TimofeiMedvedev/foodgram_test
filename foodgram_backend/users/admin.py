from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import Follow

User = get_user_model()


@admin.register(User)
class User(UserAdmin):
    list_display = ('username', 'email', 'first_name',
                    'last_name', 'follow_amount')
    search_fields = ('username', 'email')
    list_filter = ('username',)
    empty_value_display = '-пусто-'
    fieldsets = UserAdmin.fieldsets

    def follow_amount(self, obj):
        return obj.following.count()
    

@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('user', 'following')