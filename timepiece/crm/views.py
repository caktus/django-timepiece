import datetime
from dateutil.relativedelta import relativedelta
import urllib

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse, reverse_lazy, resolve
from django.db import transaction
from django.db.models import Sum, Q
from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import (CreateView, DeleteView, DetailView,
        TemplateView, UpdateView, View)

from timepiece import utils
from timepiece.forms import YearMonthForm, UserYearMonthForm, SearchForm
from timepiece.templatetags.timepiece_tags import seconds_to_hours
from timepiece.utils.csv import CSVViewMixin
from timepiece.utils.mixins import (CommitOnSuccessMixin,
        PermissionsRequiredMixin)

from timepiece.crm.forms import BusinessForm, ProjectForm, UserProfileForm,\
        ProjectRelationshipForm, SelectProjectForm, EditUserForm,\
        CreateUserForm, SelectUserForm, UserForm, ProjectSearchForm,\
        DeleteForm, QuickSearchForm
from timepiece.crm.models import Business, Project, ProjectRelationship,\
        UserProfile
from timepiece.crm.utils import grouped_totals
from timepiece.entries.models import Entry


@permission_required('entries.view_payroll_summary')
def reject_user_timesheet(request, user_id):
    """
    This allows admins to reject all entries, instead of just one
    """
    form = YearMonthForm(request.GET or request.POST)
    user = User.objects.get(pk=user_id)
    if form.is_valid():
        from_date, to_date = form.save()
        entries = Entry.no_join.filter(status=Entry.VERIFIED, user=user,
            start_time__gte=from_date, end_time__lte=to_date)
        if request.POST.get('yes'):
            if entries.exists():
                count = entries.count()
                entries.update(status=Entry.UNVERIFIED)
                msg = 'You have rejected %d previously verified entries.' \
                    % count
            else:
                msg = 'There are no verified entries to reject.'
            messages.info(request, msg)
        else:
            return render(request, 'timepiece/user/timesheet/reject.html', {
                'date': from_date,
                'timesheet_user': user
            })
    else:
        msg = 'You must provide a month and year for entries to be rejected.'
        messages.error(request, msg)

    url = reverse('view_user_timesheet', args=(user_id,))
    return HttpResponseRedirect(url)


class ProjectTimesheet(DetailView):
    template_name = 'timepiece/project/timesheet.html'
    model = Project
    context_object_name = 'project'
    pk_url_kwarg = 'project_id'

    # FIXME: this permission doesn't seem to exist
    @method_decorator(permission_required('entries.view_project_time_sheet'))
    def dispatch(self, *args, **kwargs):
        return super(ProjectTimesheet, self).dispatch(*args, **kwargs)

    def get(self, *args, **kwargs):
        if 'csv' in self.request.GET:
            request_get = self.request.GET.copy()
            request_get.pop('csv')
            return_url = reverse('view_project_timesheet_csv',
                                 args=(self.get_object().pk,))
            return_url += '?%s' % urllib.urlencode(request_get)
            return redirect(return_url)
        return super(ProjectTimesheet, self).get(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ProjectTimesheet, self).get_context_data(**kwargs)
        project = self.object
        year_month_form = YearMonthForm(self.request.GET or None)
        if self.request.GET and year_month_form.is_valid():
            from_date, to_date = year_month_form.save()
        else:
            date = utils.add_timezone(datetime.datetime.today())
            from_date = utils.get_month_start(date).date()
            to_date = from_date + relativedelta(months=1)
        entries_qs = Entry.objects
        entries_qs = entries_qs.timespan(from_date, span='month').filter(
            project=project
        )
        extra_values = ('start_time', 'end_time', 'comments', 'seconds_paused',
                'id', 'location__name', 'project__name', 'activity__name',
                'status')
        month_entries = entries_qs.date_trunc('month', extra_values)
        total = entries_qs.aggregate(hours=Sum('hours'))['hours']
        user_entries = entries_qs.order_by().values(
            'user__first_name', 'user__last_name').annotate(
            sum=Sum('hours')).order_by('-sum'
        )
        activity_entries = entries_qs.order_by().values(
            'activity__name').annotate(
            sum=Sum('hours')).order_by('-sum'
        )
        context.update({
            'project': project,
            'year_month_form': year_month_form,
            'from_date': from_date,
            'to_date': to_date - relativedelta(days=1),
            'entries': month_entries,
            'total': total,
            'user_entries': user_entries,
            'activity_entries': activity_entries,
        })
        return context


class ProjectTimesheetCSV(CSVViewMixin, ProjectTimesheet):

    def get_filename(self, context):
        project = self.object.name
        to_date_str = context['to_date'].strftime('%m-%d-%Y')
        return 'Project_timesheet {0} {1}'.format(project, to_date_str)

    def convert_context_to_csv(self, context):
        rows = []
        rows.append([
            'Date',
            'User',
            'Activity',
            'Location',
            'Time In',
            'Time Out',
            'Breaks',
            'Hours',
        ])
        for entry in context['entries']:
            data = [
                entry['start_time'].strftime('%x'),
                entry['user__first_name'] + ' ' + entry['user__last_name'],
                entry['activity__name'],
                entry['location__name'],
                entry['start_time'].strftime('%X'),
                entry['end_time'].strftime('%X'),
                seconds_to_hours(entry['seconds_paused']),
                entry['hours'],
            ]
            rows.append(data)
        total = context['total']
        rows.append(('', '', '', '', '', '', 'Total:', total))
        return rows


@login_required
def view_user_timesheet(request, user_id, active_tab):
    # User can only view their own time sheet unless they have a permission.
    user = get_object_or_404(User, pk=user_id)
    has_perm = request.user.has_perm('entries.view_entry_summary')
    if not (has_perm or user.pk == request.user.pk):
        return HttpResponseForbidden('Forbidden')

    FormClass = UserYearMonthForm if has_perm else YearMonthForm
    form = FormClass(request.GET or None)
    if form.is_valid():
        if has_perm:
            from_date, to_date, form_user = form.save()
            if form_user and request.GET.get('yearmonth', None):
                # Redirect to form_user's time sheet.
                # Do not use request.GET in urlencode to prevent redirect
                # loop caused by yearmonth parameter.
                url = reverse('view_user_timesheet', args=(form_user.pk,))
                request_data = {
                    'month': from_date.month,
                    'year': from_date.year,
                    'user': form_user.pk,  # Keep so that user appears in form.
                }
                url += '?{0}'.format(urllib.urlencode(request_data))
                return HttpResponseRedirect(url)
        else:  # User must be viewing their own time sheet; no redirect needed.
            from_date, to_date = form.save()
        from_date = utils.add_timezone(from_date)
        to_date = utils.add_timezone(to_date)
    else:
        # Default to showing this month.
        from_date = utils.get_month_start()
        to_date = from_date + relativedelta(months=1)

    entries_qs = Entry.objects.filter(user=user)
    month_qs = entries_qs.timespan(from_date, span='month')
    extra_values = ('start_time', 'end_time', 'comments', 'seconds_paused',
            'id', 'location__name', 'project__name', 'activity__name',
            'status')
    month_entries = month_qs.date_trunc('month', extra_values)
    # For grouped entries, back date up to the start of the week.
    first_week = utils.get_week_start(from_date)
    month_week = first_week + relativedelta(weeks=1)
    grouped_qs = entries_qs.timespan(first_week, to_date=to_date)
    intersection = grouped_qs.filter(start_time__lt=month_week,
        start_time__gte=from_date)
    # If the month of the first week starts in the previous
    # month and we dont have entries in that previous ISO
    # week, then update the first week to start at the first
    # of the actual month
    if not intersection and first_week.month < from_date.month:
        grouped_qs = entries_qs.timespan(from_date, to_date=to_date)
    totals =grouped_totals(grouped_qs) if month_entries else ''
    project_entries = month_qs.order_by().values(
        'project__name').annotate(sum=Sum('hours')).order_by('-sum')
    summary = Entry.summary(user, from_date, to_date)

    show_approve = show_verify = False
    can_change = request.user.has_perm('entries.change_entry')
    can_approve = request.user.has_perm('entries.approve_timesheet')
    if can_change or can_approve or user == request.user:
        statuses = list(month_qs.values_list('status', flat=True))
        total_statuses = len(statuses)
        unverified_count = statuses.count(Entry.UNVERIFIED)
        verified_count = statuses.count(Entry.VERIFIED)
        approved_count = statuses.count(Entry.APPROVED)
    if can_change or user == request.user:
        show_verify = unverified_count != 0
    if can_approve:
        show_approve = verified_count + approved_count == total_statuses \
                and verified_count > 0 and total_statuses != 0

    return render(request, 'timepiece/user/timesheet/view.html', {
        'active_tab': active_tab or 'overview',
        'year_month_form': form,
        'from_date': from_date,
        'to_date': to_date - relativedelta(days=1),
        'show_verify': show_verify,
        'show_approve': show_approve,
        'timesheet_user': user,
        'entries': month_entries,
        'grouped_totals': totals,
        'project_entries': project_entries,
        'summary': summary,
    })


@login_required
def change_user_timesheet(request, user_id, action):
    user = get_object_or_404(User, pk=user_id)
    admin_verify = request.user.has_perm('entries.view_entry_summary')
    perm = True

    if not admin_verify and action == 'verify' and user != request.user:
        perm = False
    if not admin_verify and action == 'approve':
        perm = False

    if not perm:
        return HttpResponseForbidden('Forbidden: You cannot {0} this '
                'timesheet.'.format(action))

    try:
        from_date = request.GET.get('from_date')
        from_date = utils.add_timezone(
            datetime.datetime.strptime(from_date, '%Y-%m-%d'))
    except (ValueError, OverflowError, KeyError):
        raise Http404
    to_date = from_date + relativedelta(months=1)
    entries = Entry.no_join.filter(user=user_id,
                                   end_time__gte=from_date,
                                   end_time__lt=to_date)
    active_entries = Entry.no_join.filter(
        user=user_id,
        start_time__lt=to_date,
        end_time=None,
        status=Entry.UNVERIFIED,
    )
    filter_status = {
        'verify': Entry.UNVERIFIED,
        'approve': Entry.VERIFIED,
    }
    entries = entries.filter(status=filter_status[action])

    return_url = reverse('view_user_timesheet', args=(user_id,))
    return_url += '?%s' % urllib.urlencode({
        'year': from_date.year,
        'month': from_date.month,
    })
    if active_entries:
        msg = 'You cannot verify/approve this timesheet while the user {0} ' \
            'has an active entry. Please have them close any active ' \
            'entries.'.format(user.get_name_or_username())
        messages.error(request, msg)
        return redirect(return_url)
    if request.POST.get('do_action') == 'Yes':
        update_status = {
            'verify': 'verified',
            'approve': 'approved',
        }
        entries.update(status=update_status[action])
        messages.info(request,
            'Your entries have been %s' % update_status[action])
        return redirect(return_url)
    hours = entries.all().aggregate(s=Sum('hours'))['s']
    if not hours:
        msg = 'You cannot verify/approve a timesheet with no hours'
        messages.error(request, msg)
        return redirect(return_url)
    return render(request, 'timepiece/user/timesheet/change.html', {
        'action': action,
        'timesheet_user': user,
        'from_date': from_date,
        'to_date': to_date - relativedelta(days=1),
        'return_url': return_url,
        'hours': hours,
    })


@permission_required('crm.view_business')
def list_businesses(request):
    form = SearchForm(request.GET)
    businesses = Business.objects.all()
    if form.is_valid() and 'search' in request.GET:
        search = form.cleaned_data['search']
        searchQ = Q(name__icontains=search) | Q(description__icontains=search)
        businesses = businesses.filter(searchQ)
        if businesses.count() == 1:
            url = request.REQUEST.get('next',
                    reverse('view_business', args=(businesses[0].pk,)))
            return HttpResponseRedirect(url)
    return render(request, 'timepiece/business/list.html', {
        'form': form,
        'businesses': businesses,
    })


class ViewBusiness(PermissionsRequiredMixin, DetailView):
    model = Business
    pk_url_kwarg = 'business_id'
    template_name = 'timepiece/business/view.html'
    permissions = ['crm.view_business']


@permission_required('crm.add_business')
def create_edit_business(request, business_id=None):
    business = None
    if business_id:
        business = get_object_or_404(Business, pk=business_id)
    form = BusinessForm(request.POST or None,
            instance=business)
    if form.is_valid():
        business = form.save()
        url = reverse('view_business', args=(business.pk,))
        return HttpResponseRedirect(url)
    return render(request, 'timepiece/business/create_edit.html', {
        'business': business,
        'business_form': form,
    })


@permission_required('auth.view_user')
def list_users(request):
    form = SearchForm(request.GET)
    users = User.objects.all().order_by('last_name')
    if form.is_valid() and 'search' in request.GET:
        search = form.cleaned_data['search']
        users = users.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )
        if users.count() == 1:
            url = request.REQUEST.get('next',
                    reverse('view_user', args=(users[0].id,)))
            return HttpResponseRedirect(url)
    return render(request, 'timepiece/user/list.html', {
        'form': form,
        'users': users.select_related(),
    })


class ViewUser(PermissionsRequiredMixin, CommitOnSuccessMixin, DetailView):
    model = User
    pk_url_kwarg = 'user_id'
    template_name = 'timepiece/user/view.html'
    permissions = ['auth.view_user']

    def get_context_data(self, **kwargs):
        context = super(ViewUser, self).get_context_data(**kwargs)
        context.update({
            'add_project_form': SelectProjectForm(),
        })
        return context


@permission_required('auth.add_user')
@permission_required('auth.change_user')
def create_edit_user(request, user_id=None):
    user = get_object_or_404(User, pk=user_id) if user_id else None
    form = EditUserForm(request.POST or None, instance=user)
    if form.is_valid():
        user = form.save()
        url = request.REQUEST.get('next',
                reverse('view_user', args=(user.pk,)))
        return HttpResponseRedirect(url)
    return render(request, 'timepiece/user/create_edit.html', {
        'user': user,
        'form': form,
    })


@permission_required('crm.view_project')
def list_projects(request):
    form = ProjectSearchForm(request.GET or None)
    if form.is_valid() and ('search' in request.GET or 'status' in
            request.GET):
        search, status = form.save()
        query = Q(name__icontains=search) | Q(description__icontains=search)
        projects = Project.objects.filter(query)
        projects = projects.filter(status=status) if status else projects
        if projects.count() == 1:
            url = request.REQUEST.get('next',
                    reverse('view_project', args=(projects.get().id,)))
            return HttpResponseRedirect(url)
    else:
        projects = Project.objects.all()

    return render(request, 'timepiece/project/list.html', {
        'form': form,
        'projects': projects.select_related('business'),
    })


class ViewProject(PermissionsRequiredMixin, CommitOnSuccessMixin, DetailView):
    model = Project
    pk_url_kwarg = 'project_id'
    template_name = 'timepiece/project/view.html'
    permissions = ['crm.view_project']

    def get_context_data(self, **kwargs):
        context = super(ViewProject, self).get_context_data(**kwargs)
        context.update({
            'add_user_form': SelectUserForm(),
        })
        return context


@csrf_exempt
@require_POST
@permission_required('crm.add_projectrelationship')
@transaction.commit_on_success
def create_relationship(request):
    user_id = request.REQUEST.get('user_id', None)
    project_id = request.REQUEST.get('project_id', None)
    url = reverse('dashboard')  # Default if nothing else comes up

    project = None
    if project_id:
        project = get_object_or_404(Project, pk=project_id)
        url = reverse('view_project', args=(project_id,))
    else:  # Adding a user to a specific project
        project_form = SelectProjectForm(request.POST)
        if project_form.is_valid():
            project = project_form.save()

    user = None
    if user_id:
        user = get_object_or_404(User, pk=user_id)
        url = reverse('view_user', args=(user_id,))
    else:  # Adding a project to a specific user
        user_form = SelectUserForm(request.POST)
        if user_form.is_valid():
            user = user_form.save()

    if user and project:
        ProjectRelationship.objects.get_or_create(
                user=user, project=project)

    url = request.REQUEST.get('next', url)
    return HttpResponseRedirect(url)


@csrf_exempt
@permission_required('crm.delete_projectrelationship')
@transaction.commit_on_success
def delete_relationship(request):
    user_id = request.REQUEST.get('user_id', None)
    project_id = request.REQUEST.get('project_id', None)
    rel = get_object_or_404(ProjectRelationship,
            user__id=user_id, project__id=project_id)
    if request.method == 'POST':
        rel.delete()
        url = request.REQUEST.get('next',
                reverse('view_project', args=(rel.project.pk,)))
        return HttpResponseRedirect(url)
    return render(request, 'timepiece/relationship/delete.html', {
        'user': rel.user,
        'project': rel.project,
    })


@permission_required('crm.change_projectrelationship')
@transaction.commit_on_success
def edit_relationship(request):
    user_id = request.REQUEST.get('user_id', None)
    project_id = request.REQUEST.get('project_id', None)
    rel = get_object_or_404(ProjectRelationship,
            user__id=user_id, project__id=project_id)
    data = request.POST if request.method == 'POST' else None
    form = ProjectRelationshipForm(data, instance=rel)
    if request.method == 'POST' and form.is_valid():
        rel = form.save()
        url = request.REQUEST.get('next',
                reverse('view_project', args=(project_id,)))
        return HttpResponseRedirect(url)
    return render(request, 'timepiece/relationship/edit.html', {
        'user': rel.user,
        'project': rel.project,
        'relationship_form': form,
    })


@permission_required('crm.add_project')
@permission_required('crm.change_project')
def create_edit_project(request, project_id=None):
    project = None
    if project_id:
        project = get_object_or_404(Project, pk=project_id)
    form = ProjectForm(request.POST or None, instance=project)
    if request.POST and form.is_valid():
        project = form.save()
        project.save()
        url = request.REQUEST.get('next',
                reverse('view_project', args=(project.id,)))
        return HttpResponseRedirect(url)
    return render(request, 'timepiece/project/create_edit.html', {
        'project': project,
        'project_form': form,
    })


@login_required
def edit_settings(request):
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=user)
        profile_form = UserProfileForm(
                request.POST, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.info(request, 'Your settings have been updated.')
            next_url = request.REQUEST.get('next', None)
            if next_url:
                try:
                    resolve(next_url)
                except Http404:
                    next_url = None
            next_url = next_url or reverse('dashboard')
            return HttpResponseRedirect(next_url)
    else:
        profile_form = UserProfileForm(instance=profile)
        user_form = UserForm(instance=user)
    return render(request, 'timepiece/user/settings.html', {
        'profile_form': profile_form,
        'user_form': user_form,
    })


class DeleteUser(PermissionsRequiredMixin, DeleteView):
    model = User
    success_url = reverse_lazy('list_users')
    permissions = ('auth.add_user', 'auth.change_user',)
    pk_url_kwarg = 'user_id'
    template_name = 'timepiece/delete_object.html'


class DeleteBusiness(PermissionsRequiredMixin, DeleteView):
    model = Business
    success_url = reverse_lazy('list_businesses')
    permissions = ('crm.add_business',)
    pk_url_kwarg = 'business_id'
    template_name = 'timepiece/delete_object.html'


class DeleteProject(PermissionsRequiredMixin, DeleteView):
    model = Project
    success_url = reverse_lazy('list_projects')
    permissions = ('crm.add_project', 'crm.change_project',)
    pk_url_kwarg = 'project_id'
    template_name = 'timepiece/delete_object.html'


@login_required
def search(request):
    form = QuickSearchForm(request.GET or None)
    if form.is_valid():
        return HttpResponseRedirect(form.save())
    return render(request, 'timepiece/search_results.html', {
        'form': form,
    })
