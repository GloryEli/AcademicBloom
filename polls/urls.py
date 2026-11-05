from django.urls import path
from . import views
from .views import SubjectWizard
from .forms import Step1Form, Step2Form, Step3Form, Step4Form, Step5Form
from .views import SubjectWizard, subject_results_view
from .views import delete_course


urlpatterns = [
    path("", views.sparkles_preview, name='home'),

    path('sparkles/', views.sparkles_preview, name='sparkles_preview'),

    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),

    path('create-subject/', SubjectWizard.as_view(
        [Step1Form, Step2Form, Step3Form, Step4Form, Step5Form]
    ), name='create_subject_entry'),
    
    path('new-course/', views.new_course, name='new_course'),   
    path('results/<int:subject_id>/', subject_results_view, name='subject_results'),
    path('study-plans/create/', views.create_study_plan, name='create_study_plan'),
    path('study-plans/<int:plan_id>/', views.study_plan_detail, name='study_plan_detail'),
    
    # path("generate-study-plan/<int:entry_id>/", views.generate_study_plan, name="generate_study_plan"),
    path('hero/', views.hero_view, name='hero'),

    path('course/<int:course_id>/', views.subject_dashboard, name='subject_dashboard'),

    # path('charts/', views.my_charts_view, name='my_charts'),
    
    path('guidance/<int:course_id>/', views.get_guidance_view, name='get_guidance'),
    
    path("student_dashboard/", views.student_dashboard_view, name="student_dashboard"),
    
    path('delete-course/<int:course_id>/', delete_course, name='delete_course'),
    
    path('course/new-prediction/<int:course_id>/', views.new_prediction, name='new_prediction'),

    path('course/<int:course_id>/history/', views.course_history_dashboard, name='course_history'),
]
