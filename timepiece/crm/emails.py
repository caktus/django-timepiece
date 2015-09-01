from django.contrib.auth.models import Group
from django.core.mail import send_mail, EmailMultiAlternatives
from django.contrib.auth.models import User

def new_pto(pto, url, approve_url, deny_url):
    to_addys1 = ['browne.danielc@gmail.com',
                User.objects.get(id=5).email]

    to_addys2 = ['browne.danielc@gmail.com',
                pto.user_profile.user.email]

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
                          '<a href="https://firmbase.aacengineering.com' + url + '">PTO Request</a>'
    
    html_content1 = html_content + \
                        ' | <a href="https://firmbase.aacengineering.com' + approve_url + '">Approve</a>' + \
                        ' | <a href="https://firmbase.aacengineering.com' + deny_url + '">Deny</a>' + \
                      '</dd>' + \
                    '</dl>'
    html_content2 = html_content + \
                      '</dd>' + \
                    '</dl>'

        
    msg1 = EmailMultiAlternatives(subject, text_content, 'firmbase@firmbase.aacengineering.com', to_addys1)
    msg1.attach_alternative(html_content1, "text/html")
    msg1.send()

    msg2 = EmailMultiAlternatives(subject, text_content, 'firmbase@firmbase.aacengineering.com', to_addys2)
    msg2.attach_alternative(html_content2, "text/html")
    msg2.send()
    

def approved_pto(pto, url):
    to_addys = ['browne.danielc@gmail.com']

    subject = '[FirmBase] Time Off Request Approved'
    text_content = 'Time Off request (' +  url + ') approved.'
    html_content = '<dl>' + \
                      '<dt>Requested by</dt><dd>' + str(pto.user_profile.user) + '</dd>' + \
                      '<dt>Type</dt><dd>' + ('Paid Time Off' if pto.pto else 'Unpaid Time Off') + '</dd>' + \
                      '<dt>Date Submitted</dt><dd>' + pto.request_date.strftime('%F') + '</dd>' + \
                      '<dt>Time Off Start Date</dt><dd>' + pto.pto_start_date.strftime('%F') + '</dd>' + \
                      '<dt>Time Off End Date</dt><dd>' + pto.pto_end_date.strftime('%F') + '</dd>' + \
                      '<dt>Number of Hours</dt><dd>' + str(pto.amount) + '</dd>' + \
                      '<dt>Reasons</dt><dd>' + pto.comment + '</dd>' + \
                      '<dt>Approver</dt><dd>' + str(pto.approver)  + '</dd>' + \
                      '<dt>Approval Date</dt><dd>' + str(pto.approval_date)  + '</dd>' + \
                      '<dt>Approver Comment</dt><dd>' + pto.approver_comment  + '</dd>' + \
                      '<dt>Links</dt>' + \
                        '<dd>' + \
                          '<a href="https://firmbase.aacengineering.com' + url + '">PTO Request</a>'+ \
                      '</dd>' + \
                    '</dl>'
        
    msg = EmailMultiAlternatives(subject, text_content, 'firmbase@firmbase.aacengineering.com', to_addys)
    msg.attach_alternative(html_content, "text/html")
    msg.send()

def denied_pto(pto, url):
    to_addys = ['browne.danielc@gmail.com']

    subject = '[FirmBase] Time Off Request Denied'
    text_content = 'Time Off request (' +  url + ') denied.'
    html_content = '<dl>' + \
                      '<dt>Requested by</dt><dd>' + str(pto.user_profile.user) + '</dd>' + \
                      '<dt>Type</dt><dd>' + ('Paid Time Off' if pto.pto else 'Unpaid Time Off') + '</dd>' + \
                      '<dt>Date Submitted</dt><dd>' + pto.request_date.strftime('%F') + '</dd>' + \
                      '<dt>Time Off Start Date</dt><dd>' + pto.pto_start_date.strftime('%F') + '</dd>' + \
                      '<dt>Time Off End Date</dt><dd>' + pto.pto_end_date.strftime('%F') + '</dd>' + \
                      '<dt>Number of Hours</dt><dd>' + str(pto.amount) + '</dd>' + \
                      '<dt>Reasons</dt><dd>' + pto.comment + '</dd>' + \
                      '<dt>Reviewer</dt><dd>' + str(pto.approver)  + '</dd>' + \
                      '<dt>Denied Date</dt><dd>' + str(pto.approval_date)  + '</dd>' + \
                      '<dt>Denied Comment</dt><dd>' + pto.approver_comment  + '</dd>' + \
                      '<dt>Links</dt>' + \
                        '<dd>' + \
                          '<a href="https://firmbase.aacengineering.com' + url + '">PTO Request</a>'+ \
                      '</dd>' + \
                    '</dl>'
        
    msg = EmailMultiAlternatives(subject, text_content, 'firmbase@firmbase.aacengineering.com', to_addys)
    msg.attach_alternative(html_content, "text/html")
    msg.send()

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
    msg = EmailMultiAlternatives(subject, text_content, 'firmbase@firmbase.aacengineering.com', to_addys)
    msg.attach_alternative(html_content, "text/html")
    msg.send()
