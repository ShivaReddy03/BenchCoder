from rest_framework import serializers
from .models import Submission

class SubmissionSerializer(serializers.ModelSerializer):
    problem_title = serializers.CharField(source='problem.title', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Submission
        fields = '__all__'
        read_only_fields = ('id', 'submitted_at', 'verdict', 'execution_time', 
                           'memory_used', 'ai_feedback', 'ai_status')

class SubmissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = ('problem', 'code', 'language')

class SubmissionListSerializer(serializers.ModelSerializer):
    # Instead of importing from other apps, define the fields directly
    problem_title = serializers.CharField(source='problem.title', read_only=True)
    problem_difficulty = serializers.CharField(source='problem.difficulty', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Submission
        fields = ('id', 'problem_title', 'problem_difficulty', 'user_username', 
                 'language', 'verdict', 'execution_time', 'submitted_at')