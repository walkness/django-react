from django import template
from django.utils.safestring import mark_safe
from webpack_loader.templatetags.webpack_loader import _get_bundle

register = template.Library()


def render_as_tags(bundle, defer):
    tags = []
    for chunk in bundle:
        url = chunk['url']
        if chunk['name'].endswith('.js'):
            tags.append((
                '<script{1} type="text/javascript" src="{0}"></script>'
            ).format(url, ' defer' if defer else '',))
        elif chunk['name'].endswith('.css'):
            tags.append((
                '<link type="text/css" href="{0}" rel="stylesheet"/>'
            ).format(url))
    return mark_safe('\n'.join(tags))


@register.simple_tag
def render_bundle(bundle_name, extension=None, config='DEFAULT', defer=False):
    return render_as_tags(_get_bundle(bundle_name, extension, config), defer)
