from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile
from django.db import connection

class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    last_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    email = forms.EmailField(max_length=254, help_text='Required. Inform a valid email address.')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', )

    def save(self, commit=True):
        user = super(SignUpForm, self).save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user
    


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('bio', 'city')


class UpdateProfile(forms.ModelForm):
    username = forms.CharField(required=True)
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')

    def clean_email(self):
        username = self.cleaned_data.get('username')
        email = self.cleaned_data.get('email')

        if email and User.objects.filter(email=email).exclude(username=username).count():
            raise forms.ValidationError('This email address is already in use. Please supply a different email address.')
        return email
 

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        #with connection.cursor() as cursor:
                #cursor.execute('''
                #UPDATE Profile SET first_name=%s, last_name = %s,
                #email = %s, bio = %s.. WHERE username = %s''',
                #[self.cleaned_data['first_name'], self.cleaned_data['last_name'],
                #self.cleaned_data['email'], self.cleaned_data['bio'], user.username])

        if commit:
            user.save()

        return user
