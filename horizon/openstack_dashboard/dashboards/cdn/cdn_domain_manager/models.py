# -*- coding: utf-8 -*-
# author__ = 'yanjiajia'
"""
网宿云分发平台数据库表对象模型

功能实现列表：
    域名管理
        回源配置
        缓存配置
        访问控制
    缓存刷新
    文件预取
    数据分析
    报表查询
    日志下载
"""
import datetime
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

# 加速域名表
class CdnBillMethod(models.Model):
    tenant_id = models.CharField('租户号', max_length=64)
    current_type = models.CharField('当前记费类型', max_length=20)
    update_type = models.CharField('记费更新类型', max_length=20, null=True)
    update_at = models.DateTimeField('更新时间', null=True)
    effect_at = models.DateTimeField('生效时间', null=True)


class Domain(models.Model):
    tenant_id = models.CharField('租户号', max_length=64)
    user_name = models.CharField('用户名', max_length=64)
    project_name = models.CharField('项目名称', max_length=64)
    domain_id = models.CharField('域名ID', max_length=64, null=True)
    domain_name = models.CharField('加速域名', max_length=64)
    domain_cname = models.CharField('域名别名', max_length=64, null=True)
    source_type = models.CharField('回源地址类型', max_length=64, null=True)
    status = models.CharField('状态', max_length=20, default='unverified')
    Enable = models.CharField('运行状态', max_length=10)
    current_type = models.CharField('当前记费类型', max_length=20)
    update_type = models.CharField('记费更新类型', max_length=20, null=True)
    created_at = models.DateTimeField('创建时间', default=timezone.now)
    deleted_at = models.DateTimeField('删除时间', null=True)
    update_at = models.DateTimeField('更新时间', null=True)
    effect_at = models.DateTimeField('生效时间', null=True)
    error_log = models.TextField('错误日志', null=True)
    xCncRequestId = models.CharField('请求ID', max_length=64)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = _('Domain')

    def __unicode__(self):
        return self.domain_name


class SourceAddress(models.Model):
    domain = models.ForeignKey(Domain)
    source_address = models.CharField('回源地址', max_length=64)

    def __unicode__(self):
        return self.source_address


# 缓存规则
class CacheRule(models.Model):
    domain = models.ForeignKey(Domain)
    pathPattern = models.CharField('路径规则', max_length=64)
    ignoreCacheControl = models.BooleanField('缓存控制')
    cacheTtl = models.CharField('缓存时间', max_length=64)


# 访问控制表
class AccessControl(models.Model):
    domain = models.ForeignKey(Domain)
    pathPattern = models.CharField('控制类型', max_length=64)
    allowNullReffer = models.BooleanField('refer')
    validRefers = models.URLField('白名单', max_length=128)
    invalidRefers = models.URLField('黑名单', max_length=128)
    forbiddenIps = models.CharField('禁止IP', max_length=128)











