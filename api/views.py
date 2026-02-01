from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json

from accounts.models import Region, District, Mahalla
from tasks.models import Task, TaskAssignment, TaskResponse, TaskColumn, TaskQuestion


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
        assignment = TaskAssignment.objects.select_related('task').get(
            pk=pk,
            leader=request.user
        )

        if not assignment.can_edit:
            return JsonResponse({
                'success': False,
                'error': 'Tahrirlash mumkin emas'
            })

        task = assignment.task
        saved_count = 0

        # TABLE type
        if task.type == Task.Type.TABLE:
            columns = task.columns.all()

            for key, value in request.POST.items():
                if key.startswith('col_') and value:
                    parts = key.split('_')
                    # parts: ['col', '560c853b-4700-4224-9eb5-6f4a69a03a13', '0']
                    # UUID ichida '-' bor, lekin '_' yo'q
                    if len(parts) >= 3:
                        try:
                            # ═══════════════════════════════════════════
                            # TUZATILDI: UUID to'liq olinadi
                            # ═══════════════════════════════════════════
                            # Oxirgi element - row_index
                            # O'rtadagilar - UUID (birlashtiriladi)
                            column_id = '_'.join(parts[1:-1])  # UUID ni to'liq olish
                            row_index = int(parts[-1])  # Oxirgi element - row index

                            column = columns.filter(pk=column_id).first()
                            if column:
                                response, created = TaskResponse.objects.update_or_create(
                                    assignment=assignment,
                                    column=column,
                                    row_index=row_index,
                                    defaults={'question': None}
                                )
                                response.set_value(value)
                                saved_count += 1
                        except (ValueError, IndexError) as e:
                            print(f"Error parsing column key {key}: {e}")
                            continue

        # SURVEY type
        elif task.type == Task.Type.SURVEY:
            questions = task.questions.all()

            for key, value in request.POST.items():
                if key.startswith('q_') and value:
                    try:
                        question_id = key.replace('q_', '')

                        question = questions.filter(pk=question_id).first()
                        if question:
                            # Multiple choice (checkbox) uchun
                            if question.answer_type == 'multiple':
                                values = request.POST.getlist(key)
                                response, created = TaskResponse.objects.update_or_create(
                                    assignment=assignment,
                                    question=question,
                                    row_index=0,
                                    defaults={'column': None}
                                )
                                response.value_json = values
                                response.save()
                            else:
                                response, created = TaskResponse.objects.update_or_create(
                                    assignment=assignment,
                                    question=question,
                                    row_index=0,
                                    defaults={'column': None}
                                )
                                response.set_value(value)
                            saved_count += 1
                    except Exception as e:
                        print(f"Error parsing question key {key}: {e}")
                        continue

        # REPORT type
        elif task.type == Task.Type.REPORT:
            report_text = request.POST.get('report_text', '')
            if report_text:
                response, created = TaskResponse.objects.update_or_create(
                    assignment=assignment,
                    column=None,
                    question=None,
                    row_index=0
                )
                response.value_text = report_text
                response.save()
                saved_count += 1

        # Update progress
        assignment.update_progress()

        return JsonResponse({
            'success': True,
            'saved_count': saved_count,
            'progress': assignment.progress
        })

    except TaskAssignment.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Vazifa topilmadi'
        })
    except Exception as e:
        print(f"Auto-save error: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


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
        'count': request.user.notifications.filter(is_read=False).count(),
        'notifications': data
    })