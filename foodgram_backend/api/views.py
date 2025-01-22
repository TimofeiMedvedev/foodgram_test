from django.contrib.auth import get_user_model
from rest_framework import filters, viewsets


from .serializers import (CustomCreateUserSerializer, CustomUserSerializer,)


User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet модели User."""

    queryset = User.objects.all()
    permission_classes = None
    serializer_class = CustomUserSerializer
    filter_backends = (filters.SearchFilter,)
    # search_fields = ('id',)
    # lookup_field = 'id'
   
    def get_serializer_class(self):
        if self.request.method == 'POST':
           return CustomCreateUserSerializer
