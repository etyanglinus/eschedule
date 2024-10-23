from django.contrib import admin
from .models import *

admin.site.register(Employee)
admin.site.register(Shift)
admin.site.register(Schedule)
admin.site.register(Project)
admin.site.register(ShiftSwapRequest)
admin.site.register(TimeEntry)
admin.site.register(Notification)
admin.site.register(TimeOffRequest)
