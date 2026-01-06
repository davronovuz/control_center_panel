from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count

from .models import User, Region, District, Mahalla
from tasks.models import TaskAssignment


def login_view(request):
    """Login sahifasi"""

    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.status == User.Status.BLOCKED:
                messages.error(request, "Sizning akkauntingiz bloklangan!")
            elif user.status == User.Status.INACTIVE:
                messages.error(request, "Sizning akkauntingiz faol emas!")
            else:
                login(request, user)
                messages.success(request, f"Xush kelibsiz, {user.get_full_name() or user.username}!")

                next_url = request.GET.get('next', 'dashboard:home')
                return redirect(next_url)
        else:
            messages.error(request, "Login yoki parol noto'g'ri!")

    return render(request, 'accounts/login.html')


@login_required
def logout_view(request):
    """Logout"""
    logout(request)
    messages.info(request, "Tizimdan chiqdingiz.")
    return redirect('accounts:login')


@login_required
def leader_list(request):
    """Yetakchilar ro'yxati"""

    leaders = User.objects.filter(role=User.Role.LEADER).select_related(
        'region', 'district', 'mahalla'
    ).annotate(
        tasks_count=Count('task_assignments'),
        completed_count=Count(
            'task_assignments',
            filter=Q(task_assignments__status=TaskAssignment.Status.COMPLETED)
        )
    ).order_by('-created_at')

    # Filterlar
    status = request.GET.get('status')
    region = request.GET.get('region')
    district = request.GET.get('district')
    search = request.GET.get('search')

    if status:
        leaders = leaders.filter(status=status)
    if region:
        leaders = leaders.filter(region_id=region)
    if district:
        leaders = leaders.filter(district_id=district)
    if search:
        leaders = leaders.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(username__icontains=search) |
            Q(phone__icontains=search)
        )

    # Pagination
    paginator = Paginator(leaders, 20)
    page = request.GET.get('page')
    leaders = paginator.get_page(page)

    # Filter uchun ma'lumotlar
    regions = Region.objects.filter(is_active=True)
    districts = District.objects.filter(is_active=True)

    context = {
        'leaders': leaders,
        'regions': regions,
        'districts': districts,
        'status_choices': User.Status.choices,
        'current_filters': {
            'status': status,
            'region': region,
            'district': district,
            'search': search,
        }
    }

    return render(request, 'accounts/leader_list.html', context)


@login_required
def leader_create(request):
    """Yangi yetakchi qo'shish"""

    if request.method == 'POST':
        try:
            user = User.objects.create_user(
                username=request.POST.get('username'),
                password=request.POST.get('password'),
                first_name=request.POST.get('first_name'),
                last_name=request.POST.get('last_name'),
                phone=request.POST.get('phone'),
                role=User.Role.LEADER,
                status=User.Status.ACTIVE,
            )

            # Manzil
            region_id = request.POST.get('region')
            district_id = request.POST.get('district')
            mahalla_id = request.POST.get('mahalla')

            if region_id:
                user.region_id = region_id
            if district_id:
                user.district_id = district_id
            if mahalla_id:
                user.mahalla_id = mahalla_id

            user.save()

            messages.success(request, f"Yetakchi '{user.get_full_name()}' muvaffaqiyatli qo'shildi!")
            return redirect('accounts:leader_list')

        except Exception as e:
            messages.error(request, f"Xatolik: {str(e)}")

    regions = Region.objects.filter(is_active=True)

    context = {
        'regions': regions,
    }

    return render(request, 'accounts/leader_form.html', context)


@login_required
def leader_detail(request, pk):
    """Yetakchi profili"""

    leader = get_object_or_404(User, pk=pk, role=User.Role.LEADER)

    # Vazifalar statistikasi
    assignments = TaskAssignment.objects.filter(leader=leader).select_related('task')

    stats = {
        'total': assignments.count(),
        'pending': assignments.filter(status=TaskAssignment.Status.PENDING).count(),
        'in_progress': assignments.filter(status=TaskAssignment.Status.IN_PROGRESS).count(),
        'completed': assignments.filter(status=TaskAssignment.Status.COMPLETED).count(),
    }

    # Oxirgi vazifalar
    recent_assignments = assignments.order_by('-sent_at')[:10]

    context = {
        'leader': leader,
        'stats': stats,
        'recent_assignments': recent_assignments,
    }

    return render(request, 'accounts/leader_detail.html', context)


@login_required
def leader_edit(request, pk):
    """Yetakchini tahrirlash"""

    leader = get_object_or_404(User, pk=pk, role=User.Role.LEADER)

    if request.method == 'POST':
        leader.first_name = request.POST.get('first_name')
        leader.last_name = request.POST.get('last_name')
        leader.phone = request.POST.get('phone')
        leader.status = request.POST.get('status')

        # Manzil
        region_id = request.POST.get('region')
        district_id = request.POST.get('district')
        mahalla_id = request.POST.get('mahalla')

        leader.region_id = region_id if region_id else None
        leader.district_id = district_id if district_id else None
        leader.mahalla_id = mahalla_id if mahalla_id else None

        # Parol
        new_password = request.POST.get('new_password')
        if new_password:
            leader.set_password(new_password)

        leader.save()

        messages.success(request, "Yetakchi ma'lumotlari yangilandi!")
        return redirect('accounts:leader_detail', pk=pk)

    regions = Region.objects.filter(is_active=True)
    districts = District.objects.filter(is_active=True)
    mahallas = Mahalla.objects.filter(is_active=True)

    context = {
        'leader': leader,
        'regions': regions,
        'districts': districts,
        'mahallas': mahallas,
        'status_choices': User.Status.choices,
    }

    return render(request, 'accounts/leader_form.html', context)


@login_required
def leader_delete(request, pk):
    """Yetakchini o'chirish"""

    leader = get_object_or_404(User, pk=pk, role=User.Role.LEADER)

    if request.method == 'POST':
        name = leader.get_full_name()
        leader.delete()
        messages.success(request, f"Yetakchi '{name}' o'chirildi!")
        return redirect('accounts:leader_list')

    context = {
        'leader': leader,
    }

    return render(request, 'accounts/leader_delete.html', context)