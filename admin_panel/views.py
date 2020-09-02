from django.shortcuts import render, redirect
import cv2
import os
import numpy as np
from django.conf import settings
from .models import Batch, Student, Teacher, Subject, Login, Teacher_subject, Attendence
from ams.forms import CreateBatchForm, CreateStudentForm, CreateTeacherForm, CreateSubjectForm, ManageStudentForm, UploadDatasetForm, DialyReportForm, MonthlyReportForm
import pdb
import os
from datetime import datetime
from django.http import HttpResponse, StreamingHttpResponse
import json
from django.core import serializers
from imutils.video import VideoStream
import threading
import gzip
import xlwt
import csv
import urllib.request
import urllib.parse


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sendSMS(apikey, numbers, sender, message):
    data = urllib.parse.urlencode({'apikey': apikey, 'numbers': numbers,
                                   'message': message, 'sender': sender})
    data = data.encode('utf-8')
    request = urllib.request.Request("https://api.textlocal.in/send/?")
    f = urllib.request.urlopen(request, data)
    fr = f.read()
    return(fr)


def send_sms(request):
    if request.method == 'POST':
        id = request.POST.get('id')
        student = Student.objects.get(id=id)
        sms = sendSMS("/CMTtREaOVk-zjjg3aBjH2uqPsJPyVpxYIwrbZ4Ngx",
                      student.parent_mobile, 'TXTLCL', '' + student.name + ' was absent on ' + (datetime.now()).strftime("%d %m %Y ") + ' during ' + request.POST.get('hour'))
        print(sms)
        return HttpResponse(json.dumps({'success': "Success"}), content_type="application/json",)


def index(request):
    if request.session['user_id'] == None:
        return redirect('/')
    elif request.session['type'] != 'admin':
        return redirect('/')
    return render(request, 'admin.html')


def update_teacher_subject(request):
    if request.method == 'POST':
        subject_id = request.POST.get('subject')
        teacher = request.POST.get('teacher')
        subjects = Teacher_subject.objects.filter(
            teacher_id=teacher, subject_id=subject_id)
        if len(subjects) > 0:
            return redirect('/admin_panel/update/teacher?teacher='+str(teacher))
        else:
            Teacher_subject.objects.create(
                teacher_id=teacher,
                subject_id=subject_id
            )
            return redirect('/admin_panel/update/teacher?teacher='+str(teacher))


def create_dataset(request):
    form = UploadDatasetForm()
    if request.method == 'POST':
        form = UploadDatasetForm(request.POST)
        if form.is_valid():
             # print request.POST
            batch = form.cleaned_data['batch']
            student = form.cleaned_data['student']
            dirname = os.path.join('ml/dataset/', batch.name)
            print(dirname)
            if not os.path.exists(dirname):
                os.mkdir(dirname)

            faceDetect = cv2.CascadeClassifier(
                BASE_DIR+'/ml/haarcascade_frontalface_default.xml')
            # cam = VideoStream(src=0).start()#cv2.VideoCapture(0)
            cam = cv2.VideoCapture(0)
            sampleNum = 0
            while(True):
                ret, img = cam.read()
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                faces = faceDetect.detectMultiScale(gray, 1.3, 5)
                for(x, y, w, h) in faces:
                    sampleNum = sampleNum+1
                    cv2.imwrite(BASE_DIR+'/'+dirname+'/user_'+str(student.id) +
                                '_'+str(sampleNum)+'.jpg', gray[y:y+h, x:x+w])
                    cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.waitKey(250)
                cv2.imshow("Face", img)
                cv2.waitKey(1)
                if(sampleNum > 50):
                    break
            cam.release()
            cv2.destroyAllWindows()
            return render(request, 'select_student.html', {'success': "Dataset Created Successfully", 'form': form})
    return render(request, 'select_student.html', {'form': form})


def manage_teacher(request):
    teachers = Teacher.objects.all()
    return render(request, 'mngteach.html', {'teachers': teachers})


def manage_student(request):
    form = ManageStudentForm()
    if request.method == 'POST':
        form = ManageStudentForm(request.POST)
        if form.is_valid():
            batch = form.cleaned_data['batch']
            students = Student.objects.filter(fk_batch_id=batch)
            return render(request, 'mngstd.html', {'form': form, 'students': students, })
    return render(request, 'mngstd.html', {'form': form})


def add_teacher(request):
    subjects = Subject.objects.all()
    if request.method == 'POST':
        form = CreateTeacherForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            error_subject = ''
            ss = []
            for s in subjects:
                if request.POST.get('_subject'+str(s.id)) is not None:
                    ss.insert(0, s)

            if len(ss) == 0:
                error_subject = "Please select at least one subject"
                return render(request, 'addteach.html', {'error_subject': error_subject, 'form': form, 'subjects': subjects, })
            else:
                login = Login.objects.create(
                    username=username, password=password, usertype='teacher')
                teacher = Teacher.objects.create(
                    name=name, fk_login_id=login.id)
                for s in ss:
                    Teacher_subject.objects.create(
                        subject_id=s.id, teacher_id=teacher.id)
                return render(request, 'addteach.html', {'success': "Teacher created successfully"})
        return render(request, 'addteach.html', {'form': form, 'subjects': subjects, })
    else:
        form = CreateTeacherForm()
        context = {'subjects': subjects, 'form': form}
        return render(request, 'addteach.html', context)


def update_teacher(request):
    subjects_all = Subject.objects.all()
    # raise Exception(subjects_all)
    if request.method == 'GET':
        teacher = Teacher.objects.get(id=request.GET.get('teacher'))
        subjects = teacher.teacher_subject_set.all()
        return render(request, 'update_teacher.html', {'subjects': subjects, 'teacher': teacher, 'subjects_all': subjects_all})
    if request.method == 'POST':
        teacher = Teacher.objects.get(id=request.POST.get('teacher'))
        name = request.POST.get('name')
        password = request.POST.get('password')
        if name != None and len(name) != 0 and name != teacher.name:
            teacher.name = name
        if password != None and len(password) != 0:
            if len(request.POST.get('cpassword')) == 0:
                return render(request, 'update_teacher.html', {'teacher': teacher, 'subjects_all': subjects_all, 'error_cpassword': "Please enter confirm password"})
            elif request.POST.get('cpassword') != password:
                return render(request, 'update_teacher.html', {'teacher': teacher, 'subjects_all': subjects_all, 'error_cpassword': "confirm password and password mismatch"})
            else:
                teacher.fk_login.password = password
                teacher.fk_login.save()
        teacher.save()
        return render(request, 'update_teacher.html', {'success': "Teacher updated successfully"})
    return redirect('/admin_panel')


def remove_allotted(request):
    teacher = request.GET.get('teacher')
    subject = request.GET.get('sid')
    s = Teacher_subject.objects.get(id=subject)
    s.delete()
    return redirect('/admin_panel/update/teacher?teacher='+str(teacher))


def add_student(request):
    if request.method == 'POST':
        form = CreateStudentForm(request.POST)
        if form.is_valid():
            Student.objects.create(name=form.cleaned_data['name'], parent_name=form.cleaned_data['parent_name'], parent_mobile=form.cleaned_data['parent_no'],
                                   dob=form.cleaned_data['dob'], fk_batch_id=form.cleaned_data['batch_id'].id, admission_no=form.cleaned_data['admission_no'], status=True)
            return redirect('/admin_panel', {'message': "Student registered Successfully"})
        return render(request, 'studreg.html', {
            'form': form
        })
    form = CreateStudentForm()
    return render(request, 'studreg.html', {
        'form': form,
    })


def view_student(request):
    if request.method == 'GET':
        student = Student.objects.get(id=request.GET.get('id'))
        return render(request, 'studview.html', {'student': student, 'ur': settings.MEDIA_URL})


def add_batch(request):
    form = CreateBatchForm()
    if request.method == 'POST':
        form = CreateBatchForm(request.POST)
        if form.is_valid():
            batch = form.cleaned_data['course']+form.cleaned_data['year']
            if not os.path.exists(os.path.join('ml/dataset/', batch)):
                os.mkdir(os.path.join('ml/dataset/', batch))

            Batch.objects.create(name=batch)
            context = {
                'success': "Batch created successfully",
                'form': form
            }
            return render(request, 'addbatch.html', context)
    return render(request, 'addbatch.html', {'form': form})


def registration(request):
    return render(request, 'reg.html')


def manage(request):
    return render(request, 'mng.html')


def view_teacher(request):
    return render(request, 'teacher.html')


def generate_report(request):
    form = MonthlyReportForm()
    if request.method == 'POST':
        form = MonthlyReportForm(request.POST)
        if form.is_valid():
            batch = form.cleaned_data['batch']
            month = form.cleaned_data['month']
            year = form.cleaned_data['year']
            taken_onf = str(year)+"-"+str(month)+'-1'
            taken_ont = str(year)+"-"+str(int(month)+1)+'-1'
            students = Student.objects.filter(fk_batch_id=batch.id)
            attendences = Attendence.objects.raw("SELECT *,SUM(attendence.status) AS present,COUNT(id) AS total,(COUNT(id) - SUM(attendence.status)) as absence FROM attendence WHERE taken_on<'" +
                                                 taken_ont+"' AND taken_on>'"+taken_onf + "' AND batch_id="+str(batch.id)+" GROUP BY student_id_id,subject_id_id")
            return render(request, 'report.html', {'report_error': not len(attendences) > 0, 'attendences': attendences, 'form': form})
    return render(request, 'report.html', {'form': form})


def generate_report_dialy(request):
    form = DialyReportForm()
    if request.method == 'POST':
        form = DialyReportForm(request.POST)
        if form.is_valid():
            batch = form.cleaned_data['batch']
            day = form.cleaned_data['date']
            attendences = []
            hours = [('HOUR_1', '1st Hour'), ('HOUR_2', '2nd Hour'), ('HOUR_3', '2rd Hour'),
                     ('HOUR_4', '4th Hour'), ('HOUR_5', '5th Hour'), ('HOUR_6', '6th Hour')]
            for h in hours:
                attendences.append((h[1], Attendence.objects.filter(
                    taken_on=day, batch_id=batch.id, hour=h[0])))
            return render(request, 'dialy_report.html', {'form': form, 'attendences': attendences, 'report_error': len(attendences) > 0})
    return render(request, 'dialy_report.html', {'form': form})


def trainer(request):
    import os
    from PIL import Image
    path = BASE_DIR+'/ml/dataset/'

    def getImagesWithID(path):
        imagePaths = [os.path.join(directoryPath, f)
                      for f in os.listdir(directoryPath)]
        faces = []
        Ids = []
        for imagePath in imagePaths:
            faceImg = Image.open(imagePath).convert('L')
            faceNp = np.array(faceImg, 'uint8')
            ID = int(os.path.split(imagePath)[-1].split('_')[1])
            faces.append(faceNp)
            Ids.append(ID)
            cv2.imshow("training", faceNp)
            cv2.waitKey(10)
        return np.array(Ids), np.array(faces)

    directoryPaths = [os.path.join(path, f) for f in os.listdir(path)]
    for directoryPath in directoryPaths:
        print(directoryPath)
        ids, faces = getImagesWithID(directoryPath)
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(faces, ids)
        directory_toc = os.path.join(
            'ml/recognizer/', os.path.basename(os.path.normpath(directoryPath)))
        file_exists = os.path.exists(directory_toc)
        if not file_exists:
            os.mkdir(directory_toc)
        recognizer.save(directory_toc + '/trainingData.yml')
    cv2.destroyAllWindows()
    return render(request, 'admin.html', {'success': "Training Completed Successfully"})


def create_subject(request):
    if request.method == 'GET':
        form = CreateSubjectForm()
        return render(request, 'addsub.html', {'form': form})
    else:
        form = CreateSubjectForm(request.POST)
        if form.is_valid():
            semester = form.cleaned_data['semester']
            subject = form.cleaned_data['subject']
            Subject.objects.create(name=subject, sem=semester)
            # return HttpResponse("Subject created Successfully")
            return render(request, 'addsub.html', {'success': "Subject created Successfully", 'form': form, })
        else:
            return render(request, 'addsub.html', {'form': form, })


def enable_disable_student(request):
    return_value = "0"
    if len(request.POST) > 0:
        id = request.POST['id']
        if id is not None:
            students = Student.objects.get(id=id)
            current_status = not students.status
            print(current_status)
            students.status = current_status
            students.save()
            return_value = {
                'id': id, 'status': current_status, 'message': "Success"}
    return HttpResponse(json.dumps(return_value), content_type="application/json")


def get_students_with_batch(request):
    return_value = []
    if len(request.POST) > 0:
        data = Student.objects.filter(fk_batch_id=request.POST.get('id'))
        return_value = serializers.serialize('json', data)
    return HttpResponse(json.dumps(return_value), content_type="application/json")


def export_attendence_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="attendence.csv"'

    writer = csv.writer(response)
    writer.writerow(['Admission No.', 'Name', 'Total Attendence',
                     'Current Attendence', 'Absence', 'Subject'])
    batch = request.GET.get('batch')
    month = request.GET.get('month')
    year = request.GET.get('year')
    taken_onf = str(year)+"-"+str(month)+'-1'
    taken_ont = str(year)+"-"+str(int(month)+1)+'-1'
    attendences = Attendence.objects.raw("SELECT *,SUM(attendence.status) AS present,COUNT(id) AS total,(COUNT(id) - SUM(attendence.status)) as absence FROM attendence WHERE taken_on<'" +
                                         taken_ont+"' AND taken_on>'"+taken_onf + "' AND batch_id="+str(batch)+" GROUP BY student_id_id,subject_id_id")

    for a in attendences:
        writer.writerow([a.student_id.admission_no, a.student_id.name,
                         a.total, a.present, a.absence, a.subject_id.name])
    return response


def export_attendence_xlsx(request):
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="users.xls"'

    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Users')

    row_num = 0

    font_style = xlwt.XFStyle()
    font_style.font.bold = True

    columns = ['Admission No.', 'Name', 'Total Attendence',
               'Current Attendence', 'Absence', 'Subject']

    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)

    # Sheet body, remaining rows
    font_style = xlwt.XFStyle()

    batch = request.GET.get('batch')
    month = request.GET.get('month')
    year = request.GET.get('year')
    taken_onf = str(year)+"-"+str(month)+'-1'
    taken_ont = str(year)+"-"+str(int(month)+1)+'-1'
    attendences = Attendence.objects.raw("SELECT *,SUM(attendence.status) AS present,COUNT(id) AS total,(COUNT(id) - SUM(attendence.status)) as absence FROM attendence WHERE taken_on<'" +
                                         taken_ont+"' AND taken_on>'"+taken_onf + "' AND batch_id="+str(batch)+" GROUP BY student_id_id,subject_id_id")

    for a in attendences:
        row_num += 1

        ws.write(row_num, 0, a.student_id.admission_no, font_style)
        ws.write(row_num, 1, a.student_id.name, font_style)
        ws.write(row_num, 2, a.total, font_style)
        ws.write(row_num, 3, a.present, font_style)
        ws.write(row_num, 4, a.absence, font_style)
        ws.write(row_num, 5, a.subject_id.name, font_style)
    wb.save(response)
    return response
