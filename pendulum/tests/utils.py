from datetime import date

VALID_USER, VALID_PASSWORD = 'testuser', 'password'

def ffd(date):
    """
    Form-friendly date formatter
    """
    return date.strftime('%Y-%m-%d %H:%M')
