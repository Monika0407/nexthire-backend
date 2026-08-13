from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('ml_engine', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='candidateplacementprediction',
            old_name='student',
            new_name='trainee',
        ),
        migrations.RenameField(
            model_name='jobrecommendationcache',
            old_name='student',
            new_name='trainee',
        ),
    ]
