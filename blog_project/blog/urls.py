
from django.urls import path
from . import views
urlpatterns = [
    path('', views.home, name='home_'),
    path('login/',                views.login_view,   name='login'),
    path('signup/',               views.signup_view,  name='signup'),
    path('logout/',               views.logout_view,  name='logout'),
    path('home/',                 views.home,         name='home_'),
    path('post/<int:id>/',        views.post_details, name='post_details'),
    path('post/new/',             views.post_create,  name='post_create'),
    path('post/<int:id>/edit/',   views.post_edit,    name='post_edit'),
    path('post/<int:id>/delete/', views.post_delete,  name='post_delete'),
] 
