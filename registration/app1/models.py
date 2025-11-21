# app1/models.py
from django.db import models
from django.contrib.auth.models import User

class ResumeMatch(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resume_file = models.FileField(upload_to='resumes/')
    job_description = models.TextField()
    match_score = models.FloatField(null=True, blank=True)  # 0-100
    suggestions = models.TextField(blank=True)  # plain text suggestions
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.created_at.date()}"
