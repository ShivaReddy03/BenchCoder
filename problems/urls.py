from django.urls import path
from . import views

urlpatterns = [
    path('', views.ProblemListView.as_view(), name='problem-list'),
    path('create/', views.ProblemCreateView.as_view(), name='problem-create'),
    path('<int:problem_id>/', views.ProblemDetailView.as_view(), name='problem-detail'),
    path('<int:problem_id>/testcases/', views.TestCaseCreateView.as_view(), name='testcase-create'),
]