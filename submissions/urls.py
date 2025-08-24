from django.urls import path
from . import views

urlpatterns = [
    path('', views.SubmissionListView.as_view(), name='submission-list'),
    path('create/', views.SubmissionCreateView.as_view(), name='submission-create'),
    path('<int:submission_id>/', views.SubmissionDetailView.as_view(), name='submission-detail'),
    path('<int:submission_id>/analyze/', views.SubmissionAnalysisView.as_view(), name='submission-analyze'),
]