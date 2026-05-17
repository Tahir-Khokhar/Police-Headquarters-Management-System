from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from .models import Application, Personnel


def _is_admin_user(request: HttpRequest) -> bool:
    return request.user.groups.filter(name='Police Admin').exists()


def _ensure_role_groups(request: HttpRequest) -> None:
    # Ensure groups exist (avoid DB queries during AppConfig.ready())
    from .permissions import ensure_groups

    ensure_groups()



@login_required
def personnel_dashboard(request: HttpRequest) -> HttpResponse:
    # Same page for both roles; admin sees all apps, personnel sees only their own.
    if _is_admin_user(request):
        personnel = get_object_or_404(Personnel, user=request.user)
        applications = Application.objects.all().order_by('-created_at')
    else:
        personnel = get_object_or_404(Personnel, user=request.user)
        applications = Application.objects.filter(applicant_name=personnel.full_name).order_by('-created_at')

    return render(
        request,
        'police/personnel_dashboard.html',
        {
            'personnel': personnel,
            'applications': applications,
            'is_admin': _is_admin_user(request),
        },
    )


@login_required
def application_list(request: HttpRequest) -> HttpResponse:
    if _is_admin_user(request):
        personnel = get_object_or_404(Personnel, user=request.user)
        applications = Application.objects.all().order_by('-created_at')
    else:
        personnel = get_object_or_404(Personnel, user=request.user)
        applications = Application.objects.filter(applicant_name=personnel.full_name).order_by('-created_at')

    return render(
        request,
        'police/application_list.html',
        {'applications': applications, 'personnel': personnel, 'is_admin': _is_admin_user(request)},
    )



