from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from tasks.models import Task, TaskAssignment
from accounts.models import User


@login_required
def home(request):
    """Bosh sahifa — asosiy statistika"""

    user = request.user
    today = timezone.now()
    week_ago = today - timedelta(days=7)

    # Umumiy statistika
    stats = {
        'total_tasks': Task.objects.count(),
        'active_tasks': Task.objects.filter(status=Task.Status.ACTIVE).count(),
        'completed_tasks': Task.objects.filter(status=Task.Status.COMPLETED).count(),
        'total_leaders': User.objects.filter(role=User.Role.LEADER).count(),
        'active_leaders': User.objects.filter(
            role=User.Role.LEADER,
            status=User.Status.ACTIVE
        ).count(),
    }

    # Oxirgi 7 kunlik statistika
    weekly_stats = {
        'new_tasks': Task.objects.filter(created_at__gte=week_ago).count(),
        'completed_assignments': TaskAssignment.objects.filter(
            completed_at__gte=week_ago
        ).count(),
    }

    # Faol vazifalar (muddati yaqin)
    active_tasks = Task.objects.filter(
        status=Task.Status.ACTIVE
    ).order_by('deadline')[:5]

    # Oxirgi tayinlashlar
    recent_assignments = TaskAssignment.objects.select_related(
        'task', 'leader'
    ).order_by('-sent_at')[:10]

    # Muddati o'tgan vazifalar
    overdue_tasks = Task.objects.filter(
        status=Task.Status.ACTIVE,
        deadline__lt=today
    ).count()

    # Bajarilish bo'yicha statistika
    assignment_stats = {
        'pending': TaskAssignment.objects.filter(status=TaskAssignment.Status.PENDING).count(),
        'seen': TaskAssignment.objects.filter(status=TaskAssignment.Status.SEEN).count(),
        'in_progress': TaskAssignment.objects.filter(status=TaskAssignment.Status.IN_PROGRESS).count(),
        'completed': TaskAssignment.objects.filter(status=TaskAssignment.Status.COMPLETED).count(),
    }

    context = {
        'stats': stats,
        'weekly_stats': weekly_stats,
        'active_tasks': active_tasks,
        'recent_assignments': recent_assignments,
        'overdue_tasks': overdue_tasks,
        'assignment_stats': assignment_stats,
    }

    return render(request, 'dashboard/home.html', context)


@login_required
def statistics(request):
    """Batafsil statistika sahifasi"""

    today = timezone.now()

    # Vazifalar bo'yicha
    tasks_by_status = Task.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')

    tasks_by_priority = Task.objects.values('priority').annotate(
        count=Count('id')
    ).order_by('priority')

    tasks_by_type = Task.objects.values('task_type').annotate(
        count=Count('id')
    ).order_by('task_type')

    # Yetakchilar bo'yicha
    top_leaders = User.objects.filter(
        role=User.Role.LEADER
    ).annotate(
        completed_count=Count(
            'task_assignments',
            filter=Q(task_assignments__status=TaskAssignment.Status.COMPLETED)
        )
    ).order_by('-completed_count')[:10]

    # Mahallalar bo'yicha
    from accounts.models import Mahalla
    mahalla_stats = Mahalla.objects.annotate(
        leaders_count=Count('users', filter=Q(users__role=User.Role.LEADER)),
        tasks_count=Count('tasks')
    ).order_by('-tasks_count')[:10]

    # Oylik trend (oxirgi 6 oy)
    monthly_data = []
    for i in range(5, -1, -1):
        month_start = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1)

        monthly_data.append({
            'month': month_start.strftime('%B'),
            'tasks': Task.objects.filter(
                created_at__gte=month_start,
                created_at__lt=month_end
            ).count(),
            'completed': TaskAssignment.objects.filter(
                completed_at__gte=month_start,
                completed_at__lt=month_end
            ).count()
        })

    context = {
        'tasks_by_status': tasks_by_status,
        'tasks_by_priority': tasks_by_priority,
        'tasks_by_type': tasks_by_type,
        'top_leaders': top_leaders,
        'mahalla_stats': mahalla_stats,
        'monthly_data': monthly_data,
    }

    return render(request, 'dashboard/statistics.html', context)