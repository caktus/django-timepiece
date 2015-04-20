from django import forms
from django.forms import widgets
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User, Group

from selectable import forms as selectable

from timepiece.utils.search import SearchForm
from timepiece.utils import get_setting

from timepiece.crm.lookups import (BusinessLookup, ProjectLookup, UserLookup,
        QuickLookup, ContactLookup)
from timepiece.crm.models import (Attribute, Business, Project,
        ProjectRelationship, UserProfile, PaidTimeOffRequest, 
        PaidTimeOffLog, Milestone, ActivityGoal, BusinessNote,
        BusinessDepartment, Contact, ContactNote, Lead, LeadNote,
        DistinguishingValueChallenge, TemplateDifferentiatingValue,
        DVCostItem, Opportunity, LeadAttachment)

import datetime


class CreateEditBusinessForm(forms.ModelForm):
    EMPLOYEE_CHOICES = [(None, '-')] + [(u.pk, '%s, %s'%(u.last_name, u.first_name)) \
        for u in Group.objects.get(id=1).user_set.filter(
            is_active=True).order_by('last_name', 'first_name')]

    class Meta:
        model = Business
        fields = ('name', 'short_name', 'active', 'description', 'primary_contact',
            'phone', 'fax', 'website', 'industry', 
            'classification', 'status', 'account_owner',
            'billing_street',  'billing_city', 'billing_state',  
            'billing_postalcode',  'billing_mailstop',  'billing_country', 
            'shipping_street',  'shipping_city', 'shipping_state',  
            'shipping_postalcode',  'shipping_mailstop',  'shipping_country',
            'account_number', 'ownership', 'annual_revenue',
            'num_of_employees', 'ticker_symbol')

    def __init__(self, *args, **kwargs):        
        super(CreateEditBusinessForm, self).__init__(*args, **kwargs)
        self.fields['account_owner'].choices = self.EMPLOYEE_CHOICES

    def clean_short_name(self):
        short_name = self.cleaned_data['short_name']
        if len(short_name) == 0:
            raise forms.ValidationError("A Short Name is required.")

        return short_name

class CreateEditBusinessDepartmentForm(forms.ModelForm):

    class Meta:
        model = BusinessDepartment
        fields = ('name', 'short_name', 'active', 'business', 'poc', 
            'bd_billing_street', 'bd_billing_city', 'bd_billing_state',
            'bd_billing_postalcode', 'bd_billing_mailstop',
            'bd_billing_country', 'bd_shipping_street', 'bd_shipping_city', 
            'bd_shipping_state', 'bd_shipping_postalcode', 
            'bd_shipping_mailstop', 'bd_shipping_country')

    def __init__(self, *args, **kwargs):
        super(CreateEditBusinessDepartmentForm, self).__init__(*args, **kwargs)
        print kwargs
        self.fields['business'].widget = widgets.HiddenInput()
        self.fields['business'].initial = kwargs.get('business', None)

class AddBusinessNoteForm(forms.ModelForm):

    class Meta:
        model = BusinessNote
        fields = ('text', 'business', 'author')

    def __init__(self, *args, **kwargs):
        super(AddBusinessNoteForm, self).__init__(*args, **kwargs)
        self.fields['text'].label = ''
        self.fields['text'].widget.attrs['rows'] = 4
        self.fields['author'].widget = widgets.HiddenInput()
        self.fields['business'].widget = widgets.HiddenInput()

class CreateEditProjectForm(forms.ModelForm):
    # business = selectable.AutoCompleteSelectField(BusinessLookup)
    # business.widget.attrs['placeholder'] = 'Search'
    EMPLOYEE_CHOICES = [(u.pk, '%s, %s'%(u.last_name, u.first_name)) \
        for u in Group.objects.get(id=1).user_set.filter(
            is_active=True).order_by('last_name')]

    class Meta:
        model = Project
        fields = ('name', 'business', 'business_department', 'finder', 
                'point_person', 'binder', 'type', 
                'status', 'activity_group', 'description')

    def __init__(self, *args, **kwargs):
        super(CreateEditProjectForm, self).__init__(*args, **kwargs)
        self.fields['point_person'].label = 'Minder'
        self.EMPLOYEE_CHOICES.insert(0, ('', '-'))
        for f in ['point_person', 'finder', 'binder']:
            self.fields[f].choices = self.EMPLOYEE_CHOICES

    def clean(self):
            cleaned_data = super(CreateEditProjectForm, self).clean()
            
            biz = cleaned_data.get('business', None)
            biz_dept = cleaned_data.get('business_department', None)
            
            if biz_dept and biz_dept.business != biz:
                self._errors['business_department'] = self.error_class(
                    ['Selected Company Department does not belong to selected Company.'])

            return cleaned_data

class CreateUserForm(UserCreationForm):
    business = forms.ModelChoiceField(Business.objects.all())
    hire_date = forms.DateField()
    earns_pto = forms.BooleanField(required=False, label='Earns PTO')
    earns_holiday_pay = forms.BooleanField(required=False, label='Earns Holiday Pay')
    pto_accrual = forms.FloatField(initial=0.0, label='PTO Accrual Amount', help_text='Number of PTO hours earned per pay period for the employee.')
    employee_type = forms.ChoiceField(choices=UserProfile.EMPLOYEE_TYPES.items())

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
        up = UserProfile(user=user,
                         business=self.cleaned_data['business'],
                         hire_date=self.cleaned_data['hire_date'],
                         earns_pto=self.cleaned_data['earns_pto'],
                         earns_holiday_pay=self.cleaned_data['earns_holiday_pay'],
                         pto_accrual=self.cleaned_data['pto_accrual'],
                         employee_type=self.cleaned_data['employee_type'])
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
    hire_date = forms.DateField()
    hours_per_week = forms.DecimalField(max_digits=4, decimal_places=2)
    earns_pto = forms.BooleanField(required=False, label='Earns PTO')
    earns_holiday_pay = forms.BooleanField(required=False, label='Earns Holiday Pay')
    pto_accrual = forms.FloatField(initial=0.0, label='PTO Accrual Amount', help_text='Number of PTO hours earned per pay period for the employee.')
    employee_type = forms.ChoiceField(choices=UserProfile.EMPLOYEE_TYPES.items())

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'is_active',
                'is_staff', 'groups')

    def __init__(self, *args, **kwargs):
        super(EditUserForm, self).__init__(*args, **kwargs)
        self.fields['groups'].widget = forms.CheckboxSelectMultiple()
        self.fields['groups'].help_text = None
        up = UserProfile.objects.get(user=kwargs['instance'])
        self.fields['business'].initial = up.business
        self.fields['hire_date'].initial = up.hire_date
        self.fields['hours_per_week'].initial = up.hours_per_week
        self.fields['earns_pto'].initial = up.earns_pto
        self.fields['earns_holiday_pay'].initial = up.earns_holiday_pay
        self.fields['pto_accrual'].initial = up.pto_accrual
        self.fields['employee_type'].initial = up.employee_type
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
        up.hire_date = self.cleaned_data['hire_date']
        up.hours_per_week = self.cleaned_data['hours_per_week']
        up.earns_pto = self.cleaned_data['earns_pto']
        up.earns_holiday_pay = self.cleaned_data['earns_holiday_pay']
        up.pto_accrual = self.cleaned_data['pto_accrual']
        up.employee_type = self.cleaned_data['employee_type']

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

class SelectContactForm(forms.Form):
    user = selectable.AutoCompleteSelectField(ContactLookup, label='')
    user.widget.attrs['placeholder'] = 'Add Contact'

    def get_contact(self):
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

    class Meta:
        model = ActivityGoal
        fields = ('goal_hours', 'employee', 'activity', 'date', 'end_date')

    def __init__(self, *args, **kwargs):
        super(CreateEditActivityGoalForm, self).__init__(*args, **kwargs)
        self.fields['date'].initial = datetime.date.today()
        self.fields['date'].required = True
        self.fields['activity'].required = True

    def clean_goal_hours(self):
        goal_hours = self.cleaned_data['goal_hours']
        if goal_hours <= 0:
            raise forms.ValidationError("Goal Hours must be greater than 0.")
        return goal_hours

class CreateEditContactForm(forms.ModelForm):
    EMPLOYEE_CHOICES = [(None, '-')] + [(u.pk, '%s, %s'%(u.last_name, u.first_name)) \
        for u in Group.objects.get(id=1).user_set.filter(
            is_active=True).order_by('last_name', 'first_name')]

    class Meta:
        model = Contact
        fields = ('lead_source', 'first_name', 'last_name',
            'salutation', 'first_name', 'last_name', 'title', 
            'business', 'business_department', 'assistant',
            'assistant_name', 'assistant_phone', 'assistant_email',
            'email', 'office_phone', 'mobile_phone', 'home_phone', 
            'other_phone', 'fax', 'mailing_street', 'mailing_city',
            'mailing_state', 'mailing_postalcode', 'mailing_mailstop',
            'mailing_country', 'other_street', 'other_city', 
            'other_state', 'other_postalcode', 'other_mailstop',
            'other_country', 'has_opted_out_of_email', 
            'has_opted_out_of_fax', 'do_not_call')

    def __init__(self, *args, **kwargs):        
        super(CreateEditContactForm, self).__init__(*args, **kwargs)
        self.fields['lead_source'].choices = self.EMPLOYEE_CHOICES

class AddContactNoteForm(forms.ModelForm):

    class Meta:
        model = ContactNote
        fields = ('text', 'contact', 'author')

    def __init__(self, *args, **kwargs):
        super(AddContactNoteForm, self).__init__(*args, **kwargs)
        self.fields['text'].label = ''
        self.fields['text'].widget.attrs['rows'] = 6
        self.fields['author'].widget = widgets.HiddenInput()
        self.fields['contact'].widget = widgets.HiddenInput()

class CreateEditLeadForm(forms.ModelForm):
    EMPLOYEE_CHOICES = [(None, '-')] + [(u.pk, '%s, %s'%(u.last_name, u.first_name)) \
        for u in Group.objects.get(id=1).user_set.filter(
            is_active=True).order_by('last_name', 'first_name')]

    class Meta:
        model = Lead
        fields = ('title', 'status', 'lead_source', 'aac_poc',
            'primary_contact', 'business_placeholder',
            'created_by', 'last_editor')

    def __init__(self, *args, **kwargs):        
        super(CreateEditLeadForm, self).__init__(*args, **kwargs)
        self.fields['aac_poc'].choices = self.EMPLOYEE_CHOICES
        self.fields['lead_source'].choices = self.EMPLOYEE_CHOICES
        self.fields['created_by'].widget = widgets.HiddenInput()
        self.fields['last_editor'].widget = widgets.HiddenInput()

        self.fields['primary_contact'].widget = selectable.AutoCompleteSelectWidget(ContactLookup)
        self.fields['primary_contact'].widget.attrs['placeholder'] = 'Find Contact'
        self.fields['business_placeholder'].widget = selectable.AutoCompleteSelectWidget(BusinessLookup)
        self.fields['business_placeholder'].widget.attrs['placeholder'] = 'Find Business'

    def clean(self):
        super(CreateEditLeadForm, self).clean()
        primary_contact = self.cleaned_data.get('primary_contact', None)
        business = self.cleaned_data.get('business_placeholder', None)
        if primary_contact is None and business is None:
            raise forms.ValidationError('You must select either a Primary Contact (preferred) or a Business.')
        return self.cleaned_data

class AddLeadNoteForm(forms.ModelForm):

    class Meta:
        model = LeadNote
        fields = ('text', 'lead', 'author')

    def __init__(self, *args, **kwargs):
        super(AddLeadNoteForm, self).__init__(*args, **kwargs)
        self.fields['text'].label = ''
        self.fields['text'].widget.attrs['rows'] = 6
        self.fields['author'].widget = widgets.HiddenInput()
        self.fields['lead'].widget = widgets.HiddenInput()

class AddDistinguishingValueChallenegeForm(forms.ModelForm):

    class Meta:
        model = DistinguishingValueChallenge
        fields = ('probing_question', 'order', 'short_name', 'description', 
            'longevity', 'start_date', 'steps', 'results', 'due', 
            'due_date', 'cost', 'confirm_resources', 'resources_notes', 
            'benefits_begin', 'date_benefits_begin', 'confirm', 
            'confirm_notes', 'commitment', 'commitment_notes', 'closed')


class AddTemplateDifferentiatingValuesForm(forms.Form):
    template_dvs = forms.MultipleChoiceField(
        required=True, widget=forms.CheckboxSelectMultiple,
        label='Select at least one Template Differenitating Values')

    def __init__(self, *args, **kwargs):
        super(AddTemplateDifferentiatingValuesForm, self).__init__(*args, **kwargs)
        TEMPLATE_DV_CHOICES = [(tdv.id, '%s: %s' % (tdv.short_name, 
            tdv.probing_question)) for tdv in 
            TemplateDifferentiatingValue.objects.all()]
        self.fields['template_dvs'].choices = TEMPLATE_DV_CHOICES

class CreateEditTemplateDVForm(forms.ModelForm):

    class Meta:
        model = TemplateDifferentiatingValue
        fields = ('short_name', 'probing_question')

class CreateEditDVCostItem(forms.ModelForm):

    class Meta:
        model = DVCostItem
        fields = ('dv', 'description', 'details', 'cost', 'man_hours', 'rate')

class CreateEditOpportunity(forms.ModelForm):
    # project = selectable.AutoCompleteSelectField(ProjectLookup, required=False)
    class Meta:
        model = Opportunity
        fields = ('title', 'lead', 'differentiating_value', 'proposal',
            'proposal_status', 'project')

    def __init__(self, *args, **kwargs):
        super(CreateEditOpportunity, self).__init__(*args, **kwargs)
        self.fields['lead'].widget = widgets.HiddenInput()
        self.fields['project'].widget = selectable.widgets.AutoCompleteSelectMultipleWidget(ProjectLookup)
