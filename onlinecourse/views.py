from django.http import HttpResponseRedirect
from .models import Course, Enrollment, Submission, Choice
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']

        # 2023 JCA - Prevent script insertion.
        if "<script>" in username.lower() or "<script>" in password.lower():
            # Script in the input; prevent continue.
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)

        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']

        # 2023 JCA - Prevent script insertion.
        if "<script>" in username.lower() or "<script>" in password.lower():
            # Script in the input; prevent continue.
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)

        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'

    # JCA - Included to get the details of enrolled users
    def get_context_data(self, **kwargs):
        """Get details of who is enrolled in course."""
        context = super().get_context_data(**kwargs)
        # Get users enrolled
        users = User.objects.filter(course=context['course'])
        # Get first_name and last_name
        users_enrolled = []
        for user in users:
            users_enrolled.append(user.first_name)
            users_enrolled.append(user.last_name)
        context['data'] = users_enrolled
        return context


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


def submit_request(request, course_id):
    """Submit exam to a course."""
    # Gather enrollment based on user and course
    course = get_object_or_404(Course, pk=course_id)
    user = request.user
    enrollmment_data = Enrollment.objects.get(user=user, course=course)

    # Create submission object
    new_submission = Submission(enrollment=enrollmment_data)
    new_submission.save()

    # Gather the answers in the form
    answers_by_user = []
    for items in request.POST:
        if items.startswith('choice'):
            new_choice = Choice.objects.get(pk=int(request.POST[items]))
            answers_by_user.append(new_choice)

    # Add the choices to the submission
    for current_choice in answers_by_user:
        new_submission.choices.add(current_choice)  # Object of Choice

    # Return to a proper view
    return HttpResponseRedirect(reverse(viewname='onlinecourse:exam_result', args=(course.id, new_submission.id)))


def exam_result_view(request, course_id, submission_id):
    """Create the exam result view."""
    # Gather the course and the submission:
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(Submission, pk=submission_id)

    # Security to prevent user seeing results from other users.
    user_submission = submission.enrollment
    if user_submission.user != request.user:
        return HttpResponseRedirect(reverse(viewname='onlinecourse:index'))

    total_grade: int = 0

    # Get all choices IDs:
    selected_choices: list = []
    for choice in submission.choices.all():
        selected_choices.append(choice.id)

    # Iterate through the exam questions to see how many are correct
    max_points_available: int = 0  # Used to store the maximum mark
    points_achieved: int = 0  # Max points achieved
    for question in course.question_set.all():
        max_points_available += question.question_value
        if question.get_question_score(selected_choices):
            points_achieved += question.question_value

    total_grade = int((points_achieved / max_points_available) * 100)

    context = {
        'course': course,
        'selections': selected_choices,
        'grade': total_grade,
    }
    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)
