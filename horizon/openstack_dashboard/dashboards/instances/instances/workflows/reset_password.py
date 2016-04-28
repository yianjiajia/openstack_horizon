# Created by zhihao.ding 2015/12/3

import json

from django.utils.translation import ugettext_lazy as _
from django.views.decorators.debug import sensitive_variables  # noqa

from horizon import exceptions
from horizon import forms
from horizon import workflows
from horizon import messages
from openstack_dashboard import api
from openstack_dashboard.dashboards.instances.instances \
    import utils as instance_utils
from openstack_dashboard.usage import quotas

from horizon.utils import validators
from horizon.utils import userdata

class ResetPasswordAction(workflows.Action):
    instance_id = forms.CharField(label=_("Instance ID"),
                                  widget=forms.HiddenInput(),
                                  required=False)

    is_allow_inject_passwd = forms.CharField(widget=forms.HiddenInput(), required=False)

    image_name = forms.CharField(widget=forms.HiddenInput(), required=False)

    validate_code = forms.CharField(max_length=64,
                                    label=_("Please Input Validate Code"),
                                    required=False)

    username = forms.CharField(max_length=64, label=_("User Name"), required=False)

    is_sync_set_root = forms.BooleanField(label=_("Sync set root/Administrator password"), initial=True, required=False)

    password = forms.RegexField(
        label=_("Password"),
        required=False,
        widget=forms.PasswordInput(render_value=False, attrs={'placeholder': _('begin letter,8-64 bits,with number,letter and symbol')}),
        regex=validators.password_validator(),
        error_messages={'invalid': validators.password_validator_msg()})

    confirm_password = forms.CharField(
        label=_("Confirm Password"),
        required=False,
        widget=forms.PasswordInput(render_value=False))

    is_reboot = forms.BooleanField(label=_("Reboot after reset password successfully"), initial=True, required=False) 

    def __init__(self, request, context, *args, **kwargs):
        super(ResetPasswordAction, self).__init__(request, context, *args, **kwargs)

        self.fields["username"].initial = 'syscloud'

        is_allow_inject_passwd = context.get('is_allow_inject_passwd')
        if not is_allow_inject_passwd:
            del self.fields['username']
            del self.fields['is_sync_set_root']
            del self.fields['password']
            del self.fields['confirm_password']
            del self.fields['is_reboot']

    class Meta(object):
        name = _("Reset Password")
        slug = 'reset_password'
        help_text_template = ("instances/instances/"
                              "_reset_password.html")

    def clean(self):
        cleaned_data = super(ResetPasswordAction, self).clean()
        return cleaned_data

    '''
    def get_help_text(self, extra_context=None):
        extra = {} if extra_context is None else dict(extra_context)
        return super(AuthenticationAction, self).get_help_text(extra)
    '''

class ResetPasswordStep(workflows.Step):
    action_class = ResetPasswordAction
    depends_on = ("instance_id", "name", "is_allow_inject_passwd", "image_name")
    contributes = ("phone_number", "validate_code", "is_sync_set_root", "username",
                   "password", "is_reboot", "is_allow_inject_passwd", "image_name")


class ResetPassword(workflows.Workflow):
    slug = "reset_password"
    name = _("Reset Password")
    finalize_button_name = _("Reset Password")
    success_message = _('Success Reset Password for instance %s.')
    failure_message = _('Unable to Reset Password for instance %s.')
    success_url = "horizon:instances:instances:index"
    default_steps = (ResetPasswordStep,)

    def format_status_message(self, message):
        return message % self.context.get('name', '')

    @sensitive_variables('context')
    def handle(self, request, context):
        validate_code = context.get('validate_code', None)
        if validate_code:
            request.session[validate_code] = None

        instance_id = context.get('instance_id', None)
        instance_name = context.get('name', None)

        username = context.get("username", None)
        password = context.get("password", None)

        image_name = context.get("image_name", None)
        is_allow_inject_passwd = context.get("is_allow_inject_passwd", 'False')
        is_allow_inject_passwd = True if 'True' == is_allow_inject_passwd else False

        is_sync_set_root = context.get("is_sync_set_root", False)
        is_reboot = context.get('is_reboot', False)

        if not is_allow_inject_passwd:
            messages.warning(request, _('Unable to Reset Password for instance %s.') % instance_name)
            return False

        try:
            #instance = api.nova.server_get(request, instance_id)

            user_data_script_helper = userdata.UserDataScriptHelper(image_name, is_sync_set_root=is_sync_set_root, is_rebuild=True)
            user_data = user_data_script_helper.get_user_data(username, password)

            api.nova.server_change_user_data(request, instance_id, user_data)

            # operation log
            config = _('Instance Name: %s') % instance_name
            api.logger.Logger(request).create(resource_type='instance',
                                              action_name='Reset Password',
                                              resource_name='Instance',
                                              config=config,
                                              status='Success')

            def hard_reboot():
                api.nova.server_reboot(request, instance_id, soft_reboot=True)
                # operation log
                api.logger.Logger(request).create(resource_type='instance',
                                                  action_name='Reboot System',
                                                  resource_name='Instance',
                                                  config=_('Instance Name: %s') % instance_name,
                                                  status='Success')

            if is_reboot:
                hard_reboot()

            return True
        except Exception:
            exceptions.handle(request)

            # operation log
            api.logger.Logger(request).create(resource_type='instance', action_name='Reset Password',
                                                       resource_name='Instance', config='',
                                                       status='Error')
            return False
