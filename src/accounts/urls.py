from django.conf.urls import *
from django.views.generic.base import TemplateView

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

# for some reason include('django.contrib.auth.urls') wouldn't work with {% url ... %} aka reverse() 
from django.contrib.auth import views as auth_views

urlpatterns = patterns('',
	url(r'^shib_login/$', 'accounts.shib_views.shib_login', name='shib_login'),
	url(r'^shib_hello/$', 'accounts.shib_views.shib_hello', name='shib_hello'),
	url(r'^login/$', auth_views.login, {'template_name': 'registration/login.html'}, name='login'),
	url(r'^logout/$', auth_views.logout_then_login, name='logout'),
	url(r'^change/$', 'accounts.views.change', name='registration_change'),
	url(r'^view/$', 'accounts.views.view', name='registration_view'),
	url(r'^password/change/$', auth_views.password_change, name='password_change'),
	url(r'^password/change/done/$', auth_views.password_change_done, name='password_change_done'),
	url(r'^password/reset/$', auth_views.password_reset, name='password_reset'),
        url(r'^password/reset/confirm/(?P<uidb36>[0-9A-Za-z]{1,13})-(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
           'django.contrib.auth.views.password_reset_confirm_uidb36'),
        url(r'^password/reset/confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
            'django.contrib.auth.views.password_reset_confirm',
            name='password_reset_confirm'),
	url(r'^password/reset/complete/$', auth_views.password_reset_complete, name='password_reset_complete'),
	url(r'^password/reset/done/$', auth_views.password_reset_done, name='password_reset_done'),
	url(r'^register/$', 'accounts.views.register', name='registration_register'),
	url(r'^register/complete/$', TemplateView.as_view(template_name='registration/registration_complete.html'), name='registration_complete'),
	url(r'^register/allow/(?P<user_id>\d+)/$', 'accounts.views.activation_allow', name='activation_allow'),
	url(r'^activate/(?P<activation_key>.+)/$', 'accounts.views.activate', name='registration_activate'),
)

