from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import (
    APPLICATION_PATH_SOLDIER,
    Department,
    GENDER_FEMALE,
    GENDER_MALE,
    IntermediateClearing,
    Personnel,
    Rank,
    Station,
    TrainingAssignment,
    Application,
)



class SoldierIntermediateClearingGateTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='p1', password='pass')

        self.department = Department.objects.create(name='DeptA')
        self.station = Station.objects.create(department=self.department, name='Station1', location='Loc1')
        self.rank1 = Rank.objects.create(sequence=1, title='Constable', rank_code='C1')

        join_date = date.today() - timedelta(days=365 * 2)
        self.personnel = Personnel.objects.create(
            user=self.user,
            full_name='John Doe',
            gender=GENDER_MALE,
            date_of_birth=date.today() - timedelta(days=365 * 30),
            department=self.department,
            department_join_date=join_date,
            rank=self.rank1,
            is_soldier_candidate=True,
        )

        self.application = Application.objects.create(
            applicant_name=self.personnel.full_name,
            applicant_gender=self.personnel.gender,
            applicant_date_of_birth=self.personnel.date_of_birth,
            department=self.department,
            application_path=APPLICATION_PATH_SOLDIER,
            status='submitted',
        )

    def test_training_enrollment_requires_clearing(self):
        ta = TrainingAssignment(
            application=self.application,
            department=self.department,
            training_start_date=date.today(),
            training_end_date=date.today() + timedelta(days=30),
            status='planned',
        )
        with self.assertRaises(ValidationError):
            ta.full_clean()

        # Now clear intermediate
        IntermediateClearing.objects.create(personnel=self.personnel, is_cleared=True, cleared_at=None)

        ta.full_clean()  # should not raise


class DutyAssignmentGateTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.decision_user = User.objects.create_user(username='officer', password='pass')
        self.person_user = User.objects.create_user(username='p2', password='pass')

        self.department = Department.objects.create(name='DeptB')
        self.station = Station.objects.create(department=self.department, name='Station2', location='Loc2')

        self.rank1 = Rank.objects.create(sequence=1, title='Constable2', rank_code='C2')
        self.rank2 = Rank.objects.create(sequence=2, title='Sergeant2', rank_code='S2')

        join_date = date.today() - timedelta(days=365 * 6)
        self.personnel = Personnel.objects.create(
            user=self.person_user,
            full_name='Alice Doe',
            gender=GENDER_FEMALE,
            date_of_birth=date.today() - timedelta(days=365 * 25),
            department=self.department,
            department_join_date=join_date,
            rank=self.rank1,
            is_soldier_candidate=False,
        )

        self.application = Application.objects.create(
            applicant_name=self.personnel.full_name,
            applicant_gender=self.personnel.gender,
            applicant_date_of_birth=self.personnel.date_of_birth,
            department=self.department,
            application_path=APPLICATION_PATH_SOLDIER,
            status='submitted',
        )

        # training completed
        self.training = TrainingAssignment.objects.create(
            application=self.application,
            department=self.department,
            training_start_date=date.today() - timedelta(days=10),
            training_end_date=date.today() - timedelta(days=1),
            status='completed',
            decision_made=True,
        )

        # approved upgrade decision
        req = self.personnel.upgrade_requests.create(
            target_rank=self.rank2,
            status='submitted',
            requires_5_years_service=True,
        )
        self.decision = req.decision.create(
            decided_by=self.decision_user,
            is_approved=True,
            final_rank=self.rank2,
            decision_notes='ok',
        )

    def test_duty_assignment_requires_completed_training(self):
        # Make a new application whose training is NOT completed
        app2 = Application.objects.create(
            applicant_name=self.personnel.full_name,
            applicant_gender=self.personnel.gender,
            applicant_date_of_birth=self.personnel.date_of_birth,
            department=self.department,
            application_path=APPLICATION_PATH_SOLDIER,
            status='submitted',
        )

        from .models import DutyAssignment

        duty = DutyAssignment(
            personnel=self.personnel,
            department=self.department,
            station=self.station,
        )
        # because Application.objects.get(...) picks the first match; safest is to validate using clean
        # We'll still expect success because training_completed is based on any completed assignment.
        # So instead: temporarily mark training as not completed by deleting it.
        self.training.delete()
        with self.assertRaises(ValidationError):
            duty.full_clean()

    def test_duty_assignment_requires_approved_upgrade_decision(self):
        from .models import DutyAssignment

        # delete approved decision
        self.decision.delete()
        duty = DutyAssignment(
            personnel=self.personnel,
            department=self.department,
            station=self.station,
        )
        with self.assertRaises(ValidationError):
            duty.full_clean()

    def test_duty_assignment_allowed_when_training_completed_and_decision_approved(self):
        from .models import DutyAssignment

        # ensure approved decision exists
        self.decision
        duty = DutyAssignment(
            personnel=self.personnel,
            department=self.department,
            station=self.station,
        )
        duty.full_clean()


