from django.contrib.sites.models import Site
from datetime import date, datetime, timedelta
import calendar

def determine_period(the_date=date.today(), delta=0):
    """
    Determine the start and end date for an accounting period.  If a date
    is passed in, that date will be used to determine the accounting period.
    If no date is passed in, the current date will be used.
    """
    delta = int(delta)

    try:
        # attempt to get the configuration for the current site
        site = Site.objects.get_current()
        config = site.pendulumconfiguration
    except:
        raise Exception('Please configure Pendulum for %s!' % site)

    if config.is_monthly and (config.month_start >= 1 and config.month_start <= 31):
        if config.month_start == 1:
            # if the periods start on the first of the month, just use the first
            # and last days of each month for the period
            if delta > 0:
                diff = the_date.month - delta
                if diff < 1:
                    # determine how many years to go back
                    years = abs(diff / 12)

                    # determine how many months to go back
                    months = delta - (years * 12)
                    if months == the_date.month:
                        # don't give an invalid month
                        months = -1
                        years += 1

                    # now set the year and month
                    year, month = the_date.year - years, the_date.month - months
                else:
                    year, month = the_date.year, diff
            else:
                year, month = the_date.year, the_date.month

            num_days = calendar.monthrange(year, month)[1]
            sy, sm, sd = year, month, 1
            ey, em, ed = year, month, num_days
        else:
            # if the periods don't start on the first of the month, try to
            # figure out which days are required

            sy, sm, sd = the_date.year, the_date.month, config.month_start

            # now take the delta into account
            if delta > 0:
                diff = sm - delta
                if diff < 1:
                    # determine how many years to go back
                    years = abs(diff / 12)

                    # determine how many months to go back
                    months = delta - (years * 12)
                    if months == sm:
                        # don't give an invalid month
                        months = -1
                        years += 1

                    # now set the year and month
                    sy, sm = sy - years, sm - months
                else:
                    sm = diff

            if the_date.day >= config.month_start:
                # if we are already into the period that began this month
                if sm == 12:
                    # see if the period spans into the next year
                    ey, em = sy + 1, 1
                else:
                    # if not, just add a month and subtract a day
                    ey, em = sy, em + 1
            else:
                # if we are in the period that ends this month
                if sm == 1:
                    # and we're in January, set the start to last december
                    sy, sm = sy - 1, 12
                    ey, em = sy + 1, 1
                else:
                    # otherwise, just keep it simple
                    sm = sm - 1
                    ey, em = sy, sm + 1

            ed = sd - 1

            # this should handle funky situations where a period begins on the
            # 31st of a month or whatever...
            num_days = calendar.monthrange(ey, em)[1]
            if ed > num_days:
                ed = num_days

    elif config.install_date and config.period_length:
        # if we have periods with a set number of days...
        # find out how many days have passed since the installation date
        diff = the_date - config.install_date

        # find out how many days are left over after dividing the number of days
        # since installation by the length of the period
        days_into_period = diff.days % config.period_length

        # determine the start date of the period
        start = the_date - timedelta(days=days_into_period)

        # now take into account the delta
        if delta > 0:
            start = start - timedelta(days=(delta * config.period_length))
            end = start + timedelta(days=config.period_length - 1)
        else:
            # determine the end date of the period
            end = the_date + timedelta(days=(config.period_length - days_into_period - 1))

        sy, sm, sd = start.year, start.month, start.day
        ey, em, ed = end.year, end.month, end.day
    else:
        raise Exception('Invalid Pendulum configuration for %s' % site)

    start_date = datetime(sy, sm, sd, 0, 0, 0)
    end_date = datetime(ey, em, ed, 23, 59, 59)

    return (start_date, end_date)
