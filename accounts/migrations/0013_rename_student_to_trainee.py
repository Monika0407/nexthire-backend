from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_alter_studentprofile_experience_years'),
        ('trainees', '0001_initial'),
        ('trainer', '0001_initial'),
        ('applications', '0001_initial'),
        ('ml_engine', '0001_initial'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='StudentProfile',
            new_name='TraineeProfile',
        ),
        migrations.RenameModel(
            old_name='PlacementOfficerProfile',
            new_name='TrainerProfile',
        ),
    ]
