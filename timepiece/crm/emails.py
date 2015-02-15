from django.contrib.auth.models import Group
from django.core.mail import send_mail, EmailMultiAlternatives
from django.contrib.auth.models import User

def new_pto(pto, url, approve_url, deny_url):
    to_addys = ['browne.danielc@gmail.com',
                pto.user_profile.user.email,
                User.objects.get(id=5).email]
    # for gid in [4, 5]:
    #     for u in Group.objects.get(id=gid).user_set.values():
    #         to_addys.append(u['email'])

    subject = '[FirmBase] New Time Off Request for %s' % (pto.user_profile.user)
    text_content = 'New Time Off request. ' +  url
    html_content = '<dl>' + \
                      '<dt>Requested by</dt><dd>' + str(pto.user_profile.user) + '</dd>' + \
                      '<dt>Type</dt><dd>' + ('Paid Time Off' if pto.pto else 'Unpaid Time Off') + '</dd>' + \
                      '<dt>Date Submitted</dt><dd>' + pto.request_date.strftime('%F') + '</dd>' + \
                      '<dt>Time Off Start Date</dt><dd>' + pto.pto_start_date.strftime('%F') + '</dd>' + \
                      '<dt>Time Off End Date</dt><dd>' + pto.pto_end_date.strftime('%F') + '</dd>' + \
                      '<dt>Number of Hours</dt><dd>' + str(pto.amount) + '</dd>' + \
                      '<dt>Reasons</dt><dd>' + pto.comment + '</dd>' + \
                      '<dt>Links</dt>' + \
                        '<dd>' + \
                          '<a href="https://firmbase.aacengineering.com' + url + '">PTO Request</a>' + \
                          ' | <a href="https://firmbase.aacengineering.com' + approve_url + '">Approve</a>' + \
                          ' | <a href="https://firmbase.aacengineering.com' + deny_url + '">Deny</a>' + \
                        '</dd>' + \
                    '</dl>' # % (str(pto.user_profile.user))
        # pto.request_date.strftime('%F'),
        # pto.pto_start_date.strftime('%F'),
        # pto.pto_end_date.strftime('%F'),
        # pto.amount,
        # pto.comment,
        # url)
    msg = EmailMultiAlternatives(subject, text_content, 'firmbase@project-toolbox.com', to_addys)
    msg.attach_alternative(html_content, "text/html")
    msg.send()
    #msg = send_mail(subject, body, 'firmbase@project-toolbox.com', to_addys, fail_silently=True)

def transition_ticket(transition, it_ticket, url):
    to_addys = ['browne.danielc@gmail.com']
    for group in transition.notify_groups.all():
        for user in group.user_set.all():
            to_addys.append(user.email)
    to_addys.append(it_ticket.submitter.email)
    to_addys.append(it_ticket.created_by.email)
    assignee_email = 'no one'
    if it_ticket.assignee:
        to_addys.append(it_ticket.assignee.email)
        assignee_email = it_ticket.assignee.email

    subject = '[FirmBase] Update to Ticket %s' % (it_ticket.form_id)
    text_content = '%s moved ticket %s from %s to %s. It is now assigned to %s. You can view the ticket at https://firmbase.aacengineering.com%s' % (
        it_ticket.last_user, it_ticket.form_id, transition.start_state.name, transition.end_state.name, assignee_email, url)
    html_content = '%s moved ticket <a href="https://firmbase.aacengineering.com%s">%s</a> from <strong>%s</strong> to <strong>%s</strong>.<br/>It is now assigned to <a href="mailto:%s">%s</a>.' % (
        it_ticket.last_user, url, it_ticket.form_id, transition.start_state.name, transition.end_state.name, assignee_email, assignee_email)
    msg = EmailMultiAlternatives(subject, text_content, 'firmbase@project-toolbox.com', to_addys)
    msg.attach_alternative(html_content, "text/html")
    msg.send()
