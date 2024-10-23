# In Escheduler/forms.py
from django import forms
from .models import *
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError



class AvailabilityForm(forms.ModelForm):
    availability_days = forms.MultipleChoiceField(
        choices=[
            ('Monday', 'Monday'),
            ('Tuesday', 'Tuesday'),
            ('Wednesday', 'Wednesday'),
            ('Thursday', 'Thursday'),
            ('Friday', 'Friday'),
            ('Saturday', 'Saturday'),
            ('Sunday', 'Sunday'),
        ],
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Select your available days"
    )

    class Meta:
        model = Employee
        fields = ['availability_start', 'availability_end', 'availability_days']

class ShiftSwapRequestForm(forms.ModelForm):
    requested_shift = forms.ModelChoiceField(
        queryset=Shift.objects.all(),
        required=True,
        widget=forms.Select(attrs={'placeholder': 'Select shift to swap with'}),
        label="Select Shift to Swap With"
    )

    class Meta:
        model = ShiftSwapRequest
        fields = ['requested_shift', 'reason']  # Include requested_shift in fields
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Why do you want to swap this shift?'}),
        }

class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, help_text='Enter your first name')
    middle_name = forms.CharField(max_length=30, required=False, help_text='Enter your middle name')
    last_name = forms.CharField(max_length=30, required=True, help_text='Enter your last name')
    email = forms.EmailField(
        max_length=254,
        required=True,
        help_text='Enter a valid work email address',
        label='Work Email'
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'middle_name', 'last_name', 'email', 'password1', 'password2']

    def clean_email(self):
        """Ensure email uniqueness."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with that email already exists.")
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = False  
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

