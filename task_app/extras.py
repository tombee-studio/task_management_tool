import re
from django import template
from django.template.defaultfilters import stringfilter
import markdown as md
 
register = template.Library()
 
@register.filter()
@stringfilter
def markdown(value, project):
    value = re.sub(r'(commit:\s*([0-9a-zA-Z]+))', f"[\g<1>]({project.git_url})", value)
    value = re.sub(r'\#([0-9]+)', "[\#\g<1>](/task_app/tasks/\g<1>/)", value)
    return md.markdown(value, extensions=['markdown.extensions.fenced_code'])
