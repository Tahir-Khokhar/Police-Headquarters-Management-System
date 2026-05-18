from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .models import (
    APPLICATION_PATH_SOLDIER,
    TRAINING_STATUS_COMPLETED,
    Application,
    Department,
    Personnel,
    Rank,
)


def home(request: HttpRequest) -> HttpResponse:
    """Home page showcasing all features of the Police Personnel Management System."""
    from .models import (
        Department,
        Station,
        Rank,
        Personnel,
        Application,
        TrainingAssignment,
        UpgradeRequest,
        DutyAssignment,
    )

    # System statistics
    stats = {
        'total_departments': Department.objects.count(),
        'total_stations': Station.objects.count(),
        'total_ranks': Rank.objects.count(),
        'total_personnel': Personnel.objects.count(),
        'total_applications': Application.objects.count(),
        'applications_pending': Application.objects.filter(status__in=['submitted', 'under_review']).count(),
        'trainings_active': TrainingAssignment.objects.filter(status__in=['planned', 'enrolled']).count(),
        'upgrade_requests_pending': UpgradeRequest.objects.filter(status__in=['submitted', 'waiting_department_service', 'recommended']).count(),
        'personnel_on_duty': Personnel.objects.filter(duty_assignments__isnull=False).distinct().count(),
    }

    return render(request, 'police/home.html', {'stats': stats})


def _is_admin_user(request: HttpRequest) -> bool:
    return request.user.groups.filter(name='Police Admin').exists()


def _ensure_role_groups(request: HttpRequest) -> None:
    # Ensure groups exist (avoid DB queries during AppConfig.ready())
    from .permissions import ensure_groups

    ensure_groups()



@login_required
def personnel_dashboard(request: HttpRequest) -> HttpResponse:
    is_admin = _is_admin_user(request)
    personnel = Personnel.objects.filter(user=request.user).first()

    if personnel is None:
        messages.warning(
            request,
            'Your personnel profile is not set up. Please complete your registration to access the dashboard.'
        )
        return redirect('register')

    # Applications: admin sees all, personnel sees only their own (by applicant_name).
    if is_admin:
        applications = Application.objects.all().order_by('-created_at')
    else:
        applications = Application.objects.filter(applicant_name=personnel.full_name).order_by('-created_at')

    # Global dashboard stats (based on training/duty/leave).
    # Duty: people who have an assigned DutyAssignment.
    # Training: TrainingAssignment with completed status.
    # Leave: no explicit Leave model in current codebase, so we show 0.
    if is_admin:
        duty_personnel_count = Personnel.objects.filter(duty_assignments__isnull=False).distinct().count()

        # Training is linked via Application -> TrainingAssignment (not directly on Personnel)
        training_personnel_count = Personnel.objects.filter(
            application__training_assignment__status=TRAINING_STATUS_COMPLETED
        ).distinct().count()

        leave_personnel_count = 0
    else:
        duty_personnel_count = personnel.duty_assignments.exists()

        training_personnel_count = Application.objects.filter(
            applicant_name=personnel.full_name,
            training_assignment__status=TRAINING_STATUS_COMPLETED,
        ).exists()

        leave_personnel_count = 0

    return render(
        request,
        'police/personnel_dashboard.html',
        {
            'personnel': personnel,
            'applications': applications,
            'is_admin': is_admin,
            'duty_personnel_count': duty_personnel_count,
            'training_personnel_count': training_personnel_count,
            'leave_personnel_count': leave_personnel_count,
        },
    )


@login_required
def application_list(request: HttpRequest) -> HttpResponse:
    personnel = Personnel.objects.filter(user=request.user).first()

    if personnel is None:
        messages.warning(
            request,
            'Your personnel profile is not set up. Please complete your registration to access applications.'
        )
        return redirect('register')

    if _is_admin_user(request):
        applications = Application.objects.all().order_by('-created_at')
    else:
        applications = Application.objects.filter(applicant_name=personnel.full_name).order_by('-created_at')

    return render(
        request,
        'police/application_list.html',
        {'applications': applications, 'personnel': personnel, 'is_admin': _is_admin_user(request)},
    )


def register(request: HttpRequest) -> HttpResponse:
    """Registration page for new personnel."""
    if request.user.is_authenticated:
        return redirect('personnel_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        full_name = request.POST.get('full_name', '').strip()
        gender = request.POST.get('gender', '')
        date_of_birth = request.POST.get('date_of_birth', None)
        department_id = request.POST.get('department', None)
        department_join_date = request.POST.get('department_join_date', None)
        rank_id = request.POST.get('rank', None)
        is_soldier_candidate = request.POST.get('is_soldier_candidate', 'False') == 'True'

        errors = []

        # Validation
        if not username:
            errors.append('Username is required.')
        if not password1:
            errors.append('Password is required.')
        if password1 != password2:
            errors.append('Passwords do not match.')
        if not full_name:
            errors.append('Full name is required.')
        if not gender:
            errors.append('Gender is required.')
        if not department_id:
            errors.append('Department is required.')
        if not department_join_date:
            errors.append('Department join date is required.')
        if not rank_id:
            errors.append('Rank is required.')

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            errors.append('This username is already taken.')

        # Get department and rank
        department = None
        rank = None
        if department_id:
            department = Department.objects.filter(id=department_id).first()
            if not department:
                errors.append('Invalid department selected.')
        if rank_id:
            rank = Rank.objects.filter(id=rank_id).first()
            if not rank:
                errors.append('Invalid rank selected.')

        if errors:
            # Store errors for display - we'll use a simple approach
            return render(request, 'registration/register.html', {
                'errors': errors,
                'form': type('Form', (), {'errors': True, 'username': type('Field', (), {'value': username})()})(),
                'departments': Department.objects.all().order_by('name'),
                'ranks': Rank.objects.all().order_by('sequence'),
            })

        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email if email else None,
                password=password1,
            )

            # Create personnel record
            Personnel.objects.create(
                user=user,
                full_name=full_name,
                gender=gender,
                date_of_birth=date_of_birth if date_of_birth else None,
                department=department,
                department_join_date=department_join_date,
                rank=rank,
                is_soldier_candidate=is_soldier_candidate,
            )

            # Log the user in
            login(request, user)

            messages.success(request, 'Account created successfully! Welcome to the Police Personnel Management System.')
            return redirect('personnel_dashboard')

        except IntegrityError:
            errors.append('An account with this information already exists.')
            return render(request, 'registration/register.html', {
                'errors': errors,
                'form': type('Form', (), {'errors': True})(),
                'departments': Department.objects.all().order_by('name'),
                'ranks': Rank.objects.all().order_by('sequence'),
            })

    # GET request - show registration form
    departments = Department.objects.all().order_by('name')
    ranks = Rank.objects.all().order_by('sequence')

    return render(request, 'registration/register.html', {
        'departments': departments,
        'ranks': ranks,
        'form': type('Form', (), {'errors': False})(),
    })
