# oppia/profile/urls.py
from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView

urlpatterns = patterns('',

    url(r'^register/$', 'oppia.profile.views.register', name="profile_register"),
    url(r'^school_code/$', 'oppia.profile.views.school_code', name="profile_school_code"),
    url(r'^program/$', 'oppia.profile.views.program', name="profile_program"),
    url(r'^register/thanks/$', TemplateView.as_view(template_name="oppia/thanks.html"), name="profile_register_thanks"),
    url(r'^login/$', 'oppia.profile.views.login_view', name="profile_login"),
    url(r'^logout/$', 'django.contrib.auth.views.logout', {'template_name': 'oppia/logout.html',}),
    url(r'^setlang/$', 'django.views.i18n.set_language', name="profile_set_language"),
    url(r'^reset/$', 'oppia.profile.views.reset', name="profile_reset"),
    url(r'^update_profile/$', 'oppia.profile.views.reset', name="profile_reset"),
    url(r'^reset/sent/$', TemplateView.as_view(template_name="oppia/profile/reset-sent.html"), name="profile_reset_sent"),
    url(r'^edit/$', 'oppia.profile.views.edit', name="profile_edit"),
    url(r'^edit/(?P<user_id>\d+)/$', 'oppia.profile.views.edit', name="profile_edit_user"),
    url(r'^points/$', 'oppia.profile.views.points', name="profile_points"),
    url(r'^badges/$', 'oppia.profile.views.badges', name="profile_badges"),
    url(r'^(?P<user_id>\d+)/activity/$', 'oppia.profile.views.user_activity', name="profile_user_activity"),
    url(r'^(?P<user_id>\d+)/(?P<course_id>\d+)/activity/$', 'oppia.profile.views.user_course_activity_view', name="profile_user_course_activity"),
    url(r'^upload/$', 'oppia.profile.views.upload_view', name="profile_upload"),
    url(r'^uploadschool/$', 'oppia.profile.views.upload_schools_view', name="profile_upload_school"),
)
