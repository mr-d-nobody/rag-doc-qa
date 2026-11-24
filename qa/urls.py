from django.urls import path

from . import views

urlpatterns = [
    path("documents", views.documents),
    path("upload", views.upload),
    path("ask", views.ask),
]
