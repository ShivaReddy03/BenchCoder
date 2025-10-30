from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Problem, TestCase
from .serializers import ProblemSerializer, ProblemListSerializer, TestCaseSerializer
from utils.pagination import CustomPagination
from django.db.models import Q

class ProblemListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        search_query = request.query_params.get('search', '')
        filter_query = request.query_params.get('difficulty', '')
        problems = Problem.objects.all()

        if search_query:
            problems = problems.filter(Q(title__icontains=search_query))
        if filter_query:
            problems = problems.filter(difficulty=filter_query)

        paginator = CustomPagination()
        paginated_problems = paginator.paginate_queryset(problems, request)
        serializer = ProblemListSerializer(paginated_problems, many=True)
        return paginator.get_paginated_response(serializer.data)

class ProblemDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, problem_id):
        problem = get_object_or_404(Problem, id=problem_id)
        serializer = ProblemSerializer(problem)
        return Response(serializer.data, status=status.HTTP_200_OK)

# Admin-only views for creating problems and test cases
class ProblemCreateView(APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def post(self, request):
        serializer = ProblemSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TestCaseCreateView(APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def post(self, request, problem_id):
        problem = get_object_or_404(Problem, id=problem_id)
        serializer = TestCaseSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(problem=problem)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)