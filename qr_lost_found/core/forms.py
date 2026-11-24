import logging

from django.conf import settings
from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.contrib.auth.models import User

from .models import UserProfile


logger = logging.getLogger(__name__)


class EmailOrUsernameAuthenticationForm(AuthenticationForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Username or email'
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Enter your username or email',
        })

    def clean(self):
        username = self.cleaned_data.get('username')

        if username and not User.objects.filter(username=username).exists():
            user = User.objects.filter(email__iexact=username).first()
            if user:
                self.cleaned_data['username'] = user.get_username()

        return super().clean()


class ReturnLoopPasswordResetForm(PasswordResetForm):
    def save(self, *args, **kwargs):
        email = self.cleaned_data.get('email', '')
        eligible_accounts = sum(1 for _ in self.get_users(email))
        result = super().save(*args, **kwargs)
        logger.info(
            'Password reset processing completed; eligible_accounts=%s, '
            'email_delivery_configured=%s',
            eligible_accounts,
            settings.EMAIL_DELIVERY_CONFIGURED,
        )
        return result


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
            'member_type',
            'institution_name',
            'affiliation_id',
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

            'member_type': forms.Select(attrs={
                'class': 'form-control',
            }),

            'institution_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your university or institution'
            }),

            'affiliation_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional student or staff ID'
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
            self.user.first_name, _, self.user.last_name = (
                profile.full_name.partition(' ')
            )

            self.user.save()

        return profile


class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    subject = forms.CharField(
        max_length=180,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    message = forms.CharField(
        max_length=3000,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'maxlength': '3000',
        })
    )
    website = forms.CharField(
        required=False,
        label='Leave this field empty',
        widget=forms.TextInput(attrs={
            'class': 'visually-hidden',
            'tabindex': '-1',
            'autocomplete': 'off',
            'aria-hidden': 'true',
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('website'):
            raise forms.ValidationError(
                'Please leave the hidden field empty.'
            )
        return cleaned_data


class FinderNotificationForm(forms.Form):
    message = forms.CharField(
        max_length=2000,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'id': 'message',
            'maxlength': '2000',
            'required': True,
            'placeholder': 'Describe the item and where it is safe to collect.',
        })
    )
    location = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'location',
            'maxlength': '255',
            'placeholder': 'Optional: where did you find it?',
        })
    )
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'visually-hidden',
            'tabindex': '-1',
            'autocomplete': 'off',
            'aria-hidden': 'true',
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('website'):
            raise forms.ValidationError(
                'Please leave the hidden field empty.'
            )
        return cleaned_data