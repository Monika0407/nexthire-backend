# interviews/forms.py
"""
Interview Scheduling Forms.
Enables recruiters to draft meeting coordinate lines and configure digital meet slots.
"""

from django import forms
from .models import Interview

class InterviewForm(forms.ModelForm):
    """
    Form for corporate partners to invite candidates to scheduled video calls.
    """
    class Meta:
        model = Interview
        fields = ['title', 'stage', 'scheduled_at', 'platform', 'meet_url']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:border-indigo-500 text-xs sm:text-sm',
                'placeholder': 'e.g. Technical Engineering Round 1'
            }),
            'stage': forms.Select(attrs={
                'class': 'w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:border-indigo-500 text-xs sm:text-sm'
            }),
            'scheduled_at': forms.DateTimeInput(attrs={
                'class': 'w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:border-indigo-500 text-xs sm:text-sm',
                'type': 'datetime-local'
            }),
            'platform': forms.TextInput(attrs={
                'class': 'w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:border-indigo-500 text-xs sm:text-sm',
                'placeholder': 'e.g. Google Meet, Zoom, MS Teams'
            }),
            'meet_url': forms.URLInput(attrs={
                'class': 'w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:border-indigo-500 text-xs sm:text-sm',
                'placeholder': 'https://meet.google.com/abc-defg-hij'
            }),
        }


class InterviewEvaluationForm(forms.ModelForm):
    """
    Form for evaluating candidate performance, assigning scores and giving detailed remarks.
    """
    class Meta:
        model = Interview
        fields = ['status', 'feedback_notes', 'rating_score']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:border-indigo-500 text-xs sm:text-sm'
            }),
            'feedback_notes': forms.Textarea(attrs={
                'class': 'w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:border-indigo-500 text-xs sm:text-sm h-32',
                'placeholder': 'Enter comprehensive interview remarks, technical proficiency notes and cultural alignments...'
            }),
            'rating_score': forms.NumberInput(attrs={
                'class': 'w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:border-indigo-500 text-xs sm:text-sm',
                'min': 1, 'max': 5, 'placeholder': 'Rate from 1 (poor) to 5 (excellent)'
            }),
        }
