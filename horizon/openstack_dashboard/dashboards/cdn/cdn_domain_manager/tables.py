# -*- coding: utf-8 -*-
# author__ = 'yanjiajia'

from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from horizon import exceptions
from horizon import tables
from horizon import messages
from horizon.utils.functions import check_account_is_frozen
import logging
from django.utils.translation import ungettext_lazy
from django import template
from openstack_dashboard.dashboards.cdn.cdn_domain_manager.models\
    import Domain, SourceAddress, CacheRule, AccessControl
from openstack_dashboard.dashboards.cdn import middware
from django import shortcuts
from datetime import datetime
from openstack_dashboard.api.member.member import UserCenter
from openstack_dashboard.api.logger import Logger

LOG = logging.getLogger(__name__)


def get_cdn():
    cdn_list = middware.DomainManage()
    return cdn_list.listAll()


class MyFilterAction(tables.FilterAction):
    def filter(self, table, domains, filter_string):
        """加速域名过滤"""
        query = filter_string.lower()
        return [router for router in domains
                if query in router.name.lower()]


# 创建加速域名
class CreateDomain(tables.LinkAction):
    name = "create"
    verbose_name = _("Add")
    url = "horizon:cdn:cdn_domain_manager:create"
    classes = ("ajax-modal",)
    icon = "plus"

    def allowed(self, request, datum=None):
        self.verbose_name = _("create")
        self.classes = [c for c in self.classes if c != "disabled"]
        account_is_frozen = check_account_is_frozen(request)
        if account_is_frozen:
            if "disabled" not in self.classes:
                self.classes = [c for c in self.classes] + ['disabled']
        else:
            self.classes = [c for c in self.classes if c != "disabled"]
        return True


# 禁用加速域名
class DisableDomain(tables.BatchAction):
    """定制父类"""
    name = "Disable"

    def __init__(self, **kwargs):
        super(DisableDomain, self).__init__(**kwargs)
        self.icon = 'stop'

    def get_default_classes(self):
        """重载类方法"""
        classes = ("btn", "btn-default", "btn-sm")
        return classes

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            _("Disable"),
            _("Disable"),
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            _("Disable"),
            _("Disable"),
            count
        )

    redirect_url = "horizon:cdn:cdn_domain_manager:index"

    def action(self, request, obj_id):
        return self.disable(request, obj_id)

    def disable(self, request, obj_id):
        try:
            # 执行删除前状态检查
            domain = Domain.objects.get(pk=obj_id)
            if domain.status == 'Deployed':
                domain.status = 'inProgress'
                domain.save()
                a = middware.DomainManage()
                a.disable(domainId=domain.domain_id)

                # 插入操作日志
                Logger(request).create(resource_type='CDN', action_name='Disable Domain Name',
                                                       resource_name='CDN', config=_('Domain: %s') %domain.domain_name,
                                                       status='Success')
            else:
                # 插入操作日志
                Logger(request).create(resource_type='CDN', action_name='Disable Domain Name',
                                                       resource_name='CDN', config=_('Domain: %s') %domain.domain_name,
                                                       status='Error')
                msg = _("%s status is %s, can not do this action") % (domain.domain_name, _(domain.status))
                messages.warning(request, msg)
        except Exception:
            # 插入操作日志
            Logger(request).create(resource_type='CDN', action_name='Disable Domain Name',
                                                       resource_name='CDN', config='',
                                                       status='Error')
            obj = self.table.get_object_by_id(obj_id)
            name = self.table.get_object_display(obj)
            msg = _('Unable to disable domain %s') % name
            LOG.info(msg)
            messages.error(request, msg)
            exceptions.handle(request, msg)
            redirect = reverse(self.redirect_url)
            raise exceptions.Http302(redirect, message=msg)

    def allowed(self, request, domain=None):
        account_is_frozen = check_account_is_frozen(request)
        if account_is_frozen:
            if "disabled" not in self.classes:
                self.classes = [c for c in self.classes] + ['disabled']
        else:
            self.classes = [c for c in self.classes if c != "disabled"]
        return True

    def handle(self, table, request, obj_ids):
        action_success = []
        action_failure = []
        action_not_allowed = []
        for datum_id in obj_ids:
            datum = table.get_object_by_id(datum_id)
            datum_display = table.get_object_display(datum) or datum_id
            if not table._filter_action(self, request, datum):
                action_not_allowed.append(datum_display)
                LOG.info('Permission denied to %s: "%s"' %
                         (self._get_action_name(past=True).lower(),
                          datum_display))
                continue
            try:
                self.action(request, datum_id)
                self.update(request, datum)
                action_success.append(datum_display)
                self.success_ids.append(datum_id)
            except Exception as ex:
                if getattr(ex, "_safe_message", None):
                    ignore = False
                else:
                    ignore = True
                    action_failure.append(datum_display)
                exceptions.handle(request, ignore=ignore)

        return shortcuts.redirect(self.get_success_url(request))


class EnableDomain(tables.BatchAction):
    """定制父类"""
    name = "Enable"

    def __init__(self, **kwargs):
        super(EnableDomain, self).__init__(**kwargs)
        self.icon = 'play'

    def get_default_classes(self):
        """重载类方法"""
        classes = ("btn", "btn-default", "btn-sm")
        return classes

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            _("Enable"),
            _("Enable"),
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            _("Enable"),
            _("Enable"),
            count
        )

    redirect_url = "horizon:cdn:cdn_domain_manager:index"

    def action(self, request, obj_id):
        account_is_frozen = check_account_is_frozen(request)
        if account_is_frozen:
            raise exceptions.AccountFrozenException
        return self.enable(request, obj_id)

    def enable(self, request, obj_id):
        try:
            domain = Domain.objects.get(pk=obj_id)
            if domain.status == 'Deployed':
                domain.status = 'inProgress'
                domain.save()
                a = middware.DomainManage()
                a.enable(domainId=domain.domain_id)

                # 插入操作日志
                Logger(request).create(resource_type='CDN', action_name='Enable Domain Name',
                                                       resource_name='CDN', config=_('Domain: %s') %domain.domain_name,
                                                       status='Success')
            else:
                Logger(request).create(resource_type='CDN', action_name='Enable Domain Name',
                                                       resource_name='CDN', config=_('Domain: %s') %domain.domain_name,
                                                       status='Error')
                msg = _("%s status is %s, can not do this action") % (domain.domain_name, _(domain.status))
                messages.warning(request, msg)
        except Exception:
            Logger(request).create(resource_type='CDN', action_name='Enable Domain Name',
                                                       resource_name='CDN', config='',
                                                       status='Error')
            obj = self.table.get_object_by_id(obj_id)
            name = self.table.get_object_display(obj)
            msg = _('Unable to enable domain %s') % name
            LOG.info(msg)
            messages.error(request, msg)
            exceptions.handle(request, msg)
            redirect = reverse(self.redirect_url)
            raise exceptions.Http302(redirect, message=msg)

    def allowed(self, request, domain=None):
        account_is_frozen = check_account_is_frozen(request)
        if account_is_frozen:
            if "disabled" not in self.classes:
                self.classes = [c for c in self.classes] + ['disabled']
        else:
            self.classes = [c for c in self.classes if c != "disabled"]
        return True

    def handle(self, table, request, obj_ids):
        action_success = []
        action_failure = []
        action_not_allowed = []
        for datum_id in obj_ids:
            datum = table.get_object_by_id(datum_id)
            datum_display = table.get_object_display(datum) or datum_id
            if not table._filter_action(self, request, datum):
                action_not_allowed.append(datum_display)
                LOG.info('Permission denied to %s: "%s"' %
                         (self._get_action_name(past=True).lower(),
                          datum_display))
                continue
            try:
                self.action(request, datum_id)
                self.update(request, datum)
                action_success.append(datum_display)
                self.success_ids.append(datum_id)
            except Exception as ex:
                if getattr(ex, "_safe_message", None):
                    ignore = False
                else:
                    ignore = True
                    action_failure.append(datum_display)
                exceptions.handle(request, ignore=ignore)

        return shortcuts.redirect(self.get_success_url(request))



# 删除加速域名
class DeleteDomain(tables.DeleteAction):
    name = 'Delete'

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            _("Delete"),
            _("Delete"),
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            _("Deleted"),
            _("Deleted"),
            count
        )

    redirect_url = "horizon:cdn:cdn_domain_manager:index"

    def delete(self, request, obj_id):
        try:
            # 执行删除前状态检查，当状态为"unverified"或"failed"时直接删除数据库记录
            # 否则更新状态为"deleted",保证数据统计时有记录，然后调用网宿api，删除加速记录
            domain = Domain.objects.get(pk=obj_id)
            cdn = middware.DomainManage()
            if domain.status == "unverified" or domain.status == "failed" or domain.status == "addfailed" \
                    or domain.status == 'verified':
                domain.delete()

                # 插入操作日志
                Logger(request).create(resource_type='CDN', action_name='Delete Domain Name',
                                                       resource_name='CDN', config=_('Domain: %s') %domain.domain_name,
                                                       status='Success')
            elif domain.status == 'inProgress':
                msg = _("%s status is %s, can not do this action") % (domain.domain_name, _(domain.status))
                messages.warning(request, msg)

                # 插入操作日志
                Logger(request).create(resource_type='CDN', action_name='Delete Domain Name',
                                                       resource_name='CDN', config=_('Domain: %s') %domain.domain_name,
                                                       status='Error')
            else:
                domain.status = 'deleted'
                domain.deleted_at = datetime.utcnow()
                domain.save()
                cdn.disable(domainId=domain.domain_id)

                # 插入操作日志
                Logger(request).create(resource_type='CDN', action_name='Delete Domain Name',
                                                       resource_name='CDN', config=_('Domain: %s') %domain.domain_name,
                                                       status='Success')

        except Exception:
            # 插入操作日志
            Logger(request).create(resource_type='CDN', action_name='Delete Domain Name',
                                                       resource_name='CDN', config='',
                                                       status='Error')
            name = self.table.get_object_display(obj_id)
            msg = _('Unable to delete domain %s') % name
            LOG.info(msg)
            messages.error(request, msg)
            exceptions.handle(request, msg)
            redirect = reverse(self.redirect_url)
            raise exceptions.Http302(redirect, message=msg)

    def allowed(self, request, domain=None):
        return True


# row actions
class ConfigDomain(tables.LinkAction):
    """无需设置classes,直接跳转到url,避免对当前url发送请求"""
    name = "update"
    verbose_name = _("Edit")
    url = "horizon:cdn:cdn_domain_manager:update"
    icon = "pencil"

    def allowed(self, request, domain=None):
        account_is_frozen = check_account_is_frozen(request)
        if account_is_frozen:
            if "disabled" not in self.classes:
                self.classes = [c for c in self.classes] + ['disabled']
        else:
            self.classes = [c for c in self.classes if c != "disabled"]
        return True


class VerifyDomain(tables.LinkAction):
    name = "verify"
    verbose_name = _("Verify")
    url = "horizon:cdn:cdn_domain_manager:verify"
    classes = ("ajax-modal",)
    icon = "camera"

    def allowed(self, request, domain=None):
        account_is_frozen = check_account_is_frozen(request)
        if account_is_frozen:
            if "disabled" not in self.classes:
                self.classes = [c for c in self.classes] + ['disabled']
        else:
            self.classes = [c for c in self.classes if c != "disabled"]
        return True


class UpdateRow(tables.Row):
    ajax = True

    def get_data(self, request, id):
        domain_api = middware.DomainManage()
        domain = Domain.objects.get(pk=id)
        cdn = domain_api.find(domainId=domain.domain_id)
        if not cdn.domain:
            return domain
        if domain.status != cdn.domain.status:
               domain.status = cdn.domain.status
               domain.Enable = cdn.domain.enabled
               domain.save()
        return domain


# 加速域名数据展示表格
class DomainManagerTable(tables.DataTable):
    STATUS_DISPLAY_CHOICES_A = (
        ("unverified", _("Unverified")),
        ("failed", _("Verify Failed")),
        ("addfailed", _("Accelerate Failed")),
        ("Deployed", _("Deployed")),
        ("inProgress", _("inProgress")),
    )

    STATUS_CHOICES = (
                     ('unverified', True),
                     ('failed', False),
                     ('addfailed', False),
                     ('Deployed', True),
                     ('inProgress', None),
    )
    domain_name = tables.Column("domain_name", verbose_name=_("Domain Name"))
    source_type = tables.Column("source_type", verbose_name=_("Origin Domain Type"))
    domain_cname = tables.Column('domain_cname', verbose_name=_("CNAME"))
    status = tables.Column('status', verbose_name=_("Status"), status=True,
                           display_choices=STATUS_DISPLAY_CHOICES_A,
                           status_choices=STATUS_CHOICES)
    Enable = tables.Column('Enable', verbose_name=_("Enable"))

    def __init__(self, request, data=None, needs_form_wrapper=None, **kwargs):
        super(DomainManagerTable, self).__init__(
            request,
            data=data,
            needs_form_wrapper=needs_form_wrapper,
            **kwargs)

    def get_object_display(self, obj):
        return obj.domain_name

    def render_row_actions(self, datum, pull_right=True, row=True):
        if row:
            template_path = self._meta.row_actions_row_template
        else:
            template_path = self._meta.row_actions_dropdown_template

        row_actions_template = template.loader.get_template(template_path)
        bound_actions = self.get_row_actions(datum)
        extra_context = {"row_actions": bound_actions,
                         "row_id": self.get_object_id(datum),
                         "pull_right": pull_right}
        context = template.RequestContext(self.request, extra_context)
        return row_actions_template.render(context)

    class Meta(object):
        name = "DomainManager"
        verbose_name = _("Domain List")
        status_columns = ["status"]
        row_class = UpdateRow
        table_actions = (CreateDomain, DisableDomain,
                         EnableDomain, DeleteDomain, MyFilterAction)
        row_actions = (ConfigDomain, VerifyDomain)


# 访问控制表
class AddAccessRule(tables.LinkAction):
    name = "AddAccessControl"
    verbose_name = _("Add")
    url = "horizon:cdn:cdn_domain_manager:addaccess"
    classes = ("ajax-modal",)
    icon = "plus"

    def get_link_url(self, datum=None):
        """将url传参的domain_id发送到table的table_actions"""
        domain_id = self.table.kwargs['domain_id']
        return reverse(self.url, args=(domain_id,))


class ModifyAccessRule(tables.LinkAction):
    name = "ModifyAccessRule"
    verbose_name = _("Modify")
    url = "horizon:cdn:cdn_domain_manager:modifyaccess"
    classes = ("ajax-modal",)
    icon = "pencil"

    def get_link_url(self, datum=None):
        """将url传参的domain_id发送到table的table_actions"""
        domain_id = self.table.kwargs['domain_id']
        access_id = self.table.get_object_id(datum)
        return reverse(self.url, args=(domain_id, unicode(access_id)))


class DeleteAccessRule(tables.DeleteAction):
    name = 'Delete'

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            _("Delete"),
            _("Delete"),
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            _("Deleted"),
            _("Deleted"),
            count
        )

    def delete(self, request, obj_id):
        try:
            access = AccessControl.objects.get(pk=obj_id)
            domain = Domain.objects.get(pk=access.domain_id)
            domain_manager = middware.DomainManage()
            ret = domain_manager.find(domain.domain_id)
            domain_class = ret.getDomain()
            visitControlRules = domain_class.visitControlRules
            if visitControlRules is not None:
                for i in domain_class.visitControlRules:
                    if access.pathPattern == i.pathPattern:
                        visitControlRules.remove(i)
            domain_class = middware.domainApi.Domain(domainId=domain.domain_id,
                                                     visitControlRules=domain_class.visitControlRules)
            domain_manager.modify(domain_class)
            access.delete()

            # 插入操作日志
            Logger(request).create(resource_type='CDN', action_name='Delete Access',
                                                       resource_name='CDN', config=_('Domain: %s') %domain.domain_name,
                                                       status='Success')

        except Exception:
            obj = self.table.get_object_by_id(obj_id)
            name = self.table.get_object_display(obj)
            msg = _('Unable to delete domain access rule %s') % name
            LOG.info(msg)
            messages.error(request, msg)
            exceptions.handle(request, msg)
            redirect = reverse(self.redirect_url)

            # 插入操作日志
            Logger(request).create(resource_type='CDN', action_name='Delete Access',
                                                       resource_name='CDN', config=_('Unable to delete domain access rule %s') % name,
                                                       status='Error')
            raise exceptions.Http302(redirect, message=msg)



    def allowed(self, request, domain=None):
        return True


class UpdateAccessControlTable(tables.DataTable):
    pathPattern = tables.Column("pathPattern", verbose_name=_("Type"))
    allowNullReffer = tables.Column("allowNullReffer", verbose_name=_("Refer"),
                                    help_text=_("If allow request referer to be empty"))
    validRefers = tables.Column('validRefers', verbose_name=_("White List"))
    invalidRefers = tables.Column("invalidRefers", verbose_name=_("Black List"))
    forbiddenIps = tables.Column("forbiddenIps", verbose_name=_("Forbid IP"))

    def __init__(self, request, data=None, **kwargs):
        super(UpdateAccessControlTable, self).__init__(
            request,
            data=data,
            **kwargs)

    def get_object_id(self, datum):
        return datum.id

    def get_object_display(self, datum):
        return datum.pathPattern

    class Meta(object):
        name = "access"
        verbose_name = _("Update Access Control")
        table_actions = (AddAccessRule, DeleteAccessRule)
        row_actions = (ModifyAccessRule,)


# 缓存规则表
class AddCacheRule(tables.LinkAction):
    name = " EditCacheRule"
    verbose_name = _("Add")
    url = "horizon:cdn:cdn_domain_manager:addcache"
    classes = ("ajax-modal",)
    icon = "plus"

    def get_link_url(self, datum=None):
        """将url传参的domain_id发送到table的table_actions"""
        domain_id = self.table.kwargs['domain_id']
        return reverse(self.url, args=(domain_id,))




class ModifyCacheRule(tables.LinkAction):
    name = "ModifyCacheRule"
    verbose_name = _("Modify")
    url = "horizon:cdn:cdn_domain_manager:modifycache"
    classes = ("ajax-modal",)
    icon = "pencil"

    def get_link_url(self, datum=None):
        """将url传参的domain_id发送到table的table_actions"""
        domain_id = self.table.kwargs['domain_id']
        cache_id = self.table.get_object_id(datum)
        return reverse(self.url, args=(domain_id, unicode(cache_id)))


class DeleteCacheRule(tables.DeleteAction):
    name = 'Delete'

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            _("Delete"),
            _("Delete"),
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            _("Deleted"),
            _("Deleted"),
            count
        )

    def delete(self, request, obj_id):
        try:
            cache = CacheRule.objects.get(pk=obj_id)
            domain = Domain.objects.get(pk=cache.domain_id)
            domain_manager = middware.DomainManage()
            ret = domain_manager.find(domain.domain_id)
            domain_class = ret.getDomain()
            cacheBehaviors = domain_class.cacheBehaviors
            if cacheBehaviors is not None:
                for i in cacheBehaviors:
                    if cache.pathPattern == i.pathPattern:
                        cacheBehaviors.remove(i)
            domain_class = middware.domainApi.Domain(domainId=domain.domain_id,
                                                     cacheBehaviors=cacheBehaviors)
            domain_manager.modify(domain_class)
            cache.delete()

            # 插入操作日志
            Logger(request).create(resource_type='CDN', action_name='Delete Cache',
                                                       resource_name='CDN', config=_('Domain: %s') %domain.domain_name,
                                                       status='Success')

        except Exception:
            obj = self.table.get_object_by_id(obj_id)
            name = self.table.get_object_display(obj)
            msg = _('Unable to delete domain cache rule %s') % name
            LOG.info(msg)
            messages.error(request, msg)
            exceptions.handle(request, msg)
            redirect = reverse(self.redirect_url)

            # 插入操作日志
            Logger(request).create(resource_type='CDN', action_name='Delete Cache',
                                                       resource_name='Domain', config= _('Unable to delete domain cache rule %s') % name,
                                                       status='Error')

            raise exceptions.Http302(redirect, message=msg)

    def allowed(self, request, domain=None):
        return True


class UpdateCacheRuleTable(tables.DataTable):
    pathPattern = tables.Column("pathPattern", verbose_name=_("Type"))
    ignoreCacheControl = tables.Column('ignoreCacheControl', verbose_name=_("Ignore"),
                                       help_text=_("If set the cache-control in the HTTP header"))
    cacheTtl = tables.Column('cacheTtl', verbose_name=_("Time"))

    def __init__(self, request, data=None, **kwargs):
        super(UpdateCacheRuleTable, self).__init__(
            request,
            data=data,
            **kwargs)

    def get_object_id(self, datum):
        return datum.id

    def get_object_display(self, datum):
        return datum.pathPattern

    class Meta(object):
        name = "cache"
        verbose_name = _("Update Cache Rule")
        table_actions = (AddCacheRule, DeleteCacheRule)
        row_actions = (ModifyCacheRule,)


