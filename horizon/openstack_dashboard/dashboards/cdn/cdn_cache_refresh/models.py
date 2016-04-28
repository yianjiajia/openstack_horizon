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

from django.db import models


# 缓存刷新表
class CacheRule(models.Model):
    cache_type = models.CharField('缓存类型',  max_length = 64)
    cache_time = models.IntegerField('缓存时间')
    status = models.CharField('状态', max_length = 64)

    def __unicode__(self):
        return self.cache_type

    def tojson(self):
        fields = []
        for field in self._meta.fields:
            fields.append(field.name)
        d = {}
        for attr in fields:
            d[attr] = getattr(self, attr)
        import json
        return json.dumps(d)