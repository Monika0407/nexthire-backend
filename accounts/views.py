from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from functools import wraps
from .forms import StudentRegistrationForm, RecruiterRegistrationForm, PlacementRegistrationForm, LoginForm
from .models import Role

def notify_admins_and_officers_of_registration(new_user, role_label):
    from accounts.models import CustomUser, Role
    from notifications.models import Notification
    from django.db import models

    # Notify admins (is_superuser=True or role='admin')
    admins = CustomUser.objects.filter(models.Q(is_superuser=True) | models.Q(role='admin')).exclude(id=new_user.id)
    for admin_user in admins:
        notif = Notification.objects.create(
            user=admin_user,
            title=f"New {role_label} Registration: {new_user.email}",
            message=f"A new {role_label.lower()} user has registered and is pending verification approval: {new_user.get_full_name() or new_user.email}. Please review details to verify account access.",
            notification_type=Notification.Type.ADMIN_BROADCAST
        )
        notif.dispatch_email()

    # Notify placement trainers
    trainers = CustomUser.objects.filter(role=Role.TRAINER).exclude(id=new_user.id)
    for trainer_user in trainers:
        notif = Notification.objects.create(
            user=trainer_user,
            title=f"New {role_label} Registration: {new_user.email}",
            message=f"A new {role_label.lower()} user has registered and is pending verification approval: {new_user.get_full_name() or new_user.email}. Please review details to verify account access.",
            notification_type=Notification.Type.ADMIN_BROADCAST
        )
        notif.dispatch_email()

def student_register_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:role_routing')
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            notify_admins_and_officers_of_registration(user, "Student")
            login(request, user)
            return redirect('accounts:role_routing')
    else:
        form = StudentRegistrationForm()
    return render(request, 'accounts/register_student.html', {'form': form})

def recruiter_register_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:role_routing')
    if request.method == 'POST':
        form = RecruiterRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            notify_admins_and_officers_of_registration(user, "Recruiter")
            login(request, user)
            return redirect('accounts:role_routing')
    else:
        form = RecruiterRegistrationForm()
    return render(request, 'accounts/register_recruiter.html', {'form': form})

def ensure_admin_user():
    from .models import CustomUser
    from django.contrib.auth.hashers import make_password
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
        if not admin_user.is_superuser or not admin_user.is_staff or admin_user.role != 'admin':
            admin_user.is_superuser = True
            admin_user.is_staff = True
            admin_user.role = 'admin'
            admin_user.password = make_password(password)
            admin_user.save()

def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:role_routing')
    next_url = request.GET.get('next', '')
    if 'recruiter' in next_url:
        return redirect(f'/accounts/login/recruiter/?next={next_url}')
    elif 'placement' in next_url:
        return redirect(f'/accounts/login/placement/?next={next_url}')
    elif 'admin' in next_url:
        return redirect(f'/accounts/login/admin/?next={next_url}')
    else:
        return redirect(f'/accounts/login/trainee/?next={next_url}')

def student_login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:role_routing')
    error_message = None
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            user = authenticate(request, email=email, password=password)
            if user is not None:
                if user.role == 'trainee':
                    login(request, user)
                    next_url = request.GET.get('next')
                    if next_url:
                        return redirect(next_url)
                    return redirect('accounts:role_routing')
                else:
                    error_message = "Invalid trainee credentials. This login portal is for trainees only."
            else:
                error_message = "Invalid email or password."
    else:
        form = LoginForm()
    return render(request, 'accounts/login_student.html', {'form': form, 'error_message': error_message, 'active_role': 'trainee'})

def recruiter_login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:role_routing')
    error_message = None
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            user = authenticate(request, email=email, password=password)
            if user is not None:
                if user.role == 'recruiter':
                    login(request, user)
                    next_url = request.GET.get('next')
                    if next_url:
                        return redirect(next_url)
                    return redirect('accounts:role_routing')
                else:
                    error_message = "Invalid recruiter credentials. This login portal is for recruiters only."
            else:
                error_message = "Invalid email or password."
    else:
        form = LoginForm()
    return render(request, 'accounts/login_recruiter.html', {'form': form, 'error_message': error_message, 'active_role': 'recruiter'})

def admin_login_view(request):
    ensure_admin_user()
    if request.user.is_authenticated:
        return redirect('accounts:role_routing')
    error_message = None
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            user = authenticate(request, email=email, password=password)
            if user is not None:
                if user.is_superuser or user.role == 'admin':
                    login(request, user)
                    next_url = request.GET.get('next')
                    if next_url:
                        return redirect(next_url)
                    return redirect('/admin/dashboard/')
                else:
                    error_message = "Invalid admin credentials. Access Denied."
            else:
                error_message = "Invalid email or password."
    else:
        form = LoginForm()
    return render(request, 'accounts/login_admin.html', {'form': form, 'error_message': error_message, 'active_role': 'admin'})

def placement_login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:role_routing')
    error_message = None
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            user = authenticate(request, email=email, password=password)
            if user is not None:
                if user.role == Role.TRAINER:
                    login(request, user)
                    next_url = request.GET.get('next')
                    if next_url:
                        return redirect(next_url)
                    return redirect('accounts:role_routing')
                else:
                    error_message = "Invalid placement trainer credentials. This login portal is for placement trainers only."
            else:
                error_message = "Invalid email or password."
    else:
        form = LoginForm()
    return render(request, 'accounts/login_placement.html', {'form': form, 'error_message': error_message, 'active_role': 'placement'})

def logout_view(request):
    logout(request)
    return redirect('accounts:login')

def placement_register_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:role_routing')
    if request.method == 'POST':
        form = PlacementRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            notify_admins_and_officers_of_registration(user, "Trainer")
            login(request, user)
            return redirect('accounts:role_routing')
    else:
        form = PlacementRegistrationForm()
    return render(request, 'accounts/register_placement.html', {'form': form})

def awaiting_approval_view(request):
    return render(request, 'accounts/awaiting_approval.html')

@login_required
def role_routing_view(request):
    from .models import TrainerProfile, RecruiterProfile, TraineeProfile
    user = request.user
    if user.is_superuser or user.role == 'admin':
        return redirect('admin_custom:dashboard')
    elif user.role == Role.TRAINER:
        profile, _ = TrainerProfile.objects.get_or_create(user=user)
        if not profile.is_approved:
            return redirect('accounts:awaiting_approval')
        return redirect('trainer:dashboard')
    elif user.role == 'recruiter':
        try:
            profile = user.recruiter_profile
            if not profile.is_approved_by_admin:
                return redirect('accounts:awaiting_approval')
        except RecruiterProfile.DoesNotExist:
            return redirect('accounts:awaiting_approval')
        return redirect('recruiters:dashboard')
    else:
        try:
            profile = user.trainee_profile
            if profile.approval_status != 'approved':
                return redirect('accounts:awaiting_approval')
        except TraineeProfile.DoesNotExist:
            return redirect('accounts:awaiting_approval')
        return redirect('trainees:dashboard')

# Custom role authorization decorator for function-based views
def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if request.user.role in allowed_roles or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied("You do not have access to view this resource.")
        return _wrapped_view
    return decorator
