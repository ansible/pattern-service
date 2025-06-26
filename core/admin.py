from django.contrib import admin

from core import models

admin.site.register(models.Pattern)
admin.site.register(models.ControllerLabel)
admin.site.register(models.PatternInstance)
admin.site.register(models.Automation)
admin.site.register(models.Task)
