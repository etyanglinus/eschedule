from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message}"

class Project(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)  # Manager who created the project
    
    def __str__(self):
        return self.name

        

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=15.00)  #
    availability_start = models.TimeField(default="09:00:00")  
    availability_end = models.TimeField(default="17:00:00")    
    availability_days = models.CharField(
        max_length=100,
        help_text="Comma-separated list of days (e.g., 'Monday,Tuesday')",
        default="Monday,Tuesday,Wednesday,Thursday,Friday"  
    )

    def is_available_on(self, shift_day, shift_start, shift_end):
        if shift_day in self.availability_days.split(','):
            return self.availability_start <= shift_start and self.availability_end >= shift_end
        return False

    def __str__(self):
        return self.user.username


class Shift(models.Model):
    employees = models.ManyToManyField(Employee, blank=True)  
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True)
    start_time = models.TimeField()  
    end_time = models.TimeField()   
    date = models.DateField(default='2024-01-01')

    
    shift_type = models.CharField(max_length=20, choices=[
        ('WD', 'Working Day'),
        ('WE', 'Weekend'),
        ('HD', 'Holiday'),
    ], null=True, blank=True)

    report_document = models.FileField(upload_to='reports/', null=True, blank=True)


    def __str__(self):
        return f"{self.project.name} - {self.get_shift_type_display()}"

    @property
    def time_entries(self):
        return self.timeentry_set.all()



class ShiftSwapRequest(models.Model):
    original_shift = models.ForeignKey(Shift, related_name='original_shift', on_delete=models.CASCADE)
    requested_shift = models.ForeignKey(Shift, related_name='requested_shift', on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    request_date = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(default='NO reason provided')
    status = models.CharField(max_length=10, choices=[
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    ], default='pending')

    manager_response = models.TextField(null=True, blank=True)
    response_date = models.DateTimeField(null=True, blank=True)
    def __str__(self):
        return f"{self.employee.user.username} - Swap Request from {self.original_shift} to {self.requested_shift}"


class TimeEntry(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE)
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Employee's hourly rate

    def duration(self):
        if self.check_in and self.check_out:
            return self.check_out - self.check_in
        return None

    def calculate_overtime(self):
        overtime_threshold = 8 * 3600  # 8 hours in seconds
        if self.duration():
            worked_seconds = self.duration().seconds
            if worked_seconds > overtime_threshold:
                overtime_seconds = worked_seconds - overtime_threshold
                return overtime_seconds / 3600  # Return in hours
        return 0

    def calculate_payment(self):
        base_hours = min(self.duration().seconds / 3600, 8)  # First 8 hours
        overtime_hours = self.calculate_overtime()

        # Convert hourly_rate to Decimal
        hourly_rate = Decimal(str(self.hourly_rate))
        
        overtime_multiplier = Decimal('1.5')

        # Return Decimal result
        return (Decimal(base_hours) * hourly_rate) + (Decimal(overtime_hours) * hourly_rate * overtime_multiplier)


class TimeOffRequest(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    reason = models.TextField(default='No reason provided')
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=[
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    ], default='pending')
    manager_response = models.TextField(null=True, blank=True)
    response_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.employee.user.username} - Time Off Request from {self.start_date} to {self.end_date}"

class Schedule(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField()
    shifts = models.ManyToManyField(Shift)

    def __str__(self):
        return f"Schedule for {self.project.name} on {self.date}"
    

