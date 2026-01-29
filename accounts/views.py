from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count

from .models import User, Region, District, Mahalla, Notification, Announcement


def login_view(request):
    """Login sahifasi"""
    if request.user.is_authenticated:
        if request.user.is_leader:
            return redirect('dashboard:leader_home')
        return redirect('dashboard:home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.status == User.Status.BLOCKED:
                messages.error(request, "Sizning hisobingiz bloklangan!")
                return render(request, 'accounts/login.html')

            if user.status == User.Status.INACTIVE:
                messages.error(request, "Sizning hisobingiz nofaol!")
                return render(request, 'accounts/login.html')

            login(request, user)
            user.increment_login()

            # IP saqlash
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
            user.update_activity(ip)

            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)

            if user.is_leader:
                return redirect('dashboard:leader_home')
            return redirect('dashboard:home')
        else:
            messages.error(request, "Login yoki parol noto'g'ri!")

    return render(request, 'accounts/login.html')


def logout_view(request):
    """Logout"""
    logout(request)
    messages.success(request, "Tizimdan chiqdingiz!")
    return redirect('accounts:login')


@login_required
def profile(request):
    """Profil sahifasi"""
    user = request.user

    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.middle_name = request.POST.get('middle_name', '')
        user.phone = request.POST.get('phone', '')
        user.email = request.POST.get('email', '')

        if request.FILES.get('avatar'):
            user.avatar = request.FILES['avatar']

        user.save()
        messages.success(request, "Profil yangilandi!")
        return redirect('accounts:profile')

    return render(request, 'profile.html', {'user': user})


@login_required
def change_password(request):
    """Parol o'zgartirish"""
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not request.user.check_password(current_password):
            messages.error(request, "Joriy parol noto'g'ri!")
            return redirect('accounts:change_password')

        if new_password != confirm_password:
            messages.error(request, "Yangi parollar mos kelmaydi!")
            return redirect('accounts:change_password')

        if len(new_password) < 6:
            messages.error(request, "Parol kamida 6 ta belgidan iborat bo'lishi kerak!")
            return redirect('accounts:change_password')

        request.user.set_password(new_password)
        request.user.must_change_password = False
        request.user.plain_password = ''
        request.user.save()

        messages.success(request, "Parol muvaffaqiyatli o'zgartirildi! Qaytadan kiring.")
        return redirect('accounts:login')

    return render(request, 'accounts/change_password.html')


# ========== ADMIN: Yetakchilar boshqaruvi ==========

@login_required
def leader_list(request):
    """Yetakchilar ro'yxati (Admin uchun)"""
    if not request.user.is_any_admin:
        messages.error(request, "Sizda ruxsat yo'q!")
        return redirect('dashboard:home')

    leaders = User.objects.filter(role=User.Role.LEADER).select_related('region', 'district', 'mahalla')

    # Admin ko'rish huquqi
    if request.user.is_region_admin:
        leaders = leaders.filter(region=request.user.region)
    elif request.user.is_district_admin:
        leaders = leaders.filter(district=request.user.district)

    # Filterlar
    status = request.GET.get('status')
    region_id = request.GET.get('region')
    district_id = request.GET.get('district')
    search = request.GET.get('search')

    if status:
        leaders = leaders.filter(status=status)
    if region_id:
        leaders = leaders.filter(region_id=region_id)
    if district_id:
        leaders = leaders.filter(district_id=district_id)
    if search:
        leaders = leaders.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(username__icontains=search) |
            Q(phone__icontains=search)
        )

    # Statistika qo'shish
    leaders = leaders.annotate(
        tasks_count=Count('task_assignments'),
        completed_count=Count('task_assignments', filter=Q(task_assignments__status__in=['submitted', 'approved']))
    )

    # Pagination
    paginator = Paginator(leaders, 20)
    page = request.GET.get('page')
    leaders = paginator.get_page(page)

    context = {
        'leaders': leaders,
        'status_choices': User.Status.choices,
        'regions': Region.objects.filter(is_active=True),
        'districts': District.objects.filter(is_active=True),
        'current_filters': {
            'status': status,
            'region': region_id,
            'district': district_id,
            'search': search,
        }
    }
    return render(request, 'accounts/leader_list.html', context)


@login_required
def leader_create(request):
    """Yangi yetakchi qo'shish"""
    if not request.user.is_any_admin:
        messages.error(request, "Sizda ruxsat yo'q!")
        return redirect('dashboard:home')

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        middle_name = request.POST.get('middle_name', '')
        phone = request.POST.get('phone')
        region_id = request.POST.get('region')
        district_id = request.POST.get('district')
        mahalla_id = request.POST.get('mahalla')

        # Username va parol generatsiya
        username = User.generate_username(first_name, last_name)
        password = User.generate_password()

        # User yaratish
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            phone=phone,
            role=User.Role.LEADER,
            status=User.Status.ACTIVE,
            region_id=region_id if region_id else None,
            district_id=district_id if district_id else None,
            mahalla_id=mahalla_id if mahalla_id else None,
            plain_password=password,
            created_by=request.user
        )

        messages.success(request, f"Yetakchi qo'shildi! Login: {username}, Parol: {password}")
        return redirect('accounts:leader_detail', pk=user.pk)

    context = {
        'regions': Region.objects.filter(is_active=True),
        'status_choices': User.Status.choices,
    }
    return render(request, 'accounts/leader_form.html', context)


@login_required
def leader_detail(request, pk):
    """Yetakchi tafsilotlari"""
    leader = get_object_or_404(User.objects.select_related('region', 'district', 'mahalla'), pk=pk,
                               role=User.Role.LEADER)

    if not request.user.can_view_user(leader):
        messages.error(request, "Sizda ruxsat yo'q!")
        return redirect('accounts:leader_list')

    # Statistika
    from tasks.models import TaskAssignment

    assignments = leader.task_assignments.select_related('task')
    stats = {
        'total': assignments.count(),
        'pending': assignments.filter(status=TaskAssignment.Status.PENDING).count(),
        'in_progress': assignments.filter(status=TaskAssignment.Status.IN_PROGRESS).count(),
        'submitted': assignments.filter(status=TaskAssignment.Status.SUBMITTED).count(),
        'completed': assignments.filter(
            status__in=[TaskAssignment.Status.SUBMITTED, TaskAssignment.Status.APPROVED]).count(),
    }

    recent_assignments = assignments.order_by('-created_at')[:10]

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

    if not request.user.can_view_user(leader):
        messages.error(request, "Sizda ruxsat yo'q!")
        return redirect('accounts:leader_list')

    if request.method == 'POST':
        leader.first_name = request.POST.get('first_name')
        leader.last_name = request.POST.get('last_name')
        leader.middle_name = request.POST.get('middle_name', '')
        leader.phone = request.POST.get('phone')
        leader.status = request.POST.get('status')
        leader.region_id = request.POST.get('region') or None
        leader.district_id = request.POST.get('district') or None
        leader.mahalla_id = request.POST.get('mahalla') or None

        # Parol yangilash
        new_password = request.POST.get('new_password')
        if new_password:
            leader.set_password(new_password)
            leader.plain_password = new_password

        leader.save()
        messages.success(request, "Yetakchi yangilandi!")
        return redirect('accounts:leader_detail', pk=leader.pk)

    context = {
        'leader': leader,
        'regions': Region.objects.filter(is_active=True),
        'districts': District.objects.filter(region=leader.region) if leader.region else [],
        'mahallas': Mahalla.objects.filter(district=leader.district) if leader.district else [],
        'status_choices': User.Status.choices,
    }
    return render(request, 'accounts/leader_form.html', context)


@login_required
def leader_delete(request, pk):
    """Yetakchini o'chirish"""
    leader = get_object_or_404(User, pk=pk, role=User.Role.LEADER)

    if not request.user.is_super_admin:
        messages.error(request, "Faqat Super Admin o'chira oladi!")
        return redirect('accounts:leader_list')

    if request.method == 'POST':
        leader.delete()
        messages.success(request, "Yetakchi o'chirildi!")
        return redirect('accounts:leader_list')

    return render(request, 'accounts/leader_delete.html', {'leader': leader})


# ========== Bildirishnomalar ==========

@login_required
def notifications(request):
    """Bildirishnomalar ro'yxati"""
    notifications = request.user.notifications.all()

    # Pagination
    paginator = Paginator(notifications, 20)
    page = request.GET.get('page')
    notifications = paginator.get_page(page)

    return render(request, 'accounts/notifications.html', {'notifications': notifications})


@login_required
def notification_read(request, pk):
    """Bildirishnomani o'qilgan deb belgilash"""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.mark_as_read()

    if notification.link:
        return redirect(notification.link)

    return redirect('accounts:notifications')


@login_required
def notifications_mark_all_read(request):
    """Barcha bildirishnomalarni o'qilgan deb belgilash"""
    request.user.notifications.filter(is_read=False).update(is_read=True)
    messages.success(request, "Barcha bildirishnomalar o'qilgan deb belgilandi!")
    return redirect('accounts:notifications')