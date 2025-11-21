# app1/forms.py
from django import forms
from .models import ResumeMatch

class ResumeMatchForm(forms.ModelForm):
    class Meta:
        model = ResumeMatch
        fields = ['resume_file', 'job_description']
        widgets = {
            'job_description': forms.Textarea(attrs={'rows': 6, 'placeholder': 'Paste job description here...'}),
        }

    def clean_resume_file(self):
        f = self.cleaned_data.get('resume_file')
        if f:
            if not f.name.lower().endswith('.pdf'):
                raise forms.ValidationError("Only PDF resumes are allowed.")
            if f.size > 8 * 1024 * 1024:  # 8 MB
                raise forms.ValidationError("PDF too large (max 8MB).")
        return f
