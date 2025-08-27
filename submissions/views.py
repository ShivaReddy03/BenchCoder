from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Submission
from .serializers import SubmissionSerializer, SubmissionCreateSerializer, SubmissionListSerializer

# Use a try-except block to handle the import
try:
    from judge.tasks import judge_submission, analyze_submission
except ImportError:
    # Fallback for when judge app is not available
    def judge_submission(submission_id):
        # Mock function for testing
        submission = Submission.objects.get(id=submission_id)
        submission.verdict = 'AC'
        submission.execution_time = 0.5
        submission.memory_used = 10.5
        submission.save()
    
    def analyze_submission(submission_id):
        # Mock function for testing
        submission = Submission.objects.get(id=submission_id)
        submission.ai_feedback = "Mock AI analysis"
        submission.ai_status = 'Completed'
        submission.save()

class SubmissionListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        submissions = Submission.objects.filter(user=request.user).order_by('-submitted_at')
        serializer = SubmissionListSerializer(submissions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class SubmissionDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, submission_id):
        submission = get_object_or_404(Submission, id=submission_id, user=request.user)
        serializer = SubmissionSerializer(submission)
        return Response(serializer.data, status=status.HTTP_200_OK)

class SubmissionCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = SubmissionCreateSerializer(data=request.data)
        if serializer.is_valid():
            # Create submission with pending status
            submission = serializer.save(
                user=request.user,
                verdict='P'  # Pending
            )
            
            # Enqueue the judging task
            judge_submission.delay(submission.id)
            
            return Response(SubmissionSerializer(submission).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SubmissionAnalysisView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, submission_id):
        submission = get_object_or_404(Submission, id=submission_id, user=request.user)
        
        # Update AI status
        submission.ai_status = 'Processing'
        submission.save()
        
        # Enqueue the AI analysis task
        analyze_submission.delay(submission.id)
        
        return Response(SubmissionSerializer(submission).data, status=status.HTTP_200_OK)