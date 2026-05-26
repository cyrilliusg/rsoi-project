"""URL routing for the IdP app."""
from django.urls import path

from . import views

urlpatterns = [
    path('.well-known/openid-configuration', views.discovery, name='oidc-discovery'),
    path('api/v1/jwks', views.jwks, name='jwks'),
    path('api/v1/authorize', views.authorize, name='authorize'),
    path('api/v1/token', views.token, name='token'),
    path('api/v1/logout', views.logout_view, name='logout'),
    path('api/v1/userinfo', views.UserInfoView.as_view(), name='userinfo'),
    path('api/v1/users', views.UsersView.as_view(), name='users'),
    path('login', views.login_view, name='login'),
]
