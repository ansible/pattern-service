from django.contrib import admin

from .models import Automation, ControllerLabel, Pattern, PatternInstance, Task

admin.site.register(Pattern)
admin.site.register(ControllerLabel)
admin.site.register(PatternInstance)
admin.site.register(Automation)
admin.site.register(Task)
