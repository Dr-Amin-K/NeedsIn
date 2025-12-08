from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('healthcare/', views.healthcare, name='healthcare'),
    path('humanitarian/', views.humanitarian, name='humanitarian'),
    path('energy/', views.energy, name='energy'),
    path('about/', views.about, name='about'),
    path('map/', views.map_view, name='map'),
    
]
