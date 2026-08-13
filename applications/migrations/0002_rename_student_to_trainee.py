from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='application',
            old_name='student',
            new_name='trainee',
        ),
        migrations.RenameField(
            model_name='offer',
            old_name='student',
            new_name='trainee',
        ),
    ]
