# Script to export all classes for students in the current year
# Exports the class info, teacher email, etc one per line into a csv
# Then uploads the csv to the LittleSIS SFTP server for import


#Needs pysftp: pip install pysftp --upgrade
#Needs oracledb: pip install oracledb --upgrade

# See the following for table information
# https://docs.powerschool.com/PSDD/powerschool-tables/cc-4-ver3-6-1
# https://docs.powerschool.com/PSDD/powerschool-tables/terms-13-ver3-6-1
# https://docs.powerschool.com/PSDD/powerschool-tables/courses-2-ver3-6-1
# https://docs.powerschool.com/PSDD/powerschool-tables/sections-3-ver3-6-1

# importing module
import datetime  # used to get current date for course info
import os  # needed to get environement variables
from datetime import *

import oracledb  # used to connect to PowerSchool database
import pysftp  # used to connect to the LittleSIS sftp site and upload the file

un = os.environ.get('POWERSCHOOL_READ_USER')  # username for read-only database user
pw = os.environ.get('POWERSCHOOL_DB_PASSWORD')  # the password for the database account
cs = os.environ.get('POWERSCHOOL_PROD_DB')  # the IP address, port, and database name to connect to

#set up sftp login info, stored as environment variables on system
sftpUN = os.environ.get('LITTLESIS_SFTP_USERNAME')
sftpPW = os.environ.get('LITTLESIS_SFTP_PASSWORD')
sftpHOST = os.environ.get('LITTLESIS_SFTP_ADDRESS')
cnopts = pysftp.CnOpts(knownhosts='known_hosts')  # connection options to use the known_hosts file for key validation


print(f"Username: {un} |Password: {pw} |Server: {cs}")  # debug so we can see where oracle is trying to connect to/with
print(f"SFTP Username: {sftpUN} |SFTP Password: {sftpPW} |SFTP Server: {sftpHOST}")  # debug so we can see where pysftp is trying to connect to/with
badnames = ['USE', 'training1','trianing2','trianing3','trianing4','planning','admin','nurse','user', 'use ', 'payroll', 'human', "benefits", 'test', 'teststudent','test student','testtt','testtest']

OUTPUT_FILE_NAME = 'littlesis_roster.csv'
EMAIL_SUFFIX = '@d118.org'

with oracledb.connect(user=un, password=pw, dsn=cs) as con:  # create the connecton to the database
    with con.cursor() as cur:  # start an entry cursor
        with open('roster_log.txt', 'w') as log:
            with open(OUTPUT_FILE_NAME, 'w') as output:  # open the output file
                print("Connection established: " + con.version)
                print("Connection established: " + con.version, file=log)

                today = datetime.now()  # get todays date and store it for finding the correct term later
				# print("today = " + str(today)) #debug

                cur.execute("SELECT id, firstday, lastday, schoolid, yearid FROM terms WHERE IsYearRec = 1 AND schoolid = 5 ORDER BY dcid DESC")  # get a list of terms for a building, filtering to only full years
                termRows = cur.fetchall()
                for term in termRows:
                    if term[1] < today and term[2] > today:
                        termyear = str(term[4])  # store the yearid as the term year we really look for in each student

                print('CC.COURSE_NUMBER,CC.SECTION_NUMBER,CC.TERMID,CC.SCHOOLID,CC.EXPRESSION,CC.DATEENROLLED,CC.DATELEFT,COURSES.COURSE_NAME,SECTIONS.ROOM,TEACHERS.EMAIL_ADDR,U_STUDENTSUSERFIELDS.custom_student_email,STUDENTS.STUDENT_NUMBER,STUDENTS.ENTRYDATE,STUDENTS.EXITDATE,STUDENTS.ENROLL_STATUS,SCHOOLS.ABBREVIATION', file=output)
                # do a query for active students, get their enroll infor as well as the school abbreviation
                cur.execute('SELECT students.student_number, students.entrydate, students.exitdate, students.enroll_status, students.schoolid, schools.abbreviation, students.id FROM students LEFT JOIN schools on students.schoolid = schools.school_number WHERE students.enroll_status = 0')
                studentRows = cur.fetchall()


                for student in studentRows:
                    try:
                        print(student, file=log)  # print student result to log for debug
                        stuID = str(int(student[0]))
                        stuEntry = student[1].strftime('%Y-%m-%d')  # convert the full datetime value to just yyyy-mm-dd
                        stuExit = student[2].strftime('%Y-%m-%d')  # convert the full datetime value to just yyyy-mm-dd
                        stuEnroll = str(student[3])
                        schoolID = str(student[4])
                        school = str(student[5])
                        internalID = str(student[6])
                        stuEmail = stuID + EMAIL_SUFFIX  # append email suffix to their student ID to get email

                        try:
                            cur.execute('SELECT id, dcid FROM terms where yearid = ' + termyear + ' AND schoolid = ' + schoolID)
                            termRows = cur.fetchall()
                            for term in termRows:
                                termID = str(term[0])
                                termDCID = str(term[1])
                                print("Found good term for student " + stuID + ": " + termID + " | " + termDCID, file=log)
                                # now for each term that is valid, do a query for all their courses and start processing them
                                try:
                                    cur.execute('SELECT cc.course_number, cc.section_number, cc.termid, cc.schoolid, cc.expression, cc.dateenrolled, cc.dateleft, cc.teacherid, cc.sectionid, courses.course_name FROM cc LEFT JOIN courses ON cc.course_number = courses.course_number WHERE cc.termid = ' + termID + ' AND cc.studentid = ' + internalID)
                                    courseRows = cur.fetchall()
                                    for course in courseRows:
                                        # print(course)
                                        print(course, file=log)
                                        courseNum = str(course[0])
                                        sectionNum = str(course[1])
                                        courseTerm = str(course[2])
                                        courseSchool = str(course[3])
                                        courseExpression = str(course[4])
                                        courseEnrolled = course[5].strftime('%Y-%m-%d')  # convert the full datetime value to just yyyy-mm-dd
                                        courseLeft = course[6].strftime('%Y-%m-%d')  # convert the full datetime value to just yyyy-mm-dd
                                        courseTeacherID = str(course[7])
                                        courseSectionID = str(course[8])
                                        courseName = str(course[9])

                                        cur.execute("SELECT users_dcid FROM schoolstaff WHERE id = " + courseTeacherID)  # get the user dcid from the teacherid in schoolstaff
                                        schoolStaffInfo = cur.fetchall()
                                        # print(schoolStaffInfo, file=log) # debug
                                        teacherDCID = str(schoolStaffInfo[0][0])  # just get the result directly without converting to list or doing loop

                                        cur.execute("SELECT email_addr FROM teachers WHERE users_dcid = " + teacherDCID)  # get the teacher number from the teachers table for that user dcid
                                        teacherInfo = cur.fetchall()
                                        print(teacherInfo, file=log)  # debug
                                        teacherEmail = str(teacherInfo[0][0])  # just get the result directly without converting to list or doing loop

                                        cur.execute("SELECT room FROM sections WHERE id = " + courseSectionID)  # get the room number assigned to the sectionid correlating to our home_room
                                        roomRows = cur.fetchall()
                                        roomNumber = str(roomRows[0][0])
                                        if(teacherEmail != 'None'):  # some attendance/commons classes do not have teachers listed, we dont want to print them
                                            print(courseNum + ',' + sectionNum + ',' + courseTerm + ',' + courseSchool + ',' + courseExpression + ',' + courseEnrolled + ',' + courseLeft + ',"' + courseName + '",' + roomNumber + ',' + teacherEmail + ',' + stuEmail + ',' + stuID + ',' + stuEntry + ',' + stuExit + ',' + stuEnroll + ',' + school, file=output)

                                except Exception as er:
                                    print('Course error on ' + stuID + ': ' + str(er))
                        except Exception as er:
                            print('Term error on ' + str(student[0]) + ': ' + str(er))


                    except Exception as er:
                        print('General error on ' + str(student[0]) + ': ' + str(er))

            #after all the files are done writing and now closed, open an sftp connection to the server and place the file on there
            with pysftp.Connection(sftpHOST, username=sftpUN, password=sftpPW, cnopts=cnopts) as sftp:
                print('SFTP connection established')
                print('SFTP connection established', file=log)
                # print(sftp.pwd)  # debug to list current working directory
                # print(sftp.listdir())  # debug to list files and directory in current directory
                sftp.put(OUTPUT_FILE_NAME)  # upload the file onto the sftp server
                print("Roster file placed on remote server")
                print("Roster file placed on remote server", file=log)
