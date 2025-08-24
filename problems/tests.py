from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model  
from .models import Problem, TestCase

# Use get_user_model to avoid import issues
User = get_user_model()

class ProblemTests(APITestCase):
    def setUp(self):
        # Create a regular user and an admin user
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.admin_user = User.objects.create_superuser(username='admin', password='adminpass123')
        
        # Create a sample problem
        self.problem = Problem.objects.create(
            title="Test Problem",
            description="Test Description",
            difficulty="easy",
            points=10
        )
        
        # URLs
        self.problem_list_url = reverse('problem-list')
        self.problem_detail_url = reverse('problem-detail', kwargs={'problem_id': self.problem.id})
        
    def test_get_problems_authenticated(self):
        # Login as regular user
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.problem_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
    def test_get_problems_unauthenticated(self):
        response = self.client.get(self.problem_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_get_problem_detail(self):
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.problem_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], self.problem.title)
        
    def test_create_problem_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            "title": "New Problem",
            "description": "New Problem Description",
            "difficulty": "medium",
            "points": 15
        }
        
        response = self.client.post(reverse('problem-create'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Problem.objects.count(), 2)  # Should have 2 problems now
        
    def test_create_problem_as_regular_user(self):
        self.client.force_authenticate(user=self.user)
        
        data = {
            "title": "New Problem",
            "description": "New Problem Description",
            "difficulty": "medium",
            "points": 15
        }
        
        response = self.client.post(reverse('problem-create'), data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)