from django import forms
from .models import SubjectEntry
from .models import StudyPlanQuestionnaire

class Step1Form(forms.Form):
    subject_name = forms.CharField(
        label="Subject Name",
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter subject name (e.g., Mathematics, Physics)',
            'class': 'form-control'
        })
    )

    previous_scores = forms.FloatField(
        label="Previous Scores (%)",  
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={
            'step': '0.1',
            'placeholder': '50.0',
            'class': 'form-control'
        })
    )

    def __init__(self, *args, **kwargs):
        self.mode = kwargs.pop('mode', 'not_editing')
        self.course = kwargs.pop('course', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Debug print
        print(f"DEBUG Step1Form init: mode={self.mode}, course={self.course}")
        print(f"DEBUG Step1Form init: course subject_name={getattr(self.course, 'subject_name', 'None') if self.course else 'None'}")

        # In new_prediction mode, make subject name read-only
        if self.mode == 'new_prediction':
            self.fields['subject_name'].widget = forms.TextInput(attrs={
                'readonly': True,
                'class': 'form-control readonly-field',
                'style': 'background-color: #f8f9fa; cursor: not-allowed;'
            })
            self.fields['subject_name'].help_text = "Subject name cannot be changed when making a new prediction"


    def clean_subject_name(self):
        name = self.cleaned_data['subject_name'].strip()
        
        if not name:
            raise forms.ValidationError("Subject name cannot be empty.")
        
        # Debug print toPyrhon manage.py see what's happening
        print(f"DEBUG clean_subject_name: mode={getattr(self, 'mode', 'unknown')}, course={getattr(self, 'course', None)}")

        # Use clear if-else structure
        if hasattr(self, 'mode') and self.mode == 'new_prediction':
            # NEW PREDICTION MODE: Return original course name and skip all validation
            if hasattr(self, 'course') and self.course:
                print(f"DEBUG: new_prediction mode - returning original course name: {self.course.subject_name}")
                return self.course.subject_name
            else:
                print("DEBUG: new_prediction mode but no course found - falling back to normal validation")
                # Fallback if course is not available
                pass
        
        # NOT EDITING MODE: Check for duplicates
        elif hasattr(self, 'mode') and self.mode == 'not_editing':
            if hasattr(self, 'user') and self.user and hasattr(self.user, 'student'):
                print(f"DEBUG: not_editing mode - checking for duplicates with name: {name}")
                # Check for duplicate subject names for this user
                qs = SubjectEntry.objects.filter(
                    student=self.user.student, 
                    subject_name__iexact=name
                )
                
                if qs.exists():
                    raise forms.ValidationError(
                        f"You already have a subject named '{name}'. "
                        "Please choose a different name or make a new prediction for the existing subject."
                    )
        
        # Default case (shouldn't happen but for safety)
        else:
            print(f"DEBUG: Unknown mode '{getattr(self, 'mode', 'None')}' - proceeding with normal validation")
        
        return name



    def clean_previous_scores(self):
        data = self.cleaned_data['previous_scores']
        if not (0 <= data <= 100):
            raise forms.ValidationError("Previous scores must be between 0 and 100.")
        return data

class Step2Form(forms.Form):
    hours_studied = forms.FloatField(label="How many hours do you study per week?")

    def clean_hours_studied(self):
        data = self.cleaned_data['hours_studied']
        if data < 0:
            raise forms.ValidationError("Hours studied must be positive.")
        return data
    
class Step3Form(forms.Form):
    extracurricular = forms.ChoiceField(label="Do you participate in extracurriculars?", choices=[('Yes', 'Yes'), ('No', 'No')])

class Step4Form(forms.Form):
    sleep_hours = forms.FloatField(label="How many hours do you sleep on average?")

    def clean_sleep_hours(self):
        data = self.cleaned_data['sleep_hours']
        if not (0 < data < 24):
            raise forms.ValidationError("Let's be serious here. We have just 24 hours in a day.")
        return data

class Step5Form(forms.Form):
    MOTIVATION_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    
    LEARNING_STYLE_CHOICES = [
        ('visual', 'Visual Learning (charts, diagrams, images)'),
        ('auditory', 'Auditory Learning (lectures, discussions, music)'),
        ('kinesthetic', 'Kinesthetic Learning (hands-on, movement, practice)'),
        ('reading_writing', 'Reading/Writing Learning (notes, lists, texts)'),
        ('social', 'Social Learning (group study, collaboration)'),
    ]
    
    question_papers = forms.IntegerField(
        label="How many question papers have you practiced?",
        min_value=0,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Enter number of question papers',
            'class': 'form-control'
        })
    )
    
    motivation = forms.ChoiceField(
        label="What is your motivation level?",
        choices=MOTIVATION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    preferred_learning_style = forms.MultipleChoiceField(
        label="Select your preferred learning styles (choose 1-3 options)",
        choices=LEARNING_STYLE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'learning-style-checkboxes'
        })
    )
    
    def clean_question_papers(self):
        data = self.cleaned_data['question_papers']
        if data < 0:
            raise forms.ValidationError("Number of question papers must be non-negative.")
        return data
    
    def clean_preferred_learning_style(self):
        data = self.cleaned_data['preferred_learning_style']
        if len(data) < 1:
            raise forms.ValidationError("Please select at least 1 learning style.")
        if len(data) > 3:
            raise forms.ValidationError("Please select at most 3 learning styles.")
        return data


class StudyPlanForm(forms.Form):
    DAY_CHOICES = [
        ("Monday", "Monday"),
        ("Tuesday", "Tuesday"),
        ("Wednesday", "Wednesday"),
        ("Thursday", "Thursday"),
        ("Friday", "Friday"),
        ("Saturday", "Saturday"),
        ("Sunday", "Sunday"),
    ]
    SESSION_LENGTH_CHOICES = [
        (25, "25 minutes"),
        (40, "40 minutes"),
        (50, "50 minutes"),
        (60, "60 minutes"),
    ]

    course = forms.ModelChoiceField(
        queryset=SubjectEntry.objects.none(),
        label="Choose a course",
        empty_label="Select a course",
    )
    study_days = forms.MultipleChoiceField(
        choices=DAY_CHOICES,
        label="Which days work for you?",
        widget=forms.CheckboxSelectMultiple,
        required=True,
    )
    session_minutes = forms.TypedChoiceField(
        choices=SESSION_LENGTH_CHOICES,
        coerce=int,
        label="How long should each study session be?",
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["course"].queryset = SubjectEntry.objects.filter(
            student__user=user
        ).order_by("subject_name")
        self.initial.setdefault("study_days", ["Monday", "Wednesday", "Friday"])
        self.initial.setdefault("session_minutes", 40)




# class StudyPlanQuestionnaireForm(forms.ModelForm):
#     subjects = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'e.g., Math, Physics'}))
    
#     class Meta:
#         model = StudyPlanQuestionnaire
#         fields = ['subjects', 'learning_style', 'goal', 'hours_per_week',  'hours_studied', 'sleep_hours', 'extracurricular', 'question_papers_solved', 'study_habits', 'previous_grades', 'motivation_level']
#         widgets = {
#             'learning_style': forms.Select(choices=[
#                 ('visual', 'Visual'),
#                 ('auditory', 'Auditory'),
#                 ('kinesthetic', 'Kinesthetic'),
#                 ('reading_writing', 'Reading/Writing')
#             ]),
#             'goal': forms.TextInput(attrs={'placeholder': 'e.g., Pass exam, Master topic'}),
#             'hours_per_week': forms.NumberInput(attrs={'min': 1})
#         }

#     def clean_subjects(self):
#         subjects = self.cleaned_data['subjects']
#         return [s.strip() for s in subjects.split(',')]
    
class StudyPlanQuestionnaireForm(forms.ModelForm):
    subjects = forms.CharField(max_length=255, required=True, help_text="Enter subjects (e.g., Math, Science)")
    learning_style = forms.ChoiceField(
        choices=[
            ('visual', 'Visual'),
            ('auditory', 'Auditory'),
            ('kinesthetic', 'Kinesthetic'),
            ('reading_writing', 'Reading/Writing')
        ],
        required=True
    )
    goal = forms.CharField(max_length=100, required=True, help_text="Enter your academic goal")
    hours_per_week = forms.IntegerField(min_value=1, required=True, help_text="Hours available per week")
    hours_studied = forms.IntegerField(min_value=0, required=True, help_text="Hours studied per week")
    sleep_hours = forms.IntegerField(min_value=0, required=True, help_text="Average sleep hours per night")
    extracurricular = forms.IntegerField(min_value=0, required=True, help_text="Hours spent on extracurricular activities")
    question_papers_solved = forms.IntegerField(min_value=0, required=True, help_text="Number of question papers solved")
    study_habits = forms.CharField(max_length=255, required=True, help_text="Describe your study habits")
    previous_grades = forms.IntegerField(min_value=0, max_value=100, required=True, help_text="Previous grades (0-100)")
    motivation_level = forms.ChoiceField(
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High')
        ],
        required=True
    )

    class Meta:
        model = StudyPlanQuestionnaire
        fields = [
            'subjects',
            'learning_style',
            'goal',
            'hours_per_week',
            'hours_studied',
            'sleep_hours',
            'extracurricular',
            'question_papers_solved',
            'study_habits',
            'previous_grades',
            'motivation_level'
        ]
    
 