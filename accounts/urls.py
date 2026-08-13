from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/trainee/', views.student_register_view, name='register_student'),
    path('register/recruiter/', views.recruiter_register_view, name='register_recruiter'),
    path('register/placement/', views.placement_register_view, name='register_placement'),
    path('login/', views.login_view, name='login'),
    path('login/trainee/', views.student_login_view, name='login_student'),
    path('login/recruiter/', views.recruiter_login_view, name='login_recruiter'),
    path('login/placement/', views.placement_login_view, name='login_placement'),
    path('login/admin/', views.admin_login_view, name='login_admin'),
    path('logout/', views.logout_view, name='logout'),
    path('awaiting-approval/', views.awaiting_approval_view, name='awaiting_approval'),
    path('route-gateway/', views.role_routing_view, name='role_routing'),
]
