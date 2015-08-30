from django.core.mail import send_mail, EmailMultiAlternatives
from django.contrib.auth.models import Group

def business_new_note(note, url):
    to_addys = ['browne.danielc@gmail.com', 
                # note.author.email,
                note.business.account_owner.email]
    subject = '[FirmBase] New Note on Business - %s' % (note.business.name)
    text_content = '%s added a new note to %s at %s: "%s."  You can view the business here: %s.' % (
        note.author, note.business.name, note.created_at, note.text, url)
    html_content = '%s added a new note to <a href="%s">%s</a> at %s:<p><em>%s</em>' % (
        note.author, url, note.business.name, note.created_at, note.text)
    msg = EmailMultiAlternatives(subject, text_content, 'firmbase@firmbase.aacengineering.com', to_addys)
    msg.attach_alternative(html_content, "text/html")
    msg.send()

def contact_new_note(note, url):
    to_addys = ['browne.danielc@gmail.com', 
                # note.author.email,
                note.contact.lead_source.email]
    subject = '[FirmBase] New Note on Contact - %s' % (note.contact.name)
    text_content = '%s added a new note to %s at %s: "%s."  You can view the contact here: %s.' % (
        note.author, note.contact.name, note.created_at, note.text, url)
    html_content = '%s added a new note to <a href="%s">%s</a> at %s:<p><em>%s</em>' % (
        note.author, url, note.contact.name, note.created_at, note.text)
    msg = EmailMultiAlternatives(subject, text_content, 'firmbase@firmbase.aacengineering.com', to_addys)
    msg.attach_alternative(html_content, "text/html")
    msg.send()

def contract_new_note(note, url):
    to_addys = [u.email for u in Group.objects.get(id=5).user_set.all()]
    subject = '[FirmBase] New Note on Contract - %s' % (note.contract.name)
    text_content = '%s added a new note to %s at %s: "%s."  You can view the contract here: %s.' % (
        note.author, note.contract.name, note.created_at, note.text, url)
    html_content = '%s added a new note to <a href="%s">%s</a> at %s:<p><em>%s</em>' % (
        note.author, url, note.contract.name, note.created_at, note.text)
    msg = EmailMultiAlternatives(subject, text_content, 'firmbase@firmbase.aacengineering.com', to_addys)
    msg.attach_alternative(html_content, "text/html")
    
    # msg.send()

def lead_new_note(note, url):
    if note.lead.aac_poc == note.author:
        return
    
    to_addys = ['browne.danielc@gmail.com', 
                # note.author.email,
                note.lead.aac_poc.email]
    subject = '[FirmBase] New Note on Lead - %s' % (note.lead.title)
    text_content = '%s added a new note to %s at %s: "%s."  You can view the lead here: %s.' % (
        note.author, note.lead.title, note.created_at, note.text, url)
    html_content = '%s added a new note to <a href="%s">%s</a> at %s:<p><em>%s</em>' % (
        note.author, url, note.lead.title, note.created_at, note.text)
    msg = EmailMultiAlternatives(subject, text_content, 'firmbase@firmbase.aacengineering.com', to_addys)
    msg.attach_alternative(html_content, "text/html")
    msg.send()