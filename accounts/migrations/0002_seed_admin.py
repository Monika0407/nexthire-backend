from django.db import migrations
from django.contrib.auth.hashers import make_password

def seed_admin(apps, schema_editor):
    CustomUser = apps.get_model('accounts', 'CustomUser')
    email = 'qspidershebbal469@gmail.com'
    password = '#Qs03@J54$Py81'
    
    admin_user, created = CustomUser.objects.get_or_create(
        email=email,
        defaults={
            'is_superuser': True,
            'is_staff': True,
            'role': 'admin',
            'password': make_password(password),
            'is_active': True,
        }
    )
    if not created:
        admin_user.is_superuser = True
        admin_user.is_staff = True
        admin_user.role = 'admin'
        admin_user.password = make_password(password)
        admin_user.save()

def rollback_admin(apps, schema_editor):
    CustomUser = apps.get_model('accounts', 'CustomUser')
    CustomUser.objects.filter(email='qspidershebbal469@gmail.com').delete()

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_admin, rollback_admin),
    ]
