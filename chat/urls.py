from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_room, name='chat_room'),
    path('api/register/', views.register_view),
    path('api/login/', views.login_view),
    path('api/csrf/', views.get_csrf),
    path('api/me/', views.current_user),
    path('api/logout/', views.logout_view),
    path('api/upload_image/', views.upload_image),
    path('api/remove_user/', views.remove_user),
]