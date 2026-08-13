from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('trainees', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='resume',
            old_name='student',
            new_name='trainee',
        ),
    ]
