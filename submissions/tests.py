from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from problems.models import Problem
from .models import Submission

User = get_user_model()

class SubmissionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.admin_user = User.objects.create_superuser(username='admin', password='adminpass123')
        
        self.problem = Problem.objects.create(
            title="Test Problem",
            description="Test Description",
            difficulty="easy",
            points=10
        )
        
        self.submission_data = {
            'problem': self.problem.id,
            'code': 'print("Hello, World!")',
            'language': 'python'
        }
        
        self.submission_list_url = reverse('submission-list')
        self.submission_create_url = reverse('submission-create')
        
    def test_create_submission_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.submission_create_url, self.submission_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Submission.objects.count(), 1)
        self.assertEqual(Submission.objects.get().user, self.user)
        
    def test_create_submission_unauthenticated(self):
        response = self.client.post(self.submission_create_url, self.submission_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_list_submissions_authenticated(self):
        # First create a submission
        submission = Submission.objects.create(
            user=self.user,
            problem=self.problem,
            code='test code',
            language='python'
        )
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.submission_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        
    def test_list_submissions_unauthenticated(self):
        response = self.client.get(self.submission_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_get_submission_detail(self):
        submission = Submission.objects.create(
            user=self.user,
            problem=self.problem,
            code='test code',
            language='python'
        )
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('submission-detail', kwargs={'submission_id': submission.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], submission.id)
        
    def test_request_ai_analysis(self):
        submission = Submission.objects.create(
            user=self.user,
            problem=self.problem,
            code='test code',
            language='python'
        )
        
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse('submission-analyze', kwargs={'submission_id': submission.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that AI status was updated
        submission.refresh_from_db()
        self.assertEqual(submission.ai_status, 'Completed')