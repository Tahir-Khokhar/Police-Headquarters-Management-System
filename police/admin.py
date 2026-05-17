from django.contrib import admin

from .models import (
    Application,
    Department,
    DutyAssignment,
    IntermediateClearing,
    Personnel,
    PersonnelRankHistory,
    Rank,
    Station,
    TrainingAssignment,
    UpgradeDecision,
    UpgradeRequest,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    search_fields = ['name']


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ['name', 'department', 'location']
    list_filter = ['department']
    search_fields = ['name', 'location']


@admin.register(Rank)
class RankAdmin(admin.ModelAdmin):
    list_display = ['sequence', 'title', 'rank_code']
    ordering = ['sequence']


@admin.register(Personnel)
class PersonnelAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'gender', 'department', 'department_join_date', 'rank', 'is_soldier_candidate']
    list_filter = ['department', 'gender', 'rank']
    search_fields = ['full_name']


@admin.register(PersonnelRankHistory)
class PersonnelRankHistoryAdmin(admin.ModelAdmin):
    list_display = ['personnel', 'rank', 'start_date', 'end_date']
    list_filter = ['rank']


@admin.register(IntermediateClearing)
class IntermediateClearingAdmin(admin.ModelAdmin):
    list_display = ['personnel', 'is_cleared', 'cleared_at']
    list_filter = ['is_cleared']


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['applicant_name', 'application_path', 'department', 'status', 'created_at']
    list_filter = ['status', 'department', 'application_path']
    search_fields = ['applicant_name']


@admin.register(TrainingAssignment)
class TrainingAssignmentAdmin(admin.ModelAdmin):
    list_display = ['application', 'department', 'training_start_date', 'training_end_date', 'status', 'decision_made']
    list_filter = ['status', 'department']


@admin.register(UpgradeRequest)
class UpgradeRequestAdmin(admin.ModelAdmin):
    list_display = ['personnel', 'target_rank', 'status', 'requires_5_years_service', 'submitted_at']
    list_filter = ['status', 'target_rank', 'requires_5_years_service']
    search_fields = ['personnel__full_name']


@admin.register(UpgradeDecision)
class UpgradeDecisionAdmin(admin.ModelAdmin):
    list_display = ['upgrade_request', 'is_approved', 'final_rank', 'decided_at']
    list_filter = ['is_approved', 'final_rank']


@admin.register(DutyAssignment)
class DutyAssignmentAdmin(admin.ModelAdmin):
    list_display = ['personnel', 'department', 'station', 'start_date', 'duty_status', 'assigned_at']
    list_filter = ['department', 'station', 'duty_status']
    search_fields = ['personnel__full_name', 'station__name']

