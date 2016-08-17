import hashlib
import requests
from .exceptions import ReactRenderingError, RenderServerError

from django.conf import settings
from django.shortcuts import render, redirect
from rest_framework.renderers import JSONRenderer


class RenderedComponent(object):

    def __init__(self, markup, props, initialState, head):
        self.markup = markup
        self.props = props
        self.initialState = initialState
        self.head = head

    def __str__(self):
        return self.markup

    def __unicode__(self):
        return unicode(self.markup)

    def as_context(self):
        return {'rendered': self.markup,
                'initialState': JSONRenderer().render(self.initialState),
                'head': self.head}


class ReactRedirect(object):

    def __init__(self, path):
        self.path = path

    def __str__(self):
        return self.path


class RenderServer(object):

    def render(self, path, props=None, status=None):
        url = settings.REACT_RENDER_SERVER_URL

        if props is not None:
            serialized_props = JSONRenderer().render(props)
        else:
            serialized_props = None

        options = {
            'path': path,
            'props': props
        }
        if status:
            options['status'] = status
        serialized_options = JSONRenderer().render(options)
        options_hash = hashlib.sha1(
            serialized_options).hexdigest()

        try:
            res = requests.post(
                url,
                data=serialized_options,
                headers={'content-type': 'application/json'},
                params={'hash': options_hash}
            )
        except requests.ConnectionError:
            raise RenderServerError(
                'Could not connect to render server at {}'.format(url))

        if res.status_code != 200:
            raise RenderServerError(
                'Unexpected response from render server at {} - {}: {}'.format(
                    url, res.status_code, res.text)
            )

        obj = res.json()

        markup = obj.get('markup', None)
        err = obj.get('error', None)
        redirect = obj.get('redirect', None)
        initialState = obj.get('initialState', None)
        head = obj.get('head', None)

        if redirect:
            return ReactRedirect(redirect)

        if err:
            if 'message' in err and 'stack' in err:
                raise ReactRenderingError(
                    'Message: {}\n\nStack trace: {}'.format(
                        err['message'], err['stack'])
                )
            raise ReactRenderingError(err)

        if markup is None:
            raise ReactRenderingError(
                'Render server failed to return markup. Returned: {}'.format(
                    obj))

        return RenderedComponent(markup, serialized_props, initialState, head)


render_server = RenderServer()


def react_render(request, props=None, status=None):
    if props is None:
        props = {}
    if request.user.is_authenticated():
        props['isLoggedIn'] = True
    else:
        props['isLoggedIn'] = False
        props['currentUser'] = None
    return render_server.render(request.path, props=props, status=status)


def react_render_to_response(request, props=None, template='react.html',
                             **kwargs):
    status = kwargs.get('status', None)
    react = react_render(request, props=props, status=status)
    if isinstance(react, ReactRedirect):
        return redirect(react.path)
    return render(request, template, react.as_context(), **kwargs)
