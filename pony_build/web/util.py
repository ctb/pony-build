import os.path
import jinja2
import datetime
import math

###

# jinja2 prep

thisdir = os.path.dirname(__file__)
templatesdir = os.path.join(thisdir, 'templates')
templatesdir = os.path.abspath(templatesdir)

loader = jinja2.FileSystemLoader(templatesdir)
env = jinja2.Environment(loader=loader)

###

day_diff = datetime.timedelta(1)
hour_diff = datetime.timedelta(0, 3600)
elevenmin_diff = datetime.timedelta(0, 660)
min_diff = datetime.timedelta(0, 60)

def format_timestamp(t):
    dt = datetime.datetime.fromtimestamp(t)
    now = datetime.datetime.now()
    
    diff = now - dt
    minutesSince = int(math.floor(diff.seconds / 60))

    if diff > day_diff:
        return dt.strftime("%A, %d %B %Y, %I:%M %p")
    elif diff > hour_diff:
        timeSince = (minutesSince / 60) + 1
        if timeSince == 24:
            timeSince = "a day"
        else:
            timeSince = str(timeSince) + " hours"
        return "less than " + timeSince + " ago " + dt.strftime("(%I:%M %p)")
    elif diff > elevenmin_diff:
        timeSince = ((minutesSince / 10) + 1 ) * 10
        if timeSince == 60:
            timeSince = "an hour"
        else:
            timeSince = str(timeSince) + " minutes"
        return "less than " + timeSince + " ago " + dt.strftime("(%I:%M %p)")

    return str(minutesSince) + " minutes ago " + dt.strftime("(%I:%M %p)")