from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from .views import RoleLoginView, logout_view, signup_view, signup_admin, dashboard, activate, contact_view
from . import views

app_name = "users"

urlpatterns = [
    path("login/",  RoleLoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
    path("signup/",   signup_view, name="signup"),
    path("register/", signup_view, name="register"),

    path("activate/<uidb64>/<token>/", activate, name="activate"),
    path("dashboard/", dashboard, name="dashboard"),

    path("schedule/", views.page_schedule, name="schedule"),
    path("recycling/", views.page_recycling, name="recycling"),
    path("reuse/", views.page_reuse, name="reuse"),
    path("track/", views.page_track, name="track"),
    path("complaint/", views.page_complaint, name="complaint"),
    path("contact/", contact_view, name="contact"),
    path("profile/", views.profile_view, name="profile"),
    path("go/<str:target>/", views.auth_gate, name="auth_gate"),
    path("reuse_market/", views.reuse_market, name="reuse_market"),
    path("reuse/accept/<int:pk>/", views.reuse_accept, name="reuse_accept"),
    path("accepted/", views.accepted_list, name="accepted_list"),
    path("accepted/<int:pk>/complete/", views.accepted_mark_complete, name="accepted_mark_complete"),
    path("accepted/<int:pk>/cancel/", views.accepted_cancel, name="accepted_cancel"),
    path("track/task/<int:pk>/", views.track_task, name="track_task"),
    path("api/task/<int:pk>/positions/", views.task_positions_api, name="task_positions_api"),
    path("api/track/latest/", views.user_track_latest, name="user_track_latest"),
    path("track/api/task/<int:pk>/", views.user_track_task, name="user_track_task"),
    path("driver/", views.driver_dashboard, name="driver_dashboard"),
    path("driver/tasks/", views.driver_tasks, name="driver_tasks"),
    path("driver/tasks/<int:pk>/start/", views.driver_task_start, name="driver_task_start"),
    path("driver/tasks/<int:pk>/arrive/", views.driver_task_arrive, name="driver_task_arrive"),
    path("driver/tasks/<int:pk>/complete/", views.driver_task_complete, name="driver_task_complete"),
    path("driver/ping/", views.driver_ping, name="driver_ping"),
    path("driver/profile/", views.driver_profile, name="driver_profile"),
    path("driver/forum/", views.driver_forum, name="driver_forum"),
    path("driver/activity/", views.driver_activity, name="driver_activity"),
    path("driver/complaint/", views.driver_complaint, name="driver_complaint"),

    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.html",
            subject_template_name="registration/password_reset_subject.txt",
            success_url=reverse_lazy("users:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            success_url=reverse_lazy("users:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]
