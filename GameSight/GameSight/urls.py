from django.contrib import admin
from django.urls import path

from GameSightApp.views import index, dashboard
from GameSightApp import features
from GameSightApp.views import ingresar, salir


urlpatterns = [
    path("ingresar/", 
        ingresar, 
        name="ingresar"),

    path("salir/", 
        salir, 
        name="salir"),
    
    path(
        "admin/",
        admin.site.urls,
    ),

    path(
        "",
        index,
        name="index",
    ),

    path(
        "dashboard/",
        dashboard,
        name="dashboard",
    ),

    path(
        "usuario/",
        features.user_overview,
        name="dashboard_usuario",
    ),

    path(
        "analizar/",
        features.analizar,
        name="gamesight_analizar",
    ),

    path(
        "historial/",
        features.historial,
        name="gamesight_historial",
    ),

    path(
        "favoritos/",
        features.favoritos,
        name="gamesight_favoritos",
    ),

    path(
        "resultado/<int:pk>/",
        features.resultado,
        name="gamesight_resultado",
    ),

    path(
        "resultado/<int:pk>/favorito/",
        features.favorito,
        name="gamesight_favorito",
    ),
]