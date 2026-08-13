# recruiters/forms.py
"""
Django forms for Corporate Recruiter Profile and Job management.
Handles website clean references, field layout decorations, and comma-separated tags conversion for skills_required.
"""

from django import forms
from .models import RecruiterProfile
from jobs.models import Job

class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = RecruiterProfile
        fields = [
            'company_name', 'industry_domain', 'company_website', 
            'contact_email', 'about_company'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'Enterprise Name'}),
            'industry_domain': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'e.g. Information Technology'}),
            'company_website': forms.URLInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'https://company.org'}),
            'contact_email': forms.EmailInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'recruitment@company.org'}),
            'about_company': forms.Textarea(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100 h-28', 'placeholder': 'Share details about the core work, growth trajectory and culture.'}),
        }


class JobForm(forms.ModelForm):
    raw_skills = forms.CharField(
        label="Required Technical Skills",
        help_text="Provide relevant technical tags separated by commas",
        widget=forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'Python, Django, React, MySQL'}),
        required=True
    )

    class Meta:
        model = Job
        fields = [
            'title', 'description', 'job_type', 'location', 
            'salary_package', 'min_cgpa_required', 'experience_required', 'is_active', 
            'application_deadline', 'required_courses'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'e.g. Senior Backend Engineer'}),
            'description': forms.Textarea(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100 h-32', 'placeholder': 'Role description and daily checklist.'}),
            'job_type': forms.Select(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100'}),
            'location': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'Bengaluru, IND'}),
            'salary_package': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'e.g. 12 LPA'}),
            'min_cgpa_required': forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'step': '0.01', 'placeholder': '7.00'}),
            'experience_required': forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'placeholder': 'e.g. 2'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded bg-slate-900 border-slate-800 text-indigo-600 focus:ring-indigo-500 w-4 h-4 cursor-pointer'}),
            'application_deadline': forms.DateInput(attrs={'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm text-slate-100', 'type': 'date'}),
            'required_courses': forms.CheckboxSelectMultiple(attrs={'class': 'rounded bg-slate-900 border-slate-800 text-indigo-600 focus:ring-indigo-500 w-4 h-4 cursor-pointer'}),
        }

    def __init__(self, *args, **kwargs):
        super(JobForm, self).__init__(*args, **kwargs)
        self.fields['required_courses'].required = True
        if self.instance and self.instance.pk:
            self.fields['raw_skills'].initial = ", ".join(self.instance.skills_required) if self.instance.skills_required else ""

    def save(self, commit=True):
        job = super(JobForm, self).save(commit=False)
        
        # Parse text string back into a pristine JSON array list
        skills_str = self.cleaned_data.get('raw_skills', '')
        job.skills_required = [s.strip() for s in skills_str.split(',') if s.strip()]
        
        if commit:
            job.save()
        return job
