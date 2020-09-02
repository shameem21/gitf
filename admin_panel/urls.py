from django.contrib import admin
from django.urls import path
from . import views
from django.conf.urls import url

app_name = "admin_panel"

urlpatterns = [
    path('', views.index),
    path('manage/teacher', views.manage_teacher),
    path('view/teacher', views.view_teacher),
    url(r'^enable_disable_student/$', views.enable_disable_student,
        name="enable_disable_student"),
    url(r'^get_students_with_batch/$', views.get_students_with_batch,
        name="get_students_with_batch"),
    url(r'^send_sms/$', views.send_sms, name="send_sms"),
    path('add/teacher', views.add_teacher),
    path('add/student', views.add_student),
    path('add/subject', views.create_subject),
    path('update/teacher', views.update_teacher, name="update_teacher"),
    path('add/batch', views.add_batch),
    path('registration', views.registration),
    path('manage', views.manage),
    path('manage/student', views.manage_student),
    path('report/monthly', views.generate_report),
    path('report/dialy', views.generate_report_dialy),
    path('trainer', views.trainer),
    path('create/dataset', views.create_dataset),
    path('remove/alloted', views.remove_allotted, name="remove_alloted"),
    path('update/teacher_subject', views.update_teacher_subject),
    path('view/student', views.view_student, name="view_student"),
    url(r'^export/csv/$', views.export_attendence_csv,
        name='export_attendence_csv'),
    url(r'^export/xls/$', views.export_attendence_xlsx,
        name='export_attendence_xlsx'),
]
