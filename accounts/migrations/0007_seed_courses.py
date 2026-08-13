from django.db import migrations

def seed_courses(apps, schema_editor):
    Course = apps.get_model('accounts', 'Course')
    predefined_courses = [
        'Java Testing',
        'Python Testing',
        'Java Full Stack',
        'Python Full Stack',
        'Data Analysis',
        'Data Science',
        'DevOps'
    ]
    for course_name in predefined_courses:
        Course.objects.get_or_create(name=course_name)

def rollback_courses(apps, schema_editor):
    Course = apps.get_model('accounts', 'Course')
    predefined_courses = [
        'Java Testing',
        'Python Testing',
        'Java Full Stack',
        'Python Full Stack',
        'Data Analysis',
        'Data Science',
        'DevOps'
    ]
    Course.objects.filter(name__in=predefined_courses).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_course_placementofficerprofile_courses_handled_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_courses, rollback_courses),
    ]
