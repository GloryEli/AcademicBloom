from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username


#This is the database per course.
class CourseSpecificEntry(models.Model):
    # Link to the parent course
    subject = models.ForeignKey('SubjectEntry', on_delete=models.CASCADE, related_name='entries')
    
    # Entry-specific data
    hours_studied = models.FloatField(default=0)
    previous_scores = models.FloatField(default=50)
    extracurricular = models.CharField(max_length=10, choices=[('Yes', 'Yes'), ('No', 'No')], default='No')
    sleep_hours = models.FloatField(default=8)
    question_papers = models.IntegerField(default=0)
    motivation = models.CharField(max_length=255, default='Medium')
    preferred_learning_style = models.TextField(default='None')

    # Outputs
    predicted_score = models.FloatField(null=True, blank=True)
    study_guide = models.TextField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject.subject_name} - {self.created_at.strftime('%Y-%m-%d')}"


class StudyPlan(models.Model):
    course = models.ForeignKey(
        "SubjectEntry",
        on_delete=models.CASCADE,
        related_name="study_plans",
    )
    study_days = models.JSONField(default=list)
    session_minutes = models.PositiveSmallIntegerField(default=40)
    schedule = models.JSONField(default=list)
    recommendations = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.course.subject_name} study plan"


#This represents the databse for all courses.
class SubjectEntry(models.Model):
    # Link to the user (student)
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='subject_entries')
    
    # Subject information
    subject_name = models.CharField(max_length=100)
    hours_studied = models.FloatField(default=0)
    previous_scores = models.FloatField(default=50)
    extracurricular = models.CharField(max_length=10, choices=[('Yes', 'Yes'), ('No', 'No')], default='No')
    sleep_hours = models.FloatField(default=8)
    question_papers = models.IntegerField(default=0)
    motivation = models.CharField(max_length=255, default='Medium')
    preferred_learning_style = models.TextField(default='None')


    # Outputs
    predicted_score = models.FloatField(null=True, blank=True)
    study_guide = models.TextField(null=True, blank=True)
    study_plan_pdf = models.FileField(upload_to='study_plans/', null=True, blank=True)
    

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'subject_name')  

    def __str__(self):
        return f"{self.student.user.username} - {self.subject_name}"
 

        
class StudyPlanQuestionnaire(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subjects = models.CharField(max_length=255)  # E.g., comma-separated list or JSON
    learning_style = models.CharField(max_length=50)
    goal = models.CharField(max_length=100)
    hours_per_week = models.IntegerField()
    hours_studied = models.IntegerField(default=0)
    sleep_hours = models.IntegerField(default=0)
    extracurricular = models.IntegerField(default=0)
    question_papers_solved = models.IntegerField(default=0)
    study_habits = models.TextField(blank=True, default="")
    previous_grades = models.IntegerField(default=0)
    motivation_level = models.CharField(max_length=50, default="medium")

    def __str__(self):
        return f"{self.user.username} - Study Plan"