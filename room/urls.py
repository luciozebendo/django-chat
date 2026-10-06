from django.urls import path

from . import views

urlpatterns = [
    path("", views.rooms, name="rooms"),
    path("<slug:slug>/", views.room, name="room"),
    path("<slug:slug>/files/<int:pk>/", views.download_file, name="download_file"),
]
