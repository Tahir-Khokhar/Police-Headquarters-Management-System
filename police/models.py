from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Department(models.Model):
    name = models.CharField(max_length=200, unique=True)

    def __str__(self) -> str:
        return self.name


class Station(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='stations')
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = (('department', 'name'),)

    def __str__(self) -> str:
        return f"{self.department.name} - {self.name}"


class Rank(models.Model):
    # sequence/order lets us compare rank progression
    sequence = models.PositiveIntegerField(unique=True)
    title = models.CharField(max_length=200, unique=True)
    rank_code = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ['sequence']

    def __str__(self) -> str:
        return self.title


GENDER_MALE = 'M'
GENDER_FEMALE = 'F'
GENDER_CHOICES = (
    (GENDER_MALE, 'Male'),
    (GENDER_FEMALE, 'Female'),
)


class Personnel(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='personnel_profile')

    full_name = models.CharField(max_length=200)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField(null=True, blank=True)

    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='personnel')
    department_join_date = models.DateField()

    rank = models.ForeignKey(Rank, on_delete=models.PROTECT, related_name='current_rank_personnel')

    is_soldier_candidate = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['full_name']

    def __str__(self) -> str:
        return self.full_name

    @property
    def years_of_service(self) -> float:
        # approx; good enough for validation gating. More accurate can be done with relativedelta.
        days = (timezone.now().date() - self.department_join_date).days
        return days / 365.25

    def clean(self):
        if self.department_join_date > timezone.now().date():
            raise ValidationError({'department_join_date': 'Join date cannot be in the future.'})


class PersonnelRankHistory(models.Model):
    personnel = models.ForeignKey(Personnel, on_delete=models.CASCADE, related_name='rank_history')
    rank = models.ForeignKey(Rank, on_delete=models.PROTECT, related_name='rank_history')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name='rank_history_end_after_start',
                condition=(models.Q(end_date__gte=models.F('start_date')) | models.Q(end_date__isnull=True)),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.personnel.full_name} -> {self.rank.title}"



class IntermediateClearing(models.Model):
    personnel = models.ForeignKey(Personnel, on_delete=models.CASCADE, related_name='intermediate_clearings')
    is_cleared = models.BooleanField(default=False)
    cleared_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"IntermediateClearing({self.personnel.full_name}, cleared={self.is_cleared})"


APPLICATION_PATH_FIGHTER = 'FIGHTER'
APPLICATION_PATH_SOLDIER = 'SOLDIER'
APPLICATION_PATH_CHOICES = (
    (APPLICATION_PATH_FIGHTER, 'Fighter'),
    (APPLICATION_PATH_SOLDIER, 'Soldier'),
)


class Application(models.Model):
    applicant_name = models.CharField(max_length=200)
    applicant_gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    applicant_date_of_birth = models.DateField(null=True, blank=True)

    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='applications')
    application_path = models.CharField(max_length=20, choices=APPLICATION_PATH_CHOICES)

    status = models.CharField(
        max_length=30,
        default='submitted',
        choices=(
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('under_review', 'Under Review'),
            ('intermediate_cleared', 'Intermediate Cleared'),
            ('enrolled_training', 'Enrolled Training'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Application({self.applicant_name}, {self.application_path})"


TRAINING_STATUS_PLANNED = 'planned'
TRAINING_STATUS_ENROLLED = 'enrolled'
TRAINING_STATUS_COMPLETED = 'completed'
TRAINING_STATUS_REJECTED = 'rejected'

TRAINING_STATUS_CHOICES = (
    (TRAINING_STATUS_PLANNED, 'Planned'),
    (TRAINING_STATUS_ENROLLED, 'Enrolled'),
    (TRAINING_STATUS_COMPLETED, 'Completed'),
    (TRAINING_STATUS_REJECTED, 'Rejected'),
)


class TrainingAssignment(models.Model):
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='training_assignment')
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='training_assignments')

    training_start_date = models.DateField()
    training_end_date = models.DateField()

    status = models.CharField(max_length=20, choices=TRAINING_STATUS_CHOICES, default=TRAINING_STATUS_PLANNED)

    # Decision after training to assign area/station
    decision_made = models.BooleanField(default=False)

    def clean(self):
        if self.training_end_date < self.training_start_date:
            raise ValidationError({'training_end_date': 'End date must be on/after start date.'})

        # Soldier gate: if application path is SOLDIER, an intermediate clearing must be completed.
        # NOTE: This assumes applicant_name maps to a Personnel.full_name.
        if self.application.application_path == APPLICATION_PATH_SOLDIER:
            personnel = Personnel.objects.filter(department=self.department, full_name=self.application.applicant_name).first()
            if not personnel:
                raise ValidationError({'application': 'No matching personnel found for soldier intermediate clearing gate.'})

            if not personnel.intermediate_clearings.filter(is_cleared=True).exists():
                raise ValidationError({'application': 'Soldier training requires intermediate clearing to be completed.'})

    def __str__(self) -> str:
        return f"TrainingAssignment({self.application_id}, {self.status})"



UPGRADE_STATUS_SUBMITTED = 'submitted'
UPGRADE_STATUS_WAITING_SERVICE = 'waiting_department_service'
UPGRADE_STATUS_RECOMMENDED = 'recommended'
UPGRADE_STATUS_APPROVED = 'approved'
UPGRADE_STATUS_REJECTED = 'rejected'

UPGRADE_STATUS_CHOICES = (
    (UPGRADE_STATUS_SUBMITTED, 'Submitted'),
    (UPGRADE_STATUS_WAITING_SERVICE, 'Waiting 5+ years service'),
    (UPGRADE_STATUS_RECOMMENDED, 'Recommended'),
    (UPGRADE_STATUS_APPROVED, 'Approved'),
    (UPGRADE_STATUS_REJECTED, 'Rejected'),
)


class UpgradeRequest(models.Model):
    personnel = models.ForeignKey(Personnel, on_delete=models.CASCADE, related_name='upgrade_requests')
    target_rank = models.ForeignKey(Rank, on_delete=models.PROTECT, related_name='upgrade_requests')

    status = models.CharField(max_length=40, choices=UPGRADE_STATUS_CHOICES, default=UPGRADE_STATUS_SUBMITTED)
    submitted_at = models.DateTimeField(auto_now_add=True)

    # department service requirement
    requires_5_years_service = models.BooleanField(default=True)

    notes = models.TextField(blank=True)

    def clean(self):
        if self.requires_5_years_service and self.personnel.years_of_service < 5:
            raise ValidationError({'personnel': 'Upgrade requires at least 5 years of service in the department.'})

    def __str__(self) -> str:
        return f"UpgradeRequest({self.personnel.full_name} -> {self.target_rank.title})"


class UpgradeDecision(models.Model):
    upgrade_request = models.OneToOneField(UpgradeRequest, on_delete=models.CASCADE, related_name='decision')
    decided_at = models.DateTimeField(auto_now_add=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='upgrade_decisions')

    is_approved = models.BooleanField(default=False)
    final_rank = models.ForeignKey(Rank, on_delete=models.PROTECT, related_name='final_ranks')

    decision_notes = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"UpgradeDecision({self.upgrade_request_id}, approved={self.is_approved})"


class DutyAssignment(models.Model):
    personnel = models.ForeignKey(Personnel, on_delete=models.CASCADE, related_name='duty_assignments')
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='duty_assignments')
    station = models.ForeignKey(Station, on_delete=models.PROTECT, related_name='duty_assignments')

    start_date = models.DateField(default=timezone.now)

    duty_status = models.CharField(max_length=30, default='assigned')

    assigned_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # Duty assignment is allowed only after:
        # - Training is completed for the personnel
        # - The personnel has an approved upgrade decision
        # This enforces the “after the completion of training department will decide …” rule.
        try:
            application = Application.objects.get(applicant_name=self.personnel.full_name, department=self.department)
        except Application.DoesNotExist:
            application = None

        training_completed = False
        if application:
            training_completed = TrainingAssignment.objects.filter(
                application=application,
                status=TRAINING_STATUS_COMPLETED,
            ).exists()

        has_approved_decision = UpgradeDecision.objects.filter(
            upgrade_request__personnel=self.personnel,
            is_approved=True,
        ).exists()

        if not training_completed:
            raise ValidationError({'personnel': 'Duty assignment requires completed training.'})

        if not has_approved_decision:
            raise ValidationError({'personnel': 'Duty assignment requires an approved upgrade decision.'})

    def __str__(self) -> str:
        return f"DutyAssignment({self.personnel.full_name} @ {self.station})"


