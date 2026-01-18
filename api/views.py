from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json

from accounts.models import Region, District, Mahalla
from tasks.models import TaskAssignment, TaskResponse, TaskColumn, TaskQuestion


@login_required
def get_districts(request):
    """Viloyat bo'yicha tumanlar"""
    region_id = request.GET.get('region')

    if region_id:
        districts = District.objects.filter(
            region_id=region_id,
            is_active=True
        ).values('id', 'name')
        return JsonResponse(list(districts), safe=False)

    return JsonResponse([], safe=False)


@login_required
def get_mahallas(request):
    """Tuman bo'yicha mahallalar"""
    district_id = request.GET.get('district')

    if district_id:
        mahallas = Mahalla.objects.filter(
            district_id=district_id,
            is_active=True
        ).values('id', 'name')
        return JsonResponse(list(mahallas), safe=False)

    return JsonResponse([], safe=False)


@login_required
@require_http_methods(["POST"])
def task_auto_save(request, pk):
    """Vazifa javoblarini avtomatik saqlash"""
    try:
        assignment = TaskAssignment.objects.get(pk=pk, leader=request.user)

        if not assignment.can_edit:
            return JsonResponse({'success': False, 'error': 'Tahrirlash mumkin emas'})

        task = assignment.task

        # Table type
        if task.type == 'table':
            for column in task.columns.all():
                for row_index in range(100):  # Max 100 rows
                    field_name = f'col_{column.pk}_{row_index}'
                    value = request.POST.get(field_name)

                    if value is not None:
                        response, created = TaskResponse.objects.get_or_create(
                            assignment=assignment,
                            column=column,
                            row_index=row_index
                        )
                        response.set_value(value)

        # Survey type
        elif task.type == 'survey':
            for question in task.questions.all():
                field_name = f'q_{question.pk}'
                value = request.POST.get(field_name)

                if value is not None:
                    response, created = TaskResponse.objects.get_or_create(
                        assignment=assignment,
                        question=question,
                        row_index=0
                    )
                    response.set_value(value)

        # Report type
        elif task.type == 'report':
            value = request.POST.get('report_text')
            if value:
                response, created = TaskResponse.objects.get_or_create(
                    assignment=assignment,
                    row_index=0,
                    column=None,
                    question=None
                )
                response.value_text = value
                response.save()

        # Update progress
        assignment.update_progress()

        return JsonResponse({
            'success': True,
            'progress': assignment.progress
        })

    except TaskAssignment.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Vazifa topilmadi'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def get_notifications(request):
    """Bildirishnomalar (AJAX)"""
    notifications = request.user.notifications.filter(is_read=False)[:10]

    data = []
    for notif in notifications:
        data.append({
            'id': str(notif.pk),
            'type': notif.type,
            'title': notif.title,
            'message': notif.message[:100],
            'link': notif.link,
            'created_at': notif.created_at.isoformat()
        })

    return JsonResponse({
        'count': request.user.unread_notifications_count,
        'notifications': data
    })


from django.shortcuts import render

# Create your views here.
