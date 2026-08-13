# trainees/forms.py
"""
Django forms for Student Profile configuration and Resume validation.
Enforces file format validations (PDF, DOCX) and parses data lists.
"""

from django import forms
from django.contrib.auth.models import User
from .models import TraineeProfile
from accounts.models import Course
import os

class StudentProfileForm(forms.ModelForm):
    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'Enter Full Name'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'email@example.com'})
    )
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100'})
    )
    gender = forms.ChoiceField(
        choices=[('', 'Select Gender'), ('Male', 'Male'), ('Female', 'Female'), ('Others', 'Others')],
        required=False,
        widget=forms.Select(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100'})
    )
    city = forms.CharField(
        required=False,
        widget=forms.Select(attrs={'id': 'id_city', 'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100'})
    )
    state = forms.CharField(
        required=False,
        widget=forms.Select(attrs={'id': 'id_state', 'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100'})
    )
    country = forms.CharField(
        required=False,
        widget=forms.Select(attrs={'id': 'id_country', 'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100'})
    )
    linkedin_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'https://linkedin.com/in/username'})
    )
    github_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'https://github.com/username'})
    )
    portfolio_website = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'https://myportfolio.com'})
    )
    batch_start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100'})
    )
    batch_end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100'})
    )
    tenth_school = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'School Name'})
    )
    tenth_board = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'Board'})
    )
    tenth_percentage = forms.DecimalField(
        required=False,
        max_digits=5,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'Percentage'})
    )
    tenth_year = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'Year'})
    )
    twelfth_college = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'College/Diploma Name'})
    )
    twelfth_board = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'Board'})
    )
    twelfth_percentage = forms.DecimalField(
        required=False,
        max_digits=5,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'Percentage'})
    )
    twelfth_year = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'Year'})
    )
    graduation_college = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'Graduation College Name'})
    )
    graduation_university = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'University'})
    )
    graduation_year = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'Year'})
    )
    has_post_graduation = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'rounded border-slate-800 bg-slate-950 text-indigo-650 focus:ring-0 focus:ring-offset-0'})
    )
    pg_college = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'PG College Name'})
    )
    pg_university = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'PG University'})
    )
    pg_degree = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'PG Degree'})
    )
    pg_branch = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'PG Branch'})
    )
    pg_cgpa = forms.DecimalField(
        required=False,
        max_digits=4,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'PG CGPA'})
    )
    pg_year = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'PG Year'})
    )
    raw_skills = forms.CharField(
        required=False,
        label="Technical Skills",
        help_text="Submit relevant technical tags separated by commas",
        widget=forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'Python, Django, React, AWS'})
    )
    experience_years = forms.IntegerField(
        required=False,
        min_value=0,
        label="Years of Experience",
        widget=forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'e.g. 1'})
    )
    class Meta:
        model = TraineeProfile
        fields = [
            'phone_number', 'address', 'profile_image', 'date_of_birth',
            'degree', 'branch', 'cgpa', 'experience_years',
            'gender', 'city', 'state', 'country', 'linkedin_url', 'github_url', 'portfolio_website',
            'tenth_school', 'tenth_board', 'tenth_percentage', 'tenth_year',
            'twelfth_college', 'twelfth_board', 'twelfth_percentage', 'twelfth_year',
            'graduation_college', 'graduation_university', 'graduation_year',
            'has_post_graduation', 'pg_college', 'pg_university', 'pg_degree', 'pg_branch', 'pg_cgpa', 'pg_year'
        ]
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': '+91 9876543210'}),
            'address': forms.Textarea(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100 h-24', 'placeholder': 'Residential/Mailing address details'}),
            'degree': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'e.g. B.Tech'}),
            'branch': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'Computer Science & Engineering'}),
            'cgpa': forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'step': '0.01', 'placeholder': '9.50'}),
            'profile_image': forms.ClearableFileInput(attrs={'class': 'w-full text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-700 cursor-pointer'})
        }

    def __init__(self, *args, **kwargs):
        super(StudentProfileForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['full_name'].initial = f"{self.instance.user.first_name} {self.instance.user.last_name}".strip() or self.instance.user.email.split('@')[0]
            self.fields['email'].initial = self.instance.user.email
            self.fields['raw_skills'].initial = ", ".join(self.instance.skills) if isinstance(self.instance.skills, list) else ""
        
        if self.instance:
            if self.instance.date_of_birth:
                self.fields['date_of_birth'].initial = self.instance.date_of_birth
            if self.instance.gender:
                self.fields['gender'].initial = self.instance.gender
            if self.instance.city:
                self.fields['city'].initial = self.instance.city
            if self.instance.state:
                self.fields['state'].initial = self.instance.state
            if self.instance.country:
                self.fields['country'].initial = self.instance.country
            if self.instance.linkedin_url:
                self.fields['linkedin_url'].initial = self.instance.linkedin_url
            if self.instance.github_url:
                self.fields['github_url'].initial = self.instance.github_url
            if self.instance.portfolio_website:
                self.fields['portfolio_website'].initial = self.instance.portfolio_website
            if self.instance.phone_number:
                self.fields['phone_number'].initial = self.instance.phone_number
            if self.instance.address:
                self.fields['address'].initial = self.instance.address

    def clean_profile_image(self):
        image = self.cleaned_data.get('profile_image')
        if image is False:
            return None
        if not image:
            return self.instance.profile_image if self.instance else None
        return image

    def clean(self):
        cleaned_data = super(StudentProfileForm, self).clean()
        has_pg = cleaned_data.get('has_post_graduation')
        if has_pg:
            pg_fields = ['pg_college', 'pg_university', 'pg_degree', 'pg_branch', 'pg_cgpa', 'pg_year']
            for field in pg_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, "This field is required since Post Graduation is selected.")
        return cleaned_data

    def save(self, commit=True):
        profile = super(StudentProfileForm, self).save(commit=False)
        full_name = self.cleaned_data.get('full_name', '').strip()
        if ' ' in full_name:
            first_name, last_name = full_name.split(' ', 1)
        else:
            first_name = full_name
            last_name = ''
        profile.user.first_name = first_name
        profile.user.last_name = last_name
        if self.cleaned_data.get('email'):
            profile.user.email = self.cleaned_data['email']
        profile.user.save()

        # Save explicit model fields
        if 'date_of_birth' in self.cleaned_data:
            profile.date_of_birth = self.cleaned_data.get('date_of_birth')
        if 'gender' in self.cleaned_data:
            profile.gender = self.cleaned_data.get('gender')
        if 'city' in self.cleaned_data:
            profile.city = self.cleaned_data.get('city')
        if 'state' in self.cleaned_data:
            profile.state = self.cleaned_data.get('state')
        if 'country' in self.cleaned_data:
            profile.country = self.cleaned_data.get('country')
        if 'linkedin_url' in self.cleaned_data:
            profile.linkedin_url = self.cleaned_data.get('linkedin_url')
        if 'github_url' in self.cleaned_data:
            profile.github_url = self.cleaned_data.get('github_url')
        if 'portfolio_website' in self.cleaned_data:
            profile.portfolio_website = self.cleaned_data.get('portfolio_website')
        if 'phone_number' in self.cleaned_data:
            profile.phone_number = self.cleaned_data.get('phone_number')
        if 'address' in self.cleaned_data:
            profile.address = self.cleaned_data.get('address')

        # Parse string parameters back into JSON arrays list
        skills_str = self.cleaned_data.get('raw_skills', '')
        profile.skills = [s.strip() for s in skills_str.split(',') if s.strip()]

        if commit:
            profile.save()
            self.save_m2m()
        return profile


class ResumeForm(forms.ModelForm):
    class Meta:
        model = TraineeProfile
        fields = ['resume_file']
        widgets = {
            'resume_file': forms.ClearableFileInput(attrs={'class': 'w-full text-slate-400 file:mr-4 file:py-3 file:px-6 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-emerald-600 file:text-white hover:file:bg-emerald-700 cursor-pointer'})
        }

    def clean_resume_file(self):
        resume = self.cleaned_data.get('resume_file')
        if resume:
            extension = os.path.splitext(resume.name)[1].lower()
            allowed_extensions = ['.pdf', '.docx']
            if extension not in allowed_extensions:
                raise forms.ValidationError("Illegal document signature: Only PDF or DOCX file sizes are allowed for placement submission.")
            
            # Optional: restrict size (e.g., 5MB limit)
            if resume.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Maximum file dimension exceeded: Resume file scale must be under 5MB.")
        return resume
