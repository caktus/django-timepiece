from django.core.mail import send_mail, EmailMultiAlternatives

def business_new_note(note, url):
    to_addys = ['browne.danielc@gmail.com', 
                note.author.email,
                note.business.account_owner.email]
    subject = '[FirmBase] New Note on Business - %s' % (note.business.name)
    text_content = '%s added a new note to %s at %s: "%s."  You can view the business here: %s.' % (
        note.author, note.business.name, note.created_at, note.text, url)
    html_content = '%s added a new note to <a href="%s">%s</a> at %s:<p><em>%s</em>' % (
        note.author, url, note.business.name, note.created_at, note.text)
    msg = EmailMultiAlternatives(subject, text_content, 'firmbase@project-toolbox.com', to_addys)
    msg.attach_alternative(html_content, "text/html")
    msg.send()
