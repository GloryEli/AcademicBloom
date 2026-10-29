from django.http import Http404
import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Student, SubjectEntry, CourseSpecificEntry
from django.core.cache import cache
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import get_object_or_404
from .forms import StudyPlanQuestionnaireForm
from .models import StudyPlanQuestionnaire

from django.views.decorators.http import require_POST
from .forms import Step1Form, Step2Form, Step3Form, Step4Form, Step5Form
from formtools.wizard.views import SessionWizardView
from .forms import Step1Form, Step2Form, Step3Form, Step4Form, Step5Form
from .services import (
    generate_study_guidance,
    predict_course_score,
    predict_quiz_score,
    simulate_course_outcome,
)


def _subject_payload(subject):
    """Build a payload for the local prediction/guidance service from a model instance."""
    if subject is None:
        return {}

    preferred_style = subject.preferred_learning_style or ""
    if isinstance(preferred_style, str):
        preferred_style = preferred_style.strip()

    return {
        "subject": getattr(subject, "subject_name", ""),
        "hours_studied": getattr(subject, "hours_studied", 0),
        "previous_scores": getattr(subject, "previous_scores", 0),
        "extracurricular": getattr(subject, "extracurricular", "No"),
        "sleep_hours": getattr(subject, "sleep_hours", 0),
        "question_papers": getattr(subject, "question_papers", 0),
        "motivation": getattr(subject, "motivation", "Medium"),
        "preferred_learning_style": preferred_style,
        "goal": getattr(subject, "goal", ""),
    }


def home(request):
    return render(request, 'base.html')  

def sparkles_preview(request):
    return render(request, 'sparkles_preview.html')

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            # Log in the user
            user = form.get_user()
            login(request, user)
            messages.success(request, "Welcome back!")
            return redirect('hero')  
        else:
            messages.error(request, "Invalid username or password")
    else:
        form = AuthenticationForm()

    return render(request, 'registration/login.html', {'form': form})


def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Create a Student record for this user
            Student.objects.create(user=user)

            # Log the user in
            login(request, user)

            messages.success(request, "You have successfully signed up and are now logged in!")
            return redirect('hero')  # make sure this is defined in your urls/views
        else:
            messages.error(request, "There was an error with your signup. Please try again.")
    else:
        form = UserCreationForm()

    return render(request, 'registration/signup.html', {'form': form})

class SubjectWizard(SessionWizardView):
    form_list = [Step1Form, Step2Form, Step3Form, Step4Form, Step5Form]
    template_name = "multi_form.html"

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        
        # Only pass user, course, and mode to Step1Form
        if step == '0':  # First step (0-indexed)
            kwargs['user'] = self.request.user
            
            # Determine the mode based on session flags
            new_prediction_course_id = self.request.session.get('new_prediction_course_id')
            
            # Debug session state
            print(f"DEBUG get_form_kwargs - new_prediction_course_id: {new_prediction_course_id}")
            
            if new_prediction_course_id:
                # New prediction mode - create prediction for existing course
                try:
                    student = Student.objects.get(user_id=self.request.user.pk)
                    course = SubjectEntry.objects.get(
                        id=new_prediction_course_id, 
                        student=student
                    )
                    kwargs['course'] = course
                    kwargs['mode'] = 'new_prediction'
                    print(f"DEBUG: Mode set to 'new_prediction' for course {course.subject_name}")
                except (Student.DoesNotExist, SubjectEntry.DoesNotExist):
                    if 'new_prediction_course_id' in self.request.session:
                        del self.request.session['new_prediction_course_id']
                    kwargs['mode'] = 'not_editing'
                    print("DEBUG: Course not found, mode set to 'not_editing'")
            else:
                # Not editing mode - create new course
                kwargs['mode'] = 'not_editing'
                print("DEBUG: No session flags found, mode set to 'not_editing'")
                    
        return kwargs

    def get_form_initial(self, step):
        """Set initial data for forms when making new prediction"""
        initial = super().get_form_initial(step)
        
        # Check new prediction mode
        new_prediction_course_id = self.request.session.get('new_prediction_course_id')
        
        if new_prediction_course_id:
            try:
                student = Student.objects.get(user_id=self.request.user.pk)
                course = SubjectEntry.objects.get(
                    id=new_prediction_course_id, 
                    student=student
                )
                
                # Set initial data based on the step
                if step == '0':  # Step1Form
                    initial.update({
                        'subject_name': course.subject_name,
                        'previous_scores': course.previous_scores,
                    })
                elif step == '1':  # Step2Form
                    initial.update({
                        'hours_studied': course.hours_studied,
                    })
                elif step == '2':  # Step3Form
                    initial.update({
                        'extracurricular': course.extracurricular,
                    })
                elif step == '3':  # Step4Form
                    initial.update({
                        'sleep_hours': course.sleep_hours,
                    })
                elif step == '4':  # Step5Form
                    # Convert comma-separated learning styles back to list
                    learning_styles = []
                    if course.preferred_learning_style:
                        learning_styles = [style.strip() for style in course.preferred_learning_style.split(',')]
                    
                    initial.update({
                        'question_papers': course.question_papers,
                        'motivation': course.motivation,
                        'preferred_learning_style': learning_styles,
                    })
                    
            except (Student.DoesNotExist, SubjectEntry.DoesNotExist):
                # Course doesn't exist, clear from session
                if 'new_prediction_course_id' in self.request.session:
                    del self.request.session['new_prediction_course_id']
                    
        return initial

    def process_step(self, form):
        """
        Process each step and ensure validation passes before proceeding.
        This method is called for each step validation.
        """
        # Let the parent class handle the default processing
        step_data = super().process_step(form)
        
        # For Step 1, perform additional validation
        if self.steps.current == '0':
            if not form.is_valid():
                # If form is invalid, the wizard will automatically stay on current step
                # Add any additional logging or error handling here if needed
                pass
        
        return step_data

    def get_context_data(self, form, **kwargs):
        """
        Add additional context data to the template.
        """
        context = super().get_context_data(form=form, **kwargs)
        
        # Determine the mode
        new_prediction_course_id = self.request.session.get('new_prediction_course_id')
        
        print(f"DEBUG get_context_data - Full session: {dict(self.request.session)}")
        print(f"DEBUG get_context_data - new_prediction_course_id: {new_prediction_course_id}")
        
        # Add mode-specific context
        if new_prediction_course_id:
            context['wizard_title'] = 'New Prediction'
            context['wizard_subtitle'] = 'Create a new performance prediction for your course'
            print("DEBUG get_context_data: Set wizard_title to 'New Prediction'")
        else:
            context['wizard_title'] = 'Add New Course'
            context['wizard_subtitle'] = 'Add a new subject to track your performance'
            print("DEBUG get_context_data: Set wizard_title to 'Add New Course'")
        
        print(f"DEBUG get_context_data: Final wizard_title = '{context['wizard_title']}'")
        
        # Add step-specific context
        if self.steps.current == '0':
            if new_prediction_course_id:
                context['step_title'] = 'Course Information'
                context['step_description'] = 'Confirm the course and enter your latest scores'
            else:
                context['step_title'] = 'Subject Information'
                context['step_description'] = 'Enter the subject name and your previous scores'
        elif self.steps.current == '1':
            context['step_title'] = 'Study Hours'
            context['step_description'] = 'How many hours do you study per week?'
        elif self.steps.current == '2':
            context['step_title'] = 'Extracurricular Activities'
            context['step_description'] = 'Do you participate in extracurricular activities?'
        elif self.steps.current == '3':
            context['step_title'] = 'Sleep Pattern'
            context['step_description'] = 'How many hours do you sleep on average?'
        elif self.steps.current == '4':
            context['step_title'] = 'Study Preparation'
            context['step_description'] = 'Additional information about your study habits'
            
        return context


    def done(self, form_list, **kwargs):
        data = {}
        for form in form_list:
            data.update(form.cleaned_data)

        student = get_object_or_404(Student, user_id=self.request.user.pk)
        subject_name = data.get("subject_name", "Unnamed course")

        # Convert learning style list to comma-separated string
        learning_styles = data.get("preferred_learning_style", [])
        if isinstance(learning_styles, list):
            preferred_learning_style = ", ".join(learning_styles)
        else:
            preferred_learning_style = str(learning_styles) if learning_styles else "None"

        # Determine the mode and course ID
        new_prediction_course_id = self.request.session.get('new_prediction_course_id')
        
        if new_prediction_course_id:
            # NEW PREDICTION MODE: Update course data and create new prediction entry
            subject = get_object_or_404(SubjectEntry, id=new_prediction_course_id, student=student)
            
            # DON'T update the subject name in new_prediction mode!
            # The subject name should remain the same, only update other fields
            subject.hours_studied = data["hours_studied"]
            subject.previous_scores = data["previous_scores"]
            subject.extracurricular = data["extracurricular"]
            subject.sleep_hours = data["sleep_hours"]
            subject.question_papers = data["question_papers"]
            subject.motivation = data.get("motivation", "Medium")
            subject.preferred_learning_style = preferred_learning_style
            subject.save()
            
            # Create a new prediction entry for history tracking
            entry = CourseSpecificEntry.objects.create(
                subject=subject,
                hours_studied=data["hours_studied"],
                previous_scores=data["previous_scores"],
                extracurricular=data["extracurricular"],
                sleep_hours=data["sleep_hours"],
                question_papers=data["question_papers"],
                motivation=data.get("motivation", "Medium"),
                preferred_learning_style=preferred_learning_style,
            )
            
            # Clear the new prediction flag from session
            del self.request.session['new_prediction_course_id']
            redirect_id = subject.pk
            
        else:
            # NOT EDITING MODE: Creating a new course
            subject = SubjectEntry.objects.create(
                student=student,
                subject_name=subject_name,
                hours_studied=data["hours_studied"],
                previous_scores=data["previous_scores"],
                extracurricular=data["extracurricular"],
                sleep_hours=data["sleep_hours"],
                question_papers=data["question_papers"],
                motivation=data.get("motivation", "Medium"),
                preferred_learning_style=preferred_learning_style,
            )

            # Also create a prediction entry for consistency
            entry = CourseSpecificEntry.objects.create(
                subject=subject,
                hours_studied=data["hours_studied"],
                previous_scores=data["previous_scores"],
                extracurricular=data["extracurricular"],
                sleep_hours=data["sleep_hours"],
                question_papers=data["question_papers"],
                motivation=data.get("motivation", "Medium"),
                preferred_learning_style=preferred_learning_style,
            )
        
            redirect_id = subject.pk

        outcome = simulate_course_outcome({
            "subject": subject.subject_name,
            "hours_studied": data["hours_studied"],
            "previous_scores": data["previous_scores"],
            "extracurricular": data["extracurricular"],
            "sleep_hours": data["sleep_hours"],
            "question_papers": data["question_papers"],
            "motivation": data.get("motivation", "Medium"),
            "preferred_learning_style": preferred_learning_style,
            "goal": subject.subject_name,
        })
        predicted_score = outcome["predicted_score"]
        study_guide = outcome["study_guide"]
        entry.predicted_score = predicted_score
        entry.study_guide = study_guide
        entry.save()
        subject.predicted_score = predicted_score
        subject.study_guide = study_guide
        subject.save()
        messages.success(self.request, f"Prediction successful! Estimated score: {predicted_score}")


        # Redirect to the subject dashboard - THIS LINE WAS MISPLACED
        return redirect('subject_dashboard', course_id=redirect_id)
    
    def post(self, request, *args, **kwargs):
            print(f"Current Step: {self.steps.current}")  
            form = self.get_form()
            print("Form errors:", form.errors)
            
            # Debug: Check the mode being passed
            new_prediction_course_id = self.request.session.get('new_prediction_course_id')
            print(f"DEBUG - Session new_prediction_course_id: {new_prediction_course_id}")
            
            return super().post(request, *args, **kwargs)

def subject_dashboard(request, course_id):
    course = get_object_or_404(SubjectEntry, id=course_id)
    
    # Get the Student instance associated with the user
    try:
        student = request.user.student
    except Student.DoesNotExist:
        raise Http404("Student profile not found")
    
    return render(request, 'dashboard.html', {
        'course': course,
        'courses': SubjectEntry.objects.filter(student=student),
        'current_page': 'dashboard'
    })


@login_required
def subject_results_view(request, subject_id):
    subject_entry = get_object_or_404(SubjectEntry, id=subject_id, student=request.user.student)

    return render(request, 'subject_results.html', {
        'subject_entry': subject_entry,
    })


def multi_step_form(request):
    if request.method == 'POST':
        step = request.POST.get('step')

        if step == '1':
            form = Step1Form(request.POST or None, user=request.user)
            if form.is_valid():
                request.session['previous_scores'] = form.cleaned_data['previous_scores']
                return redirect('step2')
        
        elif step == '2':
            form = Step2Form(request.POST)
            if form.is_valid():
                request.session['hours_studied'] = form.cleaned_data['hours_studied']
                return redirect('step3')
        
        elif step == '3':
            form = Step3Form(request.POST)
            if form.is_valid():
                request.session['extracurricular'] = form.cleaned_data['extracurricular']
                return redirect('step4')
        
        elif step == '4':
            form = Step4Form(request.POST)
            if form.is_valid():
                request.session['sleep_hours'] = form.cleaned_data['sleep_hours']
                return redirect('step5')
        
        elif step == '5':
            form = Step5Form(request.POST)
            if form.is_valid():
                subject_entry = SubjectEntry(
                    student=request.user,
                    subject_name=request.session.get('subject_name', 'Subject 1'),  # Update as needed
                    previous_scores=request.session['previous_scores'],
                    hours_studied=request.session['hours_studied'],
                    extracurricular=request.session['extracurricular'],
                    sleep_hours=request.session['sleep_hours'],
                    question_papers=form.cleaned_data['question_papers'],
                    preferred_learning_style=form.cleaned_data['preferred_learning_style']
                )


                subject_entry.save()
                outcome = simulate_course_outcome({
                    "subject": subject_entry.subject_name,
                    "hours_studied": subject_entry.hours_studied,
                    "previous_scores": subject_entry.previous_scores,
                    "extracurricular": subject_entry.extracurricular,
                    "sleep_hours": subject_entry.sleep_hours,
                    "question_papers": subject_entry.question_papers,
                    "preferred_learning_style": subject_entry.preferred_learning_style,
                    "motivation": subject_entry.motivation,
                    "goal": subject_entry.subject_name,
                })
                subject_entry.predicted_score = outcome["predicted_score"]
                subject_entry.study_guide = outcome["study_guide"]
                subject_entry.save(update_fields=["predicted_score", "study_guide"])
                return redirect('success')  # Redirect to a success page

    else:
        # Determine which form to display based on the current step
        step = request.GET.get('step', '1')
        if step == '1':
            form = Step1Form()
        elif step == '2':
            form = Step2Form()
        elif step == '3':
            form = Step3Form()
        elif step == '4':
            form = Step4Form()
        elif step == '5':
            form = Step5Form()

    return render(request, 'multi_step_form.html', {'form': form, 'step': step})



@login_required
def hero_view(request):
    
    student = request.user.student
    latest_score = SubjectEntry.objects.filter(student=student).last()
    recent_feedback = "Try practicing 1 more paper this week!"
    courses = SubjectEntry.objects.filter(student__user=request.user)

    return render(request, 'hero.html', {
        'latest_score': latest_score,
        'recent_feedback': recent_feedback,
        'courses': courses,
        'current_page': 'hero'
    })


@login_required
def student_dashboard_view(request):
    return render(request, 'dashboard.html')   

@login_required
def get_guidance_view(request, course_id):
    course = get_object_or_404(SubjectEntry, id=course_id)

    if request.method == "POST":
        student = Student.objects.filter(user=request.user).first()
        if not student:
            return render(request, "dashboard.html", {
                "error": "Student profile not found.",
                "course": course,
            })

        if not course:
            return render(request, "dashboard.html", {
                "error": "Course not found.",
                "course": course,
            })

        payload = {
            "subject": course.subject_name,
            "previous_scores": course.previous_scores,
            "hours_studied": course.hours_studied,
            "sleep_hours": course.sleep_hours,
            "question_papers": course.question_papers,
            "motivation": course.motivation,
            "preferred_learning_style": course.preferred_learning_style,
            "extracurricular": course.extracurricular,
            "goal": course.subject_name,
        }
        outcome = simulate_course_outcome(payload)
        course.study_guide = outcome["study_guide"]
        course.predicted_score = outcome["predicted_score"]
        course.save(update_fields=["study_guide", "predicted_score", "updated_at"])

        return render(request, "dashboard.html", {
            "course": course,
            "guidance": course.study_guide,
            "courses": SubjectEntry.objects.filter(student=request.user.student),
        })

    return redirect("subject_dashboard", course_id=course.pk)



@require_POST
@login_required
def delete_course(request, course_id):
    course = get_object_or_404(SubjectEntry, id=course_id, student=request.user.student)
    course.delete()
    messages.success(request, f"Deleted course: {course.subject_name}")
    return redirect("hero")



@login_required
def questionnaire_view(request):
    if request.method == 'POST':
        form = StudyPlanQuestionnaireForm(request.POST)
        if form.is_valid():
            questionnaire = form.save(commit=False)
            questionnaire.user = request.user
            questionnaire.save()

            data = {
                'subject': form.cleaned_data['subjects'],
                'learning_style': form.cleaned_data['learning_style'],
                'goal': form.cleaned_data['goal'],
                'hours_per_week': form.cleaned_data['hours_per_week'],
                'hours_studied': form.cleaned_data['hours_studied'],
                'sleep_hours': form.cleaned_data['sleep_hours'],
                'extracurricular': form.cleaned_data['extracurricular'],
                'question_papers': form.cleaned_data['question_papers_solved'],
                'study_habits': form.cleaned_data['study_habits'],
                'previous_scores': form.cleaned_data['previous_grades'],
                'motivation': form.cleaned_data['motivation_level'],
                'preferred_learning_style': form.cleaned_data['learning_style'],
            }

            outcome = simulate_course_outcome(data)
            return render(request, 'dashboard.html', {
                'course': type('CourseStub', (), {
                    'subject_name': form.cleaned_data['subjects'],
                    'study_guide': outcome['study_guide'],
                    'predicted_score': outcome['predicted_score'],
                })(),
                'guidance': outcome['study_guide'],
                'courses': SubjectEntry.objects.filter(student=request.user.student),
            })
        return render(request, 'questionnaire.html', {'form': form})

    form = StudyPlanQuestionnaireForm()
    return render(request, 'questionnaire.html', {'form': form})

# @login_required We can use this if the form works without errors.
# def questionnaire_view(request):
#     latest_entry = SubjectEntry.objects.filter(student=request.user.student).last()
#     initial_data = {}
#     if latest_entry:
#         initial_data = {
#             'hours_studied': latest_entry.hours_studied,
#             'sleep_hours': latest_entry.sleep_hours,
#             'extracurricular': latest_entry.extracurricular,
#             'question_papers_solved': latest_entry.question_papers,
#             'previous_grades': latest_entry.previous_scores,
#             'motivation_level': latest_entry.motivation,
#             'learning_style': latest_entry.preferred_learning_style,
#         }
#     if request.method == 'POST':
#         form = StudyPlanQuestionnaireForm(request.POST)
#         if form.is_valid():
#             # ... existing logic ...
#         return render(request, 'performance/questionnaire.html', {'form': form})
#     else:
#         form = StudyPlanQuestionnaireForm(initial=initial_data)
#     return render(request, 'performance/questionnaire.html', {'form': form})
 


@login_required
def new_prediction(request, course_id):
    print(f"DEBUG new_prediction: Function called with course_id={course_id}")
    print(f"DEBUG new_prediction: Session before changes: {dict(request.session)}")
    
    # Store the course ID in session to indicate we're making a new prediction
    print(f"DEBUG new_prediction: Setting new_prediction_course_id to {course_id}")
    request.session['new_prediction_course_id'] = course_id
    
    # Force session save
    request.session.save()
    print(f"DEBUG new_prediction: Session after changes: {dict(request.session)}")
    
    print("DEBUG new_prediction: Redirecting to wizard")
    # Redirect to the wizard which will detect we're in new prediction mode
    return redirect('create_subject_entry')  


@login_required
def new_course(request):
    """Clear any session flags and start creating a new course"""
    print(f"DEBUG new_course: Function called")
    print(f"DEBUG new_course: Session before changes: {dict(request.session)}")
    
    # Clear any existing mode flags
    if 'new_prediction_course_id' in request.session:
        print("DEBUG new_course: Clearing new_prediction_course_id from session")
        del request.session['new_prediction_course_id']
    
    # Force session save
    request.session.save()


    print(f"DEBUG new_course: Session after changes: {dict(request.session)}")
    
    print("DEBUG new_course: Redirecting to wizard in not_editing mode")

    # Redirect to the wizard which will detect we're in not_editing mode
    return redirect('create_subject_entry')


@login_required
def course_history_dashboard(request, course_id):
    course = get_object_or_404(SubjectEntry, id=course_id, student=request.user.student)
    
    # Get all prediction entries for this course, ordered by most recent
    prediction_entries = CourseSpecificEntry.objects.filter(subject=course).order_by('-created_at')
    
    # Prepare data for charts with proper fallbacks
    dates = [entry.created_at.strftime('%Y-%m-%d') for entry in prediction_entries]
    scores = [float(entry.predicted_score) if entry.predicted_score else 0 for entry in prediction_entries]
    hours_studied = [float(entry.hours_studied) for entry in prediction_entries]
    
    # Convert to JSON strings for the template
    dates_json = json.dumps(dates)
    scores_json = json.dumps(scores)
    hours_json = json.dumps(hours_studied)

    return render(request, 'course_history_dashboard.html', {
        'course': course,
        'prediction_entries': prediction_entries,
        'dates': dates_json,
        'scores': scores_json,
        'hours_studied': hours_json,
        'courses': SubjectEntry.objects.filter(student=request.user.student),
        'current_page': 'history'
    })