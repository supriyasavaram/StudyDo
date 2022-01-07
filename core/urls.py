from os import name
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = 'core'
urlpatterns = [
    path('', views.IndexView, name='Index'),
    path('calendar',views.CalendarView, name='Calendar'),
    path('upload/', views.upload_notes, name="upload_notes"),
    path('upload/<str:c_title>', views.upload_notes, name="upload_notes"),
    path('courses/', views.Courses, name='Courses'),
    path('courses/<slug:slug>', views.Courses, name='Courses'),
    path('add-course/', views.create_course, name='create_course'),
    path('<slug:slug>/delete/<int:pk>', views.delete_upload, name="delete_upload"),
    path('changecourse/<slug:slug>', views.course_enroll, name = "course_enroll"),
    path('account/social/login/cancelled/', views.cancelled_login, name='cancelled_login'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)