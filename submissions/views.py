from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Submission
from .serializers import SubmissionSerializer, SubmissionCreateSerializer, SubmissionListSerializer

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
            submission = serializer.save(
                user=request.user,
                verdict='P'
            )
            
            # Simulate judging process
            submission.verdict = 'AC'
            submission.execution_time = 0.5
            submission.memory_used = 10.5
            submission.save()
            
            return Response(SubmissionSerializer(submission).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SubmissionAnalysisView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, submission_id):
        submission = get_object_or_404(Submission, id=submission_id, user=request.user)
        
        submission.ai_status = 'Processing'
        submission.save()
        
        # Simulate AI analysis
        submission.ai_feedback = "This is a simulated AI feedback. Your code looks good but could be optimized for better performance."
        submission.ai_status = 'Completed'
        submission.save()
        
        return Response(SubmissionSerializer(submission).data, status=status.HTTP_200_OK)