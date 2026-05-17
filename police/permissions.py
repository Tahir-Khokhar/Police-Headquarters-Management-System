from django.contrib.auth.models import Group


REQUIRED_GROUPS = {
    'POLICE_ADMIN': 'Police Admin',
    'POLICE_PERSONNEL': 'Police Personnel',
}


def ensure_groups():
    """Create groups if they don't exist. Safe to call at startup/management commands."""
    for _, name in REQUIRED_GROUPS.items():
        Group.objects.get_or_create(name=name)

