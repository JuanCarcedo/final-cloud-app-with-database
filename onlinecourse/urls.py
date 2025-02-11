from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = 'onlinecourse'
urlpatterns = [
    path(route='', view=views.CourseListView.as_view(), name='index'),
    path('registration/', views.registration_request, name='registration'),
    path('login/', views.login_request, name='login'),
    path('logout/', views.logout_request, name='logout'),
    path('<int:pk>/', views.CourseDetailView.as_view(), name='course_details'),
    path('<int:course_id>/enroll/', views.enroll, name='enroll'),
    # 03/2023 JCA Included
    path('<int:course_id>/submit/', views.submit_request, name='submit'),
    path('<int:course_id>/submission/<int:submission_id>/result/', views.exam_result_view, name='exam_result'),
 ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
