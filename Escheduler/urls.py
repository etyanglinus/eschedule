from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('create-shift/', views.create_shift, name='create_shift'),
    path('assign_shift/<int:project_id>/', views.assign_shift, name='assign_shift'),
  
  
    path('create-project/', views.create_project, name='create_project'),
    path('projects/', views.project_list, name='project_list'),
    path('projects/<int:project_id>/', views.project_detail, name='project_detail'),
    path('projects/<int:project_id>/', views.project_schedule, name='project_schedule'),
    path('shifts/request-swap/<int:shift_id>/', views.request_shift_swap, name='request_shift_swap'),
    path('overtime/', views.timesheet, name='timesheet'), 
    path('export_analytics_csv/', views.export_analytics_csv, name='export_analytics_csv'),
    path('employee_analytics/', views.employee_analytics, name='employee_analytics'),
    path('request_time_off/', views.request_time_off, name='request_time_off'),
    path('check_in/<int:shift_id>/', views.check_in, name='check_in'),
    path('check_out/<int:shift_id>/', views.check_out, name='check_out'),

    # path('verify-email/<uidb64>/<token>/', views.verify_email, name='verify_email'),
    path('activate/<uidb64>/<token>/', views.activate_account, name='activate_account'),
    path('api/shifts/<int:shift_id>/', views.get_shift_details, name='get_shift_details'),
    path('submit-shift-report/', views.submit_shift_report, name='submit_shift_report'),
    path('manage_time_off_requests/', views.manage_time_off_requests, name='manage_time_off_requests'),
    path('manage_shift_swaps/', views.manage_shift_swaps, name='manage_shift_swaps'),
]
