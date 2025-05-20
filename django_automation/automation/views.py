from django.shortcuts import render
from django.http import JsonResponse
from playwright_scripts.login_script import vodafone_login, send_graphql_request
from django.http import StreamingHttpResponse
from playwright.sync_api import sync_playwright
from urllib.parse import unquote
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.views.decorators.http import require_POST
from django.core.cache import cache 
from django.http import JsonResponse
import json
import uuid
import re
import requests
import logging

logger = logging.getLogger(__name__)

logger.debug("Debugbericht")
logger.info("Info")
logger.error("Foutmelding")

# Create your views here.


def dashboard(request):
    return render(request, 'automation/dashboard.html')



def vodafone(request):
    return render(request, 'automation/vodafone.html')


def vodafone_login_form(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        print("[+] Request ontvangen")
        try:
            title = vodafone_login(username, password)
            return JsonResponse({'success': True, 'message': f'Inloggen gelukt: {title}'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return render(request, 'automation/forms/vodafone_forms/vodafone_login_form.html')


def vodafone_login_stream(request, token):
    data = cache.get(f'vodafone_login:{token}')
    if not data:
        def error_stream():
            yield 'data: {"message": "Ongeldige of verlopen sessie.", "success": false}\n\n'
        return StreamingHttpResponse(error_stream(), content_type='text/event-stream')

    username = data['username']
    password = data['password']
    zoeknummer = data['zoeknummer']

    return StreamingHttpResponse(
        vodafone_login(username, password, token, zoeknummer), 
        content_type='text/event-stream'
    )


@require_POST
@csrf_protect
def start_vodafone_login(request):
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        zoeknummer = data.get('zoeknummer')

        if not username or not password or not zoeknummer:
            return JsonResponse({'error': 'Ongeldige gegevens'}, status=400)

        token = str(uuid.uuid4())
        cache.set(f'vodafone_login:{token}', {
            'username': username,
            'password': password,
            'zoeknummer': zoeknummer
        }, timeout=300)

        return JsonResponse({'token': token})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



@require_POST
@csrf_exempt
def submit_2fa_code(request):
    token = request.POST.get('token')
    code = request.POST.get('code')
    if not token or not code:
        return JsonResponse({'error': 'Token of code ontbreekt'}, status=400)

    cache.set(f"2fa_code:{token}", code, timeout=180)
    return JsonResponse({'status': 'ok'})

@require_POST
@csrf_exempt
def cancel_2fa(request):
    token = request.POST.get('token')
    if not token:
        return JsonResponse({'error': 'Token ontbreekt'}, status=400)

    cache.set(f"2fa_cancel:{token}", True, timeout=180)
    return JsonResponse({'status': 'cancelled'})


@require_POST
@csrf_exempt
def graphql_nummer_lookup(request):
    try:
        data = json.loads(request.body)
        token = data.get('token')
        nummer = data.get('zoeknummer')

        session = cache.get(f'vodafone_session:{token}')
        if not session:
            return JsonResponse({'error': 'Geen geldige sessie gevonden'}, status=401)

        response_data = send_graphql_request(session, nummer)
        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



@csrf_exempt
def haal_graphql_resultaat_op(request):
    try:
        if request.method != "POST":
            return JsonResponse({"error": "Alleen POST ondersteund"}, status=405)

        print("Request method:", request.method)
        print("Content-Type:", request.headers.get("Content-Type"))
        print("Request body (raw):", request.body)

        if not request.body:
            return JsonResponse({"error": "Lege body ontvangen"}, status=400)

        data = json.loads(request.body)
        print("DATA == ", data)

        token = data.get("token")
        print("OPHAAL KEY == ", f"graphql_result:{token}")

        if not token:
            return JsonResponse({"error": "Token ontbreekt"}, status=400)

        result = cache.get(f"graphql_result:{token}")
        print("CACHE RESULTAAT == ", result)

        if result is None:
            return JsonResponse({"error": "Geen resultaat gevonden"}, status=404)

        print("RESULT als tekst == ", json.dumps(result, indent=2, ensure_ascii=False))
        return JsonResponse(result, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



def kpn(request):
    return render(request, 'automation/kpn.html')




def micollab(request):
    return render(request, 'automation/micollab.html')



    
def mitel(request):
    return render(request, 'automation/mitel.html')



    
def devops(request):
    return render(request, 'automation/devops.html')


