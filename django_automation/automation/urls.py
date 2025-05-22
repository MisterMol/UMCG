from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'), 
    path('vodafone/', views.vodafone, name='vodafone'),
    path('vodafone/form/login', views.vodafone_check_nummers_form, name='vodafone_check_nummers_form'),
    path('vodafone/login/stream', views.vodafone_login_stream, name='vodafone_login_stream'),
    path('vodafone/start-login/', views.start_vodafone_login, name='vodafone_start_login'),
    path('vodafone/stream/<uuid:token>/', views.vodafone_login_stream, name='vodafone_login_stream'),
    path('vodafone/submit-2fa-code/', views.submit_2fa_code, name='submit_2fa_code'),
    path('vodafone/cancel-2fa/', views.cancel_2fa, name='cancel_2fa'),
    path('vodafone/graphql-resultaat-ophalen/', views.haal_graphql_resultaat_op, name='haal_graphql_resultaat_op'),
    path('kpn/', views.kpn, name='kpn'), 
    path('mitel/', views.mitel, name='mitel'), 
    path('micollab/', views.micollab, name='micollab'), 
    path('devops/', views.devops, name='devops'),
]
