from django import forms
from django.contrib.auth.models import User

from .models import UserProfile


class UserProfileForm(forms.ModelForm):

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )

    class Meta:
        model = UserProfile

        fields = [
            'full_name',
            'phone',
        ]

        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your full name'
            }),

            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your phone number'
            }),
        }

    def __init__(self, *args, **kwargs):

        self.user = kwargs.pop('user', None)

        super().__init__(*args, **kwargs)

        if self.user:
            self.fields['email'].initial = self.user.email

    def clean_email(self):
        email = self.cleaned_data['email']

        if User.objects.filter(
            email__iexact=email
        ).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError(
                'An account with this email address already exists.'
            )

        return email

    def save(self, commit=True):

        profile = super().save(commit=False)

        if commit:
            profile.save()

            self.user.email = self.cleaned_data['email']
            self.user.first_name = profile.full_name

            self.user.save()

        return profile