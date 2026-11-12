from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from .models import Student, SubjectEntry, StudyPlan
from unittest.mock import patch
from .services import LLMOutcome, predict_course_score, simulate_course_outcome



@override_settings(
    STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage"
)

class CourseOutcomeServiceTests(TestCase):
    def setUp(self):
        self.profile = {
        "subject": "Mathematics",
        "hours_studied": 6,
        "previous_scores": 70,
        "extracurricular": "No",
        "sleep_hours": 8,
        "question_papers": 2,
        "motivation": "high",
        "preferred_learning_style": "visual",
        "goal": "Mathematics",
        }

    @patch("polls.services.predict_course_outcome_with_llm")
    def test_uses_llm_result_when_available(self, llm_call):
        llm_call.return_value = LLMOutcome(
        predicted_score=83.5,
        guidance=["Use spaced repetition."],
        )

        outcome = simulate_course_outcome(self.profile)

        self.assertEqual(outcome["predicted_score"], 83.5)
        self.assertIn("<li>Use spaced repetition.</li>", outcome["study_guide"])
        llm_call.assert_called_once_with(self.profile)

    @patch("polls.services.predict_course_outcome_with_llm")
    def test_uses_python_result_when_llm_fails(self, llm_call):
        llm_call.side_effect = RuntimeError("simulated API failure")

        with self.assertLogs("polls.services", level="ERROR"):
            outcome = simulate_course_outcome(self.profile)

        self.assertEqual(outcome["predicted_score"], predict_course_score(self.profile))
        self.assertIn("Continue your current routine", outcome["study_guide"])


@override_settings(
    STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage"
)

class SignupLoginFlowTests(TestCase):
    def test_signup_credentials_work_after_logging_out(self):
        credentials = {
            "username": "newstudent",
            "password1": "Very-Strong-Passphrase-742!",
            "password2": "Very-Strong-Passphrase-742!",
        }
        signup_response = self.client.post(reverse("signup"), credentials)

        self.assertRedirects(signup_response, reverse("hero"))
        user = User.objects.get(username=credentials["username"])
        self.assertTrue(user.check_password(credentials["password1"]))
        self.assertTrue(Student.objects.filter(user=user).exists())

        self.client.logout()
        login_response = self.client.post(
            reverse("login"),
            {
                "username": credentials["username"],
                "password": credentials["password1"],
            },
        )

        self.assertRedirects(login_response, reverse("hero"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)


@override_settings(
    STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage"
)
class StudyPlanFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="student", password="pass12345")
        self.student = Student.objects.create(user=self.user)
        self.course = SubjectEntry.objects.create(
            student=self.student,
            subject_name="Mathematics",
            hours_studied=6,
            previous_scores=72,
            sleep_hours=8,
            question_papers=2,
            motivation="high",
            preferred_learning_style="visual",
        )
        self.client.force_login(self.user)

    def test_create_study_plan_uses_course_profile_and_persists_schedule(self):
        response = self.client.post(
            reverse("create_study_plan"),
            {
                "course": self.course.pk,
                "study_days": ["Monday", "Thursday"],
                "session_minutes": 50,
            },
        )

        plan = StudyPlan.objects.get(course=self.course)
        self.assertRedirects(
            response,
            reverse("study_plan_detail", kwargs={"plan_id": plan.pk}),
        )
        self.assertEqual(plan.study_days, ["Monday", "Thursday"])
        self.assertEqual(plan.session_minutes, 50)
        self.assertEqual([session["day"] for session in plan.schedule], ["Monday", "Thursday"])
        self.assertIn("mind map", plan.schedule[0]["activity"])
        self.assertTrue(plan.recommendations)

    def test_study_plan_form_is_prefilled_and_detail_is_available(self):
        response = self.client.get(
            reverse("create_study_plan"),
            {"course": self.course.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mathematics")
        self.assertContains(response, 'value="Monday" id="id_study_days_0" checked')

        plan = StudyPlan.objects.create(
            course=self.course,
            study_days=["Monday"],
            schedule=[{
                "day": "Monday",
                "title": "Learn & connect",
                "activity": "Review algebra.",
                "duration": 40,
            }],
            recommendations=["Keep a steady routine."],
        )
        detail = self.client.get(
            reverse("study_plan_detail", kwargs={"plan_id": plan.pk})
        )

        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Your personal weekly plan")
        self.assertContains(detail, "Review algebra.")
        self.assertContains(detail, "Keep a steady routine.")

    def test_student_cannot_create_plan_for_another_students_course(self):
        another_user = User.objects.create_user(username="another", password="pass12345")
        another_student = Student.objects.create(user=another_user)
        another_course = SubjectEntry.objects.create(
            student=another_student,
            subject_name="Physics",
        )

        response = self.client.post(
            reverse("create_study_plan"),
            {
                "course": another_course.pk,
                "study_days": ["Tuesday"],
                "session_minutes": 25,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(StudyPlan.objects.filter(course=another_course).exists())
        self.assertContains(response, "Select a valid choice")

    def test_student_cannot_view_another_students_plan(self):
        another_user = User.objects.create_user(username="another", password="pass12345")
        another_student = Student.objects.create(user=another_user)
        another_course = SubjectEntry.objects.create(
            student=another_student,
            subject_name="Physics",
        )
        plan = StudyPlan.objects.create(course=another_course)

        response = self.client.get(
            reverse("study_plan_detail", kwargs={"plan_id": plan.pk})
        )

        self.assertEqual(response.status_code, 404)

    def test_create_plan_is_available_from_home_and_course_dashboard(self):
        home = self.client.get(reverse("hero"))
        dashboard = self.client.get(
            reverse("subject_dashboard", kwargs={"course_id": self.course.pk})
        )

        self.assertContains(home, "Create a study plan")
        self.assertContains(home, reverse("create_study_plan"))
        self.assertContains(dashboard, "Create study plan")
        self.assertContains(
            dashboard,
            f'{reverse("create_study_plan")}?course={self.course.pk}',
        )
