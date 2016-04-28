from django.conf import settings
from django.http import HttpResponseForbidden
from django.template import Context, Engine
from django.utils.translation import ugettext as _
from django.utils.version import get_docs_version


# We include the template inline since we need to be able to reliably display
# this error message, especially for the sake of developers, and there isn't any
# other way of making it available independent of what is in the settings file.

# Only the text appearing with DEBUG=False is translated. Normal translation
# tags cannot be used with this inline templates as makemessages would not be
# able to discover the strings.

CSRF_FAILURE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta http-equiv="content-type" content="text/html; charset=utf-8">
  <meta http-equiv="refresh" content="0.1;url="%s">  
</head>
<body>

</body>
</html>
""" % settings.LOGIN_URL


def csrf_failure(request, reason=""):
    """
    Default view used when request fails CSRF protection
    """
    from django.middleware.csrf import REASON_NO_REFERER, REASON_NO_CSRF_COOKIE
    t = Engine().from_string(CSRF_FAILURE_TEMPLATE)
    c = Context({
        'title': _("Forbidden"),
        'main': _("CSRF verification failed. Request aborted."),
        'reason': reason,
        'no_referer': reason == REASON_NO_REFERER,
        'no_referer1': _(
            "You are seeing this message because this HTTPS site requires a "
            "'Referer header' to be sent by your Web browser, but none was "
            "sent. This header is required for security reasons, to ensure "
            "that your browser is not being hijacked by third parties."),
        'no_referer2': _(
            "If you have configured your browser to disable 'Referer' headers, "
            "please re-enable them, at least for this site, or for HTTPS "
            "connections, or for 'same-origin' requests."),
        'no_cookie': reason == REASON_NO_CSRF_COOKIE,
        'no_cookie1': _(
            "You are seeing this message because this site requires a CSRF "
            "cookie when submitting forms. This cookie is required for "
            "security reasons, to ensure that your browser is not being "
            "hijacked by third parties."),
        'no_cookie2': _(
            "If you have configured your browser to disable cookies, please "
            "re-enable them, at least for this site, or for 'same-origin' "
            "requests."),
        'DEBUG': settings.DEBUG,
        'docs_version': get_docs_version(),
        'more': _("More information is available with DEBUG=True."),
    })
    return HttpResponseForbidden(t.render(c), content_type='text/html')
