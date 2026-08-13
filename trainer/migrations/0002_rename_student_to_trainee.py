from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('trainer', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='candidaterecommendation',
            old_name='student',
            new_name='trainee',
        ),
    ]
