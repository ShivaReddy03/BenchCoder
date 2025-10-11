from django.db import models
from django.conf import settings

class Submission(models.Model):
    VERDICT_CHOICES = [
        ('AC', 'Accepted'),
        ('WA', 'Wrong Answer'),
        ('TLE', 'Time Limit Exceeded'),
        ('MLE', 'Memory Limit Exceeded'),
        ('RE', 'Runtime Error'),
        ('CE', 'Compilation Error'),
        ('PE', 'Presentation Error'),
        ('OT', 'Other'),
        ('P', 'Pending')
    ]
    
    LANGUAGE_CHOICES = [
        ('python', 'Python'),
        ('java', 'Java'),
        ('cpp', 'C++'),
        ('c', 'C'),
        ('javascript', 'JavaScript'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    problem = models.ForeignKey('problems.Problem', on_delete=models.CASCADE)  # Use string reference
    code = models.TextField()
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='python')
    verdict = models.CharField(max_length=20, choices=VERDICT_CHOICES, default='P')
    execution_time = models.FloatField(null=True, blank=True)
    memory_used = models.FloatField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    ai_feedback = models.TextField(null=True, blank=True)
    ai_status = models.CharField(max_length=30, default='Not Requested')
    
    def __str__(self):
        return f"{self.user.username} - {self.problem.title} - {self.verdict}"