import os
import django

# Set the environment variable for the settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'employee_scheduler.settings')

# Initialize Django
django.setup()  

from django.db import connection
from Escheduler.models import Employee, Shift

import time


def measure_simple_query():
    # Measure response time for a simple query
    times = []
    for _ in range(10):  
        start_time = time.time()
        # Simple query: Get all employees
        Employee.objects.filter(user__username__startswith='user_').all()
        end_time = time.time()
        times.append((end_time - start_time) * 1000)  
    average_time = sum(times) / len(times)
    print(f"Average Simple Query Response Time: {average_time:.2f} ms")
    
    # Optionally, get the raw execution time with EXPLAIN ANALYZE
    with connection.cursor() as cursor:
        cursor.execute('EXPLAIN ANALYZE SELECT * FROM "Escheduler_employee" WHERE user_id < 100;')
        result = cursor.fetchall()
        for row in result:
            print(row)

def measure_complex_query():
    print("Measuring Complex Query Performance")
    times = []
    for _ in range(10):  
        start_time = time.time()
        # Complex query: Inner join between Shift and Employee through the ManyToMany relationship
        Shift.objects.filter(start_time__gte='09:00:00').select_related('employees').all()
        end_time = time.time()
        times.append((end_time - start_time) * 1000)  # Convert to milliseconds
    average_time = sum(times) / len(times)
    print(f"Average Complex Query Response Time: {average_time:.2f} ms")
    
    # Optionally, get the raw execution time with EXPLAIN ANALYZE
    with connection.cursor() as cursor:
        cursor.execute('EXPLAIN ANALYZE SELECT * FROM "Escheduler_shift" '
                       'INNER JOIN "Escheduler_shift_employees" ON "Escheduler_shift"."id" = "Escheduler_shift_employees"."shift_id" '
                       'WHERE "Escheduler_shift"."start_time" >= \'09:00:00\';')
        result = cursor.fetchall()
        for row in result:
            print(row)


if __name__ == "__main__":
    print("Measuring Simple Query Performance")
    measure_simple_query()
    
    print("\nMeasuring Complex Query Performance")
    measure_complex_query()
