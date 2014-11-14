from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User, Group

from selectable import forms as selectable

from timepiece.utils.search import SearchForm
from timepiece.utils import get_setting

from timepiece.crm.lookups import (BusinessLookup, ProjectLookup, UserLookup,
        QuickLookup)
from timepiece.crm.models import (Attribute, Business, Project,
        ProjectRelationship, UserProfile, PaidTimeOffRequest, 
        PaidTimeOffLog, Milestone, ActivityGoal)


class CreateEditBusinessForm(forms.ModelForm):

    class Meta:
        model = Business
        fields = ('name', 'short_name', 'email', 'description', 'notes')


class CreateEditProjectForm(forms.ModelForm):
    # business = selectable.AutoCompleteSelectField(BusinessLookup)
    # business.widget.attrs['placeholder'] = 'Search'
    EMPLOYEE_CHOICES = [(u.pk, '%s, %s'%(u.last_name, u.first_name)) \
        for u in Group.objects.get(id=1).user_set.filter(
            is_active=True).order_by('last_name')]

    class Meta:
        model = Project
        fields = ('name', 'business', 'finder', 
                'point_person', 'binder', 'type', 
                'status', 'activity_group', 'description')

    def __init__(self, *args, **kwargs):
        super(CreateEditProjectForm, self).__init__(*args, **kwargs)
        self.fields['point_person'].label = 'Minder'
        self.EMPLOYEE_CHOICES.insert(0, ('', '-'))
        for f in ['point_person', 'finder', 'binder']:
            self.fields[f].choices = self.EMPLOYEE_CHOICES


class CreateUserForm(UserCreationForm):
    business = forms.ModelChoiceField(Business.objects.all())

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'is_active',
                'is_staff', 'groups')

    def __init__(self, *args, **kwargs):
        super(CreateUserForm, self).__init__(*args, **kwargs)
        self.fields['groups'].widget = forms.CheckboxSelectMultiple()
        self.fields['groups'].help_text = None

    def save(self, commit=True):
        user = super(CreateUserForm, self).save(commit)
        up = UserProfile(user=user, business=self.cleaned_data['business'])
        if commit:
            self.save_m2m()
            up.save()
        return user


class EditProjectRelationshipForm(forms.ModelForm):

    class Meta:
        model = ProjectRelationship
        fields = ('types',)

    def __init__(self, *args, **kwargs):
        super(EditProjectRelationshipForm, self).__init__(*args, **kwargs)
        self.fields['types'].widget = forms.CheckboxSelectMultiple(
                choices=self.fields['types'].choices)


class EditUserForm(UserChangeForm):
    password1 = forms.CharField(required=False, max_length=36,
            label='Password', widget=forms.PasswordInput(render_value=False))
    password2 = forms.CharField(required=False, max_length=36,
            label='Repeat Password',
            widget=forms.PasswordInput(render_value=False))
    business = forms.ModelChoiceField(Business.objects.all())

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'is_active',
                'is_staff', 'groups')

    def __init__(self, *args, **kwargs):
        super(EditUserForm, self).__init__(*args, **kwargs)
        self.fields['groups'].widget = forms.CheckboxSelectMultiple()
        self.fields['groups'].help_text = None
        self.fields['business'].initial = UserProfile.objects.get(user=kwargs['instance']).business
        # In 1.4 this field is created even if it is excluded in Meta.
        if 'password' in self.fields:
            del(self.fields['password'])

    def clean(self):
        super(EditUserForm, self).clean()
        password1 = self.cleaned_data.get('password1', None)
        password2 = self.cleaned_data.get('password2', None)
        if password1 and password1 != password2:
            raise forms.ValidationError('Passwords must match.')
        return self.cleaned_data

    def save(self, commit=True):
        instance = super(EditUserForm, self).save(commit=False)
        password1 = self.cleaned_data.get('password1', None)
        # set the user's business in UserProfile
        up = UserProfile.objects.get(user=instance)
        up.business = self.cleaned_data.get('business')
        if password1:
            instance.set_password(password1)
        if commit:
            instance.save()
            up.save()
            self.save_m2m()
        return instance


class EditUserSettingsForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super(EditUserSettingsForm, self).__init__(*args, **kwargs)
        for name in self.fields:
            self.fields[name].required = True


class ProjectSearchForm(SearchForm):
    status = forms.ChoiceField(required=False, choices=[], label='')

    def __init__(self, *args, **kwargs):
        print 'kwargs', kwargs.get('data', None)
        if get_setting('TIMEPIECE_DEFAULT_PROJECT_STATUS') and kwargs.get('data', None) is None:
            kwargs['data'] = {'status': get_setting('TIMEPIECE_DEFAULT_PROJECT_STATUS')}
        super(ProjectSearchForm, self).__init__(*args, **kwargs)
        statuses = Attribute.statuses.all()
        choices = [('', 'Any Status')] + [(a.pk, a.label) for a in statuses]
        self.fields['status'].choices = choices
        if get_setting('TIMEPIECE_DEFAULT_PROJECT_STATUS') and kwargs.get('data', None) is None:
            self.fields['status'].initial = get_setting('TIMEPIECE_DEFAULT_PROJECT_STATUS')


class QuickSearchForm(forms.Form):
    quick_search = selectable.AutoCompleteSelectField(QuickLookup, required=False)
    quick_search.widget.attrs['placeholder'] = 'Search'

    def clean_quick_search(self):
        item = self.cleaned_data['quick_search']
        if not item:
            msg = 'No user, business, or project matches your query.'
            raise forms.ValidationError(msg)
        return item

    def get_result(self):
        return self.cleaned_data['quick_search'].get_absolute_url()


class SelectProjectForm(forms.Form):
    project = selectable.AutoCompleteSelectField(ProjectLookup, label='')
    project.widget.attrs['placeholder'] = 'Add Project'

    def get_project(self):
        return self.cleaned_data['project'] if self.is_valid() else None


class SelectUserForm(forms.Form):
    user = selectable.AutoCompleteSelectField(UserLookup, label='')
    user.widget.attrs['placeholder'] = 'Add User'

    def get_user(self):
        return self.cleaned_data['user'] if self.is_valid() else None

class ApproveDenyPTORequestForm(forms.ModelForm):

    class Meta:
        model = PaidTimeOffRequest
        fields = ('approver_comment', )

class CreateEditPTORequestForm(forms.ModelForm):
    
    class Meta:
        model = PaidTimeOffRequest
        fields = ('pto', 'pto_start_date', 'pto_end_date', 'amount', 'comment')

class CreateEditPaidTimeOffLog(forms.ModelForm):

    class Meta:
        model = PaidTimeOffLog
        fields = ('user_profile', 'date', 'amount', 'comment', )

    def __init__(self, *args, **kwargs):
        super(CreateEditPaidTimeOffLog, self).__init__(*args, **kwargs)
        self.fields['user_profile'].label = 'Employee'
        up_choices = [(u.id, '%s, %s'%(u.last_name, u.first_name)) for u in Group.objects.get(id=1
            ).user_set.filter(is_active=True).order_by('last_name', 'first_name')]
        # up_choices.insert(0, ('', '-'))
        self.fields['user_profile'].choices = up_choices

class CreateEditMilestoneForm(forms.ModelForm):
    
    class Meta:
        model = Milestone
        fields = ('name', 'due_date', 'description')

class CreateEditActivityGoalForm(forms.ModelForm):
    EMPLOYEE_CHOICES = [(u.pk, '%s, %s'%(u.last_name, u.first_name)) \
        for u in Group.objects.get(id=1).user_set.filter(
            is_active=True).order_by('last_name')]

    class Meta:
        model = ActivityGoal
        fields = ('goal_hours', 'employee', 'activity', 'date')

    def __init__(self, *args, **kwargs):
        super(CreateEditActivityGoalForm, self).__init__(*args, **kwargs)
        self.EMPLOYEE_CHOICES.insert(0, ('', '-'))
        self.fields['employee'].choices = self.EMPLOYEE_CHOICES
