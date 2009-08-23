import os.path
import jinja2

thisdir = os.path.dirname(__file__)
templatesdir = os.path.join(thisdir, 'templates')
templatesdir = os.path.abspath(templatesdir)

loader = jinja2.FileSystemLoader(templatesdir)
env = jinja2.Environment(loader=loader)
