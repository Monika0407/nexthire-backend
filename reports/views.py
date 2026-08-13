# reports/views.py
"""
Placement Reports and CSV compiled audit exporters.
Provides views to generate compliance documents down to user levels.
"""

import csv
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from accounts.models import TraineeProfile
from applications.models import Application, Status

def is_staff_or_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

@login_required
@user_passes_test(is_staff_or_admin, login_url='accounts:login')
def export_placed_students_csv(req):
    """
    Renders dynamic CSV spreadsheet tracking placed trainees, Batch Code indices, CGPA, courses, CTC.
    """
    # Create the HttpResponse object with the appropriate CSV header
    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="nexthire_placed_export_2026.csv"'},
    )

    writer = csv.writer(response)
    # Write statutory header rows
    writer.writerow(['Student Batch Code', 'Full Name', 'Course Stream', 'CGPA Transcript', 'Hired Company', 'Hired Role Package', 'Status'])

    # Query placed candidates
    placed_applications = Application.objects.filter(status=Status.OFFER_ACCEPTED).select_related('trainee', 'trainee__user', 'job', 'job__recruiter')

    for app in placed_applications:
        trainee = app.trainee
        user = trainee.user
        job = app.job
        writer.writerow([
            trainee.batch_code,
            user.get_full_name() or user.username,
            trainee.get_course_display(),
            trainee.cgpa,
            job.recruiter.company_name,
            job.salary_package,
            app.get_status_display()
        ])

    return response
