import os.path
import jinja2
import datetime

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
min_diff = datetime.timedelta(0, 60)

def format_timestamp(t):
    dt = datetime.datetime.fromtimestamp(t)
    now = datetime.datetime.now()

    diff = now - dt
    if diff < min_diff:
        return dt.strftime("less than a minute ago (%I:%M %p)")
    elif diff < hour_diff:
        return dt.strftime("less than an hour ago (%I:%M %p)")
    elif diff < day_diff:
        return dt.strftime("less than a day ago (%I:%M %p)")
    
    return dt.strftime("%A, %d %B %Y, %I:%M %p")

