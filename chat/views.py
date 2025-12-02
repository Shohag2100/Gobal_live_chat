from django.contrib.auth import authenticate, login, logout, get_user_model
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token
from django.shortcuts import render
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.files.storage import FileSystemStorage
import json
import socket
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Q

from .models import PrivateMessage

# Try to use dnspython for MX lookups when available
try:
    from importlib import import_module
    dns_pkg = import_module('dns')
    try:
        # ensure the resolver submodule is available
        import_module('dns.resolver')
        dns = dns_pkg
    except Exception:
        dns = None
except Exception:
    dns = None

CustomUser = get_user_model()


@csrf_exempt
def register_view(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=400)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # Expect: email, full_name, username, password, confirm_password
    email = (data.get('email') or '').strip()
    full_name = (data.get('full_name') or '').strip()
    username = (data.get('username') or '').strip()
    password = data.get('password')
    confirm = data.get('confirm_password')
    errors = {}

    # presence checks
    if not email:
        errors['email'] = 'Email is required'
    if not username:
        errors['username'] = 'Username is required'
    if not full_name:
        errors['full_name'] = 'Full name is required'
    if not password:
        errors['password'] = 'Password is required'
    if not confirm:
        errors['confirm_password'] = 'Confirm password is required'

    if errors:
        return JsonResponse({'errors': errors}, status=400)

    # password match
    if password != confirm:
        errors['confirm_password'] = 'Passwords do not match'

    # validate email format
    try:
        validate_email(email)
    except ValidationError:
        errors['email'] = 'Invalid email address'

    # basic domain existence check (MX then A record)
    domain = email.split('@')[-1]
    domain_ok = False
    try:
        if dns:
            answers = dns.resolver.resolve(domain, 'MX')
            if answers:
                domain_ok = True
    except Exception:
        domain_ok = False

    if not domain_ok:
        try:
            socket.gethostbyname(domain)
            domain_ok = True
        except Exception:
            domain_ok = False

    if not domain_ok:
        errors['email'] = 'Email domain appears invalid or unreachable'

    # uniqueness checks
    if CustomUser.objects.filter(username=username).exists():
        errors['username'] = 'Username already taken'
    if CustomUser.objects.filter(email=email).exists():
        errors['email'] = 'Email already registered'

    if errors:
        return JsonResponse({'errors': errors}, status=400)

    user = CustomUser.objects.create_user(username=username, email=email, password=password)
    # store full name in first_name (or extend model for separate field later)
    user.first_name = full_name
    user.save()
    login(request, user)
    return JsonResponse({"success": True, "username": user.username})


@csrf_exempt
def login_view(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=400)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    identifier = (data.get('email') or data.get('username') or '').strip()
    password = data.get('password')

    if not identifier or not password:
        return JsonResponse({"error": "Email/username and password required"}, status=400)

    # First, try direct authentication assuming identifier is username
    user = authenticate(request, username=identifier, password=password)

    # If that fails and the identifier looks like an email, try to find the user
    # by email and authenticate using their username. This allows logging in
    # with either email or username.
    if not user and '@' in identifier:
        try:
            possible = CustomUser.objects.filter(email__iexact=identifier).first()
            if possible:
                user = authenticate(request, username=possible.username, password=password)
        except Exception:
            user = None

    if user:
        login(request, user)
        return JsonResponse({"success": True, "username": user.username})

    return JsonResponse({"error": "Invalid credentials"}, status=400)


def get_csrf(request):
    return JsonResponse({'csrfToken': get_token(request)})


def chat_room(request):
    return render(request, 'chat/room.html')


def current_user(request):
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        return JsonResponse({'username': user.username})
    return JsonResponse({'error': 'unauthorized'}, status=401)


@csrf_exempt
def logout_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    try:
        logout(request)
        return JsonResponse({'success': True})
    except Exception:
        return JsonResponse({'error': 'logout failed'}, status=500)


@csrf_exempt
def upload_image(request):
    """Accepts a multipart POST with an 'image' file, saves it to MEDIA_ROOT and returns its absolute URL.

    Requires the user to be authenticated (returns 401 otherwise).
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    user = getattr(request, 'user', None)
    if not (user and user.is_authenticated):
        return JsonResponse({'error': 'unauthorized'}, status=401)

    if 'image' not in request.FILES:
        return JsonResponse({'error': 'image file required'}, status=400)

    image = request.FILES['image']
    fs = FileSystemStorage(location=str(settings.MEDIA_ROOT))
    filename = fs.save(image.name, image)
    rel_url = settings.MEDIA_URL + filename
    abs_url = request.build_absolute_uri(rel_url)
    return JsonResponse({'image_url': abs_url})


@csrf_exempt
def remove_user(request):
    """Admin-only: remove a user by username and broadcast a notice to the chat room.

    POST JSON: { "username": "target" }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    if not getattr(request, 'user', None) or not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({'error': 'forbidden'}, status=403)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'invalid json'}, status=400)

    target = (data.get('username') or '').strip()
    if not target:
        return JsonResponse({'error': 'username required'}, status=400)

    tup = CustomUser.objects.filter(username=target)
    if not tup.exists():
        return JsonResponse({'error': 'user not found'}, status=404)

    # delete the user
    tup.delete()

    # broadcast a message to global_chat so clients see the removal
    layer = get_channel_layer()
    async_to_sync(layer.group_send)('global_chat', {
        'type': 'chat_message',
        'message': f'User {target} was removed by admin',
        'image_url': None,
        'username': '(admin)'
    })

    return JsonResponse({'success': True})


def private_messages(request):
    """Return recent private messages between the authenticated user and a target user.

    Query params: `username` (preferred) or `user_id`.
    """
    user = getattr(request, 'user', None)
    if not (user and user.is_authenticated):
        return JsonResponse({'error': 'unauthorized'}, status=401)

    target_name = request.GET.get('username')
    target_id = request.GET.get('user_id')
    target = None
    if target_name:
        try:
            target = CustomUser.objects.get(username=target_name)
        except CustomUser.DoesNotExist:
            return JsonResponse({'error': 'target not found'}, status=404)
    elif target_id:
        try:
            target = CustomUser.objects.get(id=int(target_id))
        except Exception:
            return JsonResponse({'error': 'target not found'}, status=404)
    else:
        return JsonResponse({'error': 'username or user_id required'}, status=400)

    qs = PrivateMessage.objects.filter(
        Q(sender=user, recipient=target) | Q(sender=target, recipient=user)
    ).order_by('timestamp')[:200]

    return JsonResponse({'messages': [m.to_dict() for m in qs]})