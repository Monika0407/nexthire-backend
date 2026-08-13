from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import TraineeProfile, RecruiterProfile, Course

User = get_user_model()

class StudentRegistrationForm(forms.ModelForm):
    name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Enter Full Name', 'class': 'form-control'}),
        label="Name"
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Enter Email Address', 'class': 'form-control'})
    )
    phone_number = forms.CharField(
        required=False,
        max_length=15,
        widget=forms.TextInput(attrs={'placeholder': 'Enter Mobile Number', 'class': 'form-control'}),
        label="Mobile Number"
    )
    degree = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'Enter Degree', 'class': 'form-control'}),
        label="Degree"
    )
    branch = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'Enter Branch', 'class': 'form-control'}),
        label="Branch"
    )
    batch_code = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'placeholder': 'Enter Batch Code', 'class': 'form-control'}),
        label="Batch Code",
        required=True
    )
    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-checkbox'}),
        required=False,
        label="Select Enrolled Courses"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter Password', 'class': 'form-control'}),
        label="Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password', 'class': 'form-control'}),
        label="Confirm Password"
    )

    class Meta:
        model = User
        fields = ['email', 'password']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match!")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.role = 'trainee'
        user.first_name = self.cleaned_data['name']
        user.phone_number = self.cleaned_data.get('phone_number', '')
        if commit:
            user.save()
            import uuid
            temp_usn = f"TEMP_{uuid.uuid4().hex[:8]}"
            trainee = TraineeProfile.objects.create(
                user=user,
                usn=temp_usn,
                degree=self.cleaned_data.get('degree', ''),
                branch=self.cleaned_data.get('branch', ''),
                batch_code=self.cleaned_data.get('batch_code', ''),
                phone_number=self.cleaned_data.get('phone_number', '')
            )
            selected_courses = self.cleaned_data.get('courses')
            if selected_courses:
                trainee.courses.set(selected_courses)
        return user


class RecruiterRegistrationForm(forms.ModelForm):
    company_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Enter Company Name', 'class': 'form-control'}),
        label="Company Name"
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Enter Email Address', 'class': 'form-control'})
    )
    phone_number = forms.CharField(
        required=False,
        max_length=15,
        widget=forms.TextInput(attrs={'placeholder': 'Enter Mobile Number', 'class': 'form-control'}),
        label="Mobile Number"
    )
    company_website = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'placeholder': 'https://example.com', 'class': 'form-control'}),
        label="Company Website Link"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter Password', 'class': 'form-control'}),
        label="Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password', 'class': 'form-control'}),
        label="Confirm Password"
    )

    class Meta:
        model = User
        fields = ['email', 'password']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email address already exists.")
        return email

    def clean_company_name(self):
        company_name = self.cleaned_data.get('company_name')
        if RecruiterProfile.objects.filter(company_name=company_name).exists():
            raise ValidationError("A company with this name is already registered.")
        return company_name

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match!")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.role = 'recruiter'
        user.phone_number = self.cleaned_data.get('phone_number', '')
        if commit:
            user.save()
            RecruiterProfile.objects.create(
                user=user,
                company_name=self.cleaned_data['company_name'],
                company_website=self.cleaned_data.get('company_website', ''),
                contact_email=user.email
            )
        return user


class PlacementRegistrationForm(forms.ModelForm):
    name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Enter Full Name', 'class': 'form-control'}),
        label="Name"
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Enter Email Address', 'class': 'form-control'})
    )
    phone_number = forms.CharField(
        required=False,
        max_length=15,
        widget=forms.TextInput(attrs={'placeholder': 'Enter Mobile Number', 'class': 'form-control'}),
        label="Mobile Number"
    )
    courses_handled = forms.ModelMultipleChoiceField(
        queryset=Course.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-checkbox'}),
        required=False,
        label="Select Handled Course Domains"
    )
    secret_key = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter Secret Registration Key', 'class': 'form-control'}),
        label="Secret Key"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter Password', 'class': 'form-control'}),
        label="Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password', 'class': 'form-control'}),
        label="Confirm Password"
    )

    class Meta:
        model = User
        fields = ['email', 'password']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email address already exists.")
        return email

    def clean_secret_key(self):
        secret_key = self.cleaned_data.get('secret_key')
        if secret_key != 'Qs94Js85Ps03':
            raise ValidationError("Invalid Secret Key! Trainer registration is restricted.")
        return secret_key

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match!")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.role = 'trainer'
        user.first_name = self.cleaned_data['name']
        user.phone_number = self.cleaned_data.get('phone_number', '')
        if commit:
            user.save()
            from .models import TrainerProfile
            trainer = TrainerProfile.objects.create(
                user=user,
                is_approved=False
            )
            selected_courses = self.cleaned_data.get('courses_handled')
            if selected_courses:
                trainer.courses_handled.set(selected_courses)
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Enter Email Address', 'class': 'form-control'}),
        label="Email Address"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter Password', 'class': 'form-control'}),
        label="Password"
    )
