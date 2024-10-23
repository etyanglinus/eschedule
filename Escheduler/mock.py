from Escheduler.models import Employee, Project, Shift
from django.contrib.auth.models import User
from datetime import date, time
from decimal import Decimal

# Create some users and employees
for i in range(100):  # Generate 100 employees
    user = User.objects.create_user(username=f'user_{i}', password='password')
    Employee.objects.create(user=user, hourly_rate=Decimal('15.00'), 
                            availability_start=time(9, 0), availability_end=time(17, 0))

# Create a sample project
project = Project.objects.create(name="Sample Project", 
                                  description="This is a test project", 
                                  start_date=date(2024, 1, 1), 
                                  end_date=date(2024, 12, 31), 
                                  created_by=User.objects.first())

# Create shifts for employees
for i in range(100):  # Generate 100 shifts
    Shift.objects.create(project=project, start_time=time(9, 0), end_time=time(17, 0), 
                          date=date(2024, 1, (i % 31) + 1))  # Use modulus for dates
