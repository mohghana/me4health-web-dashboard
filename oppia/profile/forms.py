# oppia/profile/forms.py
import hashlib
import urllib

from django import forms
from django.conf import settings
from django.contrib.auth import (authenticate, login, views)
from django.core.urlresolvers import reverse
from django.core.validators import validate_email
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Button, Layout, Fieldset, ButtonHolder, Submit, Div, HTML
from oppia.models import SchoolCode,Program

class LoginForm(forms.Form):
    username = forms.CharField(max_length=30, 
                               error_messages={'required': _(u'Please enter a username.')},)
    password = forms.CharField(widget=forms.PasswordInput,
                                error_messages={'required': _(u'Please enter a password.'),},      
                                required=True)
    next = forms.CharField(widget=forms.HiddenInput())
    
    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_action = reverse('profile_login')
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-4'
        self.helper.layout = Layout(
                                    'username',
                                    'password',
                                    'next',
                                Div(
                                   Submit('submit', _(u'Login'), css_class='btn btn-default'),
                                   HTML("""<a class="btn btn-default" href="{% url 'profile_reset' %}">"""+_(u'Forgotten password?') + """</a>"""),
                                   css_class='col-lg-offset-2 col-lg-4',
                                ),
        )
       
    def clean(self):
        cleaned_data = self.cleaned_data
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")
        
        user = authenticate(username=username, password=password)
        if user is None or not user.is_active:
            raise forms.ValidationError( _(u"Invalid username or password. Please try again."))
        return cleaned_data
     
class RegisterForm(forms.Form):
    CHOICES = (('-----','-----'),
               ('2012','2012'),
               ('2013','2013'),
               ('2014','2014'),
               ('2015','2015'),
               ('2016','2016'),
               ('2017','2017'),
               ('2018','2018'),
               ('2019','2019'),
               ('2020','2020'),
               ('2021','2021'),
               ('2022','2022'),
               ('2023','2023'),
               ('2024','2024'),
               ('2025','2025'),
               ('2026','2026'),
               ('2027','2027'),
               ('2028','2028'),
               ('2029','2029'),
               ('2030','2030'),
               ('2031','2031'),
               ('2032','2032'),
               ('2033','2033'),
               ('2034','2034'),
               ('2035','2035'),
               ('2036','2036'),
               ('2037','2037'),
               ('2038','2038'),
               ('2039','2039'),
               ('2040','2040'),
               ('2041','2041'),
               ('2042','2042'),
               ('2043','2043'),
               ('2044','2044'),
               ('2045','2045'),
               ('2046','2046'),
               ('2047','2047'),
               ('2048','2048'),
               ('2049','2049'),
               ('2050','2050'),)
    PROGRAM_CHOICES = (('-----','-----'),
                       ('Midwifery','Midwifery'),
                       ('Community Health Nursing','Community Health Nursing'),
                       ('Registered General Nursing','Registered General Nursing'),
                       ('Allied Health','Allied Health'),)
    STATUS_CHOICES = (('-----','-----'),
                      ('Tutor','Tutor'),
                      ('Student','Student'),
                      ('Guest','Guest'),)
    GENDER_CHOICES = (('-----','-----'),
                      ('Male','Male'),
                      ('Female','Female'),)
    REGIONS = ( ('-----','-----'),
               ('Greater Accra Region','Greater Accra Region'),
               ('Central Region','Central Region'),
               ('Ashanti Region','Ashanti Region'),
               ('Brong Ahafo Region','Brong Ahafo Region'),
               ('Upper East Region','Upper East Region'),
               ('Upper West Region','Upper West Region'),
               ('Northern Region','Northern Region'),
               ('Volta Region','Volta Region'),
               ('Western Region','Western Region'),
               ('Eastern Region','Eastern Region'),)
    username = forms.CharField(max_length=30, 
                               min_length=4,
                               error_messages={'required': _(u'Please enter a username.')},)
    email = forms.CharField(validators=[validate_email],
                                error_messages={'invalid': _(u'Please enter a valid e-mail address.'),
                                                'required': _(u'Please enter your e-mail address.')},
                                required=True)
    password = forms.CharField(widget=forms.PasswordInput,
                                error_messages={'required': _(u'Please enter a password.'),
                                                'min_length': _(u'Your password should be at least 6 characters long.')},
                                min_length=6,       
                                required=True)
    password_again = forms.CharField(widget=forms.PasswordInput,
                                    min_length=6,
                                    error_messages={'required': _(u'Please enter your password again.'),
                                                    'min_length': _(u'Your password again should be at least 6 characters long.')},
                                    required=True)
    first_name = forms.CharField(max_length=100,
                                    error_messages={'required': _(u'Please enter your first name.'),
                                                    'min_length': _(u'Your first name should be at least 2 characters long.')},
                                    min_length=2,
                                    required=True)
    last_name = forms.CharField(max_length=100,
                                error_messages={'required': _(u'Please enter your last name.'),
                                                'min_length': _(u'Your last name should be at least 2 characters long.')},
                                min_length=2,
                                required=True)
    phone_number = forms.CharField(max_length=10,
                                error_messages={'required': _(u'Please enter your mobile number.'),
                                                'min_length': _(u'Your mobile number should be at least 10 characters long.')},
                                min_length=10,
                                required=True)
    school_code = forms.CharField(error_messages={'required': _(u'Please enter your your school code.')},
                                required=False)
    year_group = forms.ChoiceField(choices=CHOICES,
                                           widget=forms.Select(),required=False)
    program = forms.ChoiceField(choices=PROGRAM_CHOICES,
                                           widget=forms.Select(),required=False)
    #program = forms.ModelChoiceField(queryset=Program.objects.all(),required=True)
    status = forms.ChoiceField(choices=STATUS_CHOICES,
                                           widget=forms.Select(),required=True)
    home_town = forms.ChoiceField(choices=REGIONS,
                                           widget=forms.Select(),required=False)
    job_title = forms.CharField(max_length=100,required=False)
    organisation = forms.CharField(max_length=100,required=False)
    gender = forms.ChoiceField(choices=GENDER_CHOICES,
                                           widget=forms.Select(),required=True)
    #school_code = forms.ModelChoiceField(queryset=SchoolCode.objects.all(),required=True)

    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)
        if self.fields['status'] == "Guest":
            self.fields['home_town'].required =True
            #self.fields['year_group'].required=True
            #self.fields['program'].required=True
        if self.fields['status'] =="Tutor":
            self.fields['home_town'].required =False
            self.fields['year_group'].required=True
            self.fields['program'].required=False
        if self.fields['status'] =="Student":
            self.fields['home_town'].required =False
            self.fields['year_group'].required=True
            self.fields['program'].required=True
        self.helper = FormHelper()
        self.helper.form_action = reverse('profile_register')
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-4'
        self.helper.layout = Layout(
                                    'username',
                                    'email',
                                    'password',
                                    'password_again',
                                    'first_name',
                                    'last_name',
                                    'gender',
                                    'phone_number',
                                    'status',
                                    'school_code',
                                    'year_group',
                                    'program',
                                    'home_town',
                                Div(
                                   Submit('submit', _(u'Register'), css_class='btn btn-default'),
                                   css_class='col-lg-offset-2 col-lg-4',
                                ),
        )

    def clean(self):
        cleaned_data = self.cleaned_data
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")
        password_again = cleaned_data.get("password_again")
        username = cleaned_data.get("username")
        gender = cleaned_data.get("gender")
        phone_number = cleaned_data.get("phone_number")
        year_group = cleaned_data.get("year_group")
        school_code = cleaned_data.get("school_code")
        status = cleaned_data.get("status")
        home_town = cleaned_data.get("home_town")
        program = cleaned_data.get("program")

        #if cleaned_data.get('status')=="Guest":
         #   del self.errors['school_code']
        # check the username not already used
        num_rows = User.objects.filter(username=username).count()
        if num_rows != 0:
            raise forms.ValidationError( _(u"Username has already been registered, please select another."))
        
        # check the email address not already used
        num_rows = User.objects.filter(email=email).count()
        if num_rows != 0:
            raise forms.ValidationError( _(u"Email has already been registered"))

        # check the password are the same
        if password and password_again:
            if password != password_again:
                raise forms.ValidationError( _(u"Passwords do not match."))

        # check the school code
        school_code_existing = SchoolCode.objects.filter(
                       school_code=school_code,).count()
        if school_code_existing == 0 and cleaned_data.get('status')!="Guest":
            raise forms.ValidationError(_(u'This school code does not exist!'))
        # Always return the full collection of cleaned data.
        return cleaned_data

class ResetForm(forms.Form):
    username = forms.CharField(max_length=30,
        error_messages={'invalid': _(u'Please enter a username or email address.')},
        required=True)
    
    def __init__(self, *args, **kwargs):
        super(ResetForm, self).__init__(*args, **kwargs)
        self.fields['username'].label = "Username or email"
        self.helper = FormHelper()
        self.helper.form_action = reverse('profile_reset')
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-4'
        self.helper.layout = Layout(
                                    'username',
                                Div(
                                   Submit('submit', _(u'Reset password'), css_class='btn btn-default'),
                                   css_class='col-lg-offset-2 col-lg-4',
                                ),
        )
    
    def clean(self):
        cleaned_data = self.cleaned_data
        username = cleaned_data.get("username")
        try:
            user = User.objects.get(username__exact=username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email__exact=username)
            except User.DoesNotExist:
                raise forms.ValidationError( _(u"Username/email not found"))
        return cleaned_data

class SchoolCodeForm(forms.Form):
    REGIONS = (('Greater Accra Region','Greater Accra Region'),
               ('Central Region','Central Region'),
               ('Ashanti Region','Ashanti Region'),
               ('Brong Ahafo Region','Brong Ahafo Region'),
               ('Upper East Region','Upper East Region'),
               ('Upper West Region','Upper West Region'),
               ('Northern Region','Northern Region'),
               ('Volta Region','Volta Region'),
               ('Western Region','Western Region'),
               ('Eastern Region','Eastern Region'),)
    TYPES = (('Registered Midwifery','Registered Midwifery'),
               ('Postbasic Midwifery','Postbasic Midwifery'),
               ('HAC/Midwifery','HAC/Midwifery'),
               ('Midwifery','Midwifery'),
               ('Nursing/Midwifery','Nursing/Midwifery'),
               ('Community Health Nursing','Community Health Nursing'),
               ('CHNTS','CHNTS'),
               ('RGN','RGN'),
               ('CHNTS/Nursing','CHNTS/Nursing'),
               ('Health Assistant Clinical','Health Assistant Clinical'),
               ('HAC/PB Midwifery','HAC/PB Midwifery'),)
    school_name = forms.CharField(max_length=30,
        error_messages={'invalid': _(u'Please enter a school name.')},
        required=True)
    school_code = forms.CharField(max_length=30,
        error_messages={'invalid': _(u'Please enter a school code.')},
        required=True)
    region = forms.ChoiceField(choices=REGIONS,
                                           widget=forms.Select(),required=True)
    school_type = forms.ChoiceField(choices=TYPES,
                                           widget=forms.Select(),required=True)
    
    def __init__(self, *args, **kwargs):
        super(SchoolCodeForm, self).__init__(*args, **kwargs)
        self.fields['school_name'].label = "Name of School"
        self.helper = FormHelper()
        self.helper.form_action = reverse('profile_school_code')
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-4'
        self.helper.layout = Layout(
                                    'school_name',
                                    'school_code',
                                    'region',
                                    'school_type',
                                Div(
                                   Submit('submit', _(u'Save'), css_class='btn btn-default'),
                                   css_class='col-lg-offset-2 col-lg-4',
                                ),
        )
class ProgramForm(forms.Form):
  
    program_name = forms.CharField(max_length=30,
        error_messages={'invalid': _(u'Please enter a program name.')},
        required=True)
    
    def __init__(self, *args, **kwargs):
        super(ProgramForm, self).__init__(*args, **kwargs)
        self.fields['program_name'].label = "Program Name"
        self.helper = FormHelper()
        self.helper.form_action = reverse('profile_program')
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-4'
        self.helper.layout = Layout(
                                    'program_name',
                                Div(
                                   Submit('submit', _(u'Save'), css_class='btn btn-default'),
                                   css_class='col-lg-offset-2 col-lg-4',
                                ),
        )
class ProfileForm(forms.Form):
    CHOICES = (('-----','-----'),
              ('2012','2012'),
               ('2013','2013'),
               ('2014','2014'),
               ('2015','2015'),
               ('2016','2016'),
               ('2017','2017'),
               ('2018','2018'),
               ('2019','2019'),
               ('2020','2020'),
               ('2021','2021'),
               ('2022','2022'),
               ('2023','2023'),
               ('2024','2024'),
               ('2025','2025'),
               ('2026','2026'),
               ('2027','2027'),
               ('2028','2028'),
               ('2029','2029'),
               ('2030','2030'),
               ('2031','2031'),
               ('2032','2032'),
               ('2033','2033'),
               ('2034','2034'),
               ('2035','2035'),
               ('2036','2036'),
               ('2037','2037'),
               ('2038','2038'),
               ('2039','2039'),
               ('2040','2040'),
               ('2041','2041'),
               ('2042','2042'),
               ('2043','2043'),
               ('2044','2044'),
               ('2045','2045'),
               ('2046','2046'),
               ('2047','2047'),
               ('2048','2048'),
               ('2049','2049'),
               ('2050','2050'),)
    STATUS_CHOICES = (('-----','-----'),
                      ('Tutor','Tutor'),
                      ('Student','Student'),
                      ('Guest','Guest'),)
    GENDER_CHOICES = (('-----','-----'),
                      ('Male','Male'),
                      ('Female','Female'),)
    PROGRAM_CHOICES= (('-----','-----'),
                ('Midwifery','Midwifery'),
               ('Community Health Nursing','Community Health Nursing'),
               ('Registered General Nursing','Registered General Nursing'),
               ('Allied Health','Allied Health'),)
    REGIONS = (('-----','-----'),
               ('Greater Accra Region','Greater Accra Region'),
               ('Central Region','Central Region'),
               ('Ashanti Region','Ashanti Region'),
               ('Brong Ahafo Region','Brong Ahafo Region'),
               ('Upper East Region','Upper East Region'),
               ('Upper West Region','Upper West Region'),
               ('Northern Region','Northern Region'),
               ('Volta Region','Volta Region'),
               ('Western Region','Western Region'),
               ('Eastern Region','Eastern Region'),)
    api_key = forms.CharField(widget = forms.TextInput(attrs={'readonly':'readonly'}),
                               required=False, help_text=_(u'You cannot edit the API Key.'))
    username = forms.CharField(widget = forms.TextInput(attrs={'readonly':'readonly'}),
                               required=False, help_text=_(u'You cannot edit the username.'))
    email = forms.CharField(validators=[validate_email],
                            error_messages={'invalid': _(u'Please enter a valid e-mail address.')},
                            required=True)
    password = forms.CharField(widget=forms.PasswordInput,
                               required=False,
                               min_length=6,
                               error_messages={'min_length': _(u'The new password should be at least 6 characters long')},)
    password_again = forms.CharField(widget=forms.PasswordInput,
                                     required=False,
                                     min_length=6)
    first_name = forms.CharField(max_length=100,
                                 min_length=2,
                                 required=True)
    last_name = forms.CharField(max_length=100,
                                min_length=2,
                                required=True)
    phone_number = forms.CharField(max_length=10,
                                error_messages={'required': _(u'Please enter your mobile number.'),
                                                'min_length': _(u'Your mobile number should be at least 10 characters long.')},
                                min_length=10,
                                required=True)
    phone_number_two = forms.CharField(max_length=10,
                                error_messages={'required': _(u'Please enter your mobile number.'),
                                                'min_length': _(u'Your mobile number should be at least 10 characters long.')},
                                min_length=10,
                                required=False)
    phone_number_three = forms.CharField(max_length=10,
                                error_messages={'required': _(u'Please enter your mobile number.'),
                                                'min_length': _(u'Your mobile number should be at least 10 characters long.')},
                                min_length=10,
                                required=False)
    #school_code = forms.ModelChoiceField(queryset=SchoolCode.objects.all(),required=True)
    school_code = forms.CharField(error_messages={'required': _(u'Please enter your your school code.')},
                                required=False)
    year_group = forms.ChoiceField(choices=CHOICES,
                                           widget=forms.Select(),required=False)
    program = forms.ChoiceField(choices=PROGRAM_CHOICES,
                                           widget=forms.Select(),required=False)
    #program = forms.ModelChoiceField(queryset=Program.objects.all(),required=True)
    status = forms.ChoiceField(choices=STATUS_CHOICES,
                                           widget=forms.Select(),required=True)
    home_town = forms.ChoiceField(choices=REGIONS,
                                           widget=forms.Select(),required=False)
    gender = forms.ChoiceField(choices=GENDER_CHOICES,
                                           widget=forms.Select(),required=True)
    
    
    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        if self.fields['status'] == "Guest":
            self.fields['home_town'].required =True
            #self.fields['year_group'].required=True
            #self.fields['program'].required=True
        if self.fields['status'] =="Tutor":
            self.fields['home_town'].required =False
            self.fields['year_group'].required=True
            self.fields['program'].required=False
        if self.fields['status'] =="Student":
            self.fields['home_town'].required =False
            self.fields['year_group'].required=True
            self.fields['program'].required=True
        if len(args) == 1:
            email = args[0]['email']
            username = args[0]['username']
        else:
            kw = kwargs.pop('initial')
            email = kw['email'] 
            username = kw['username'] 
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-4'
        if settings.OPPIA_SHOW_GRAVATARS:
            gravatar_url = "https://www.gravatar.com/avatar.php?"
            gravatar_url += urllib.urlencode({
                'gravatar_id':hashlib.md5(email).hexdigest(),
                'size':64
            })
            self.helper.layout = Layout(
                    Div(
                        HTML("""<label class="control-label col-lg-2">"""+_(u'Photo') + """</label>"""),
                        Div(
                            HTML(mark_safe('<img src="{0}" alt="gravatar for {1}" class="gravatar" width="{2}" height="{2}"/>'.format(gravatar_url, username, 64))),
                            HTML("""<br/>"""),
                            HTML("""<a href="https://www.gravatar.com">"""+_(u'Update gravatar')+"""</a>"""),
                            css_class="col-lg-4",
                        ),
                        css_class="form-group",
                        ),
                    'api_key',
                    'username',
                    'email',
                    'first_name',
                    'last_name',
                    'gender',
                    'phone_number',
                    'phone_number_two',
                    'phone_number_three',
                    'status',
                    'school_code',
                    'year_group',
                    'program',
                    'home_town',
                    Div(
                        HTML("""<h3>"""+_(u'Change password') + """</h3>"""),
                        ),
                    'password',
                    'password_again',
                    Div(
                       Submit('submit', _(u'Save'), css_class='btn btn-default'),
                       css_class='col-lg-offset-2 col-lg-4',
                    ),
                )
        else:
            self.helper.layout = Layout(
                    'api_key',
                    'username',
                    'email',
                    'first_name',
                    'last_name',
                    Div(
                        HTML("""<h3>"""+_(u'Change password') + """</h3>"""),
                        ),
                    'password',
                    'password_again',
                    Div(
                       Submit('submit', _(u'Save'), css_class='btn btn-default'),
                       css_class='col-lg-offset-2 col-lg-4',
                    ),
                )      

        
    def clean(self):
        cleaned_data = self.cleaned_data
        # check email not used by anyone else
        if cleaned_data.get('status')=="Guest":
            del self.errors['school_code']
            #del self.errors['program']
            #del self.errors['year_group']
        email = cleaned_data.get("email")
        username = cleaned_data.get("username")
        school_code = cleaned_data.get("school_code")
        num_rows = User.objects.exclude(username__exact=username).filter(email=email).count()
        if num_rows != 0:
            raise forms.ValidationError( _(u"Email address already in use"))
        
        # if password entered then check they are the same
        password = cleaned_data.get("password")
        password_again = cleaned_data.get("password_again")
        if password and password_again:
            if password != password_again:
                raise forms.ValidationError( _(u"Passwords do not match."))
        school_code_existing = SchoolCode.objects.filter(
                       school_code=school_code,).exists()
        if not school_code_existing and cleaned_data.get("status")!="Guest":
            raise forms.ValidationError(_(u'This school code does not exist!')) 
        return cleaned_data
    
class UploadProfileForm(forms.Form):
    upload_file = forms.FileField(
                required=True,
                error_messages={'required': _('Please select a file to upload')},)
    
    def __init__(self, *args, **kwargs):
        super(UploadProfileForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_action = reverse('profile_upload')
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-4'
        self.helper.layout = Layout(
                'upload_file',
                Div(
                   Submit('submit', _(u'Upload'), css_class='btn btn-default'),
                   css_class='col-lg-offset-2 col-lg-4',
                ),
            ) 
class UploadSchoolCodeForm(forms.Form):
    upload_file = forms.FileField(
                required=True,
                error_messages={'required': _('Please select a file to upload')},)
    
    def __init__(self, *args, **kwargs):
        super(UploadSchoolCodeForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_action = reverse('profile_upload_school')
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-4'
        self.helper.layout = Layout(
                'upload_file',
                Div(
                   Submit('submit', _(u'Upload'), css_class='btn btn-default'),
                   css_class='col-lg-offset-2 col-lg-4',
                ),
            ) 
    