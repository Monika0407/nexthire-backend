# applications/forms.py
"""
Job Applications and Selection Offer Letter Forms.
Allows recruiters to dispatch formal compensation offers to successful candidates.
"""

from django import forms
from .models import Offer

class OfferForm(forms.ModelForm):
    """
    Form for Corporate recruiters to release selection letters to candidate students.
    """
    class Meta:
        model = Offer
        fields = ['trainee', 'job', 'package', 'offer_letter_text']
        widgets = {
            'trainee': forms.Select(attrs={
                'class': 'w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:border-indigo-500 text-xs sm:text-sm'
            }),
            'job': forms.Select(attrs={
                'class': 'w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:border-indigo-500 text-xs sm:text-sm'
            }),
            'package': forms.TextInput(attrs={
                'class': 'w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:border-indigo-500 text-xs sm:text-sm',
                'placeholder': 'e.g. 14 LPA (Base: 12 LPA + Bonuses)'
            }),
            'offer_letter_text': forms.Textarea(attrs={
                'class': 'w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:border-indigo-500 text-xs sm:text-sm h-36',
                'placeholder': 'Provide official onboarding instructions and compensation distributions detail lines...'
            }),
        }
