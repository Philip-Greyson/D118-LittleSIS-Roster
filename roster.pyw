"""Script to export class section info for all students to a csv which is uploaded to LittleSIS.

https://github.com/Philip-Greyson/D118-LittleSIS-Roster

Finds all currently enrolled students, then finds the current terms for this school year.
Finds the courses the students are enrolled in for those terms and then all the requisite info about the sections.
Exports each course information to a .csv file, which is then uploaded to the LittleSIS SFTP server for processing.

needs oracledb: pip install oracledb --upgrade
needs pysftp: pip install pysftp --upgrade

See the following for PS table information:
https://ps.powerschool-docs.com/pssis-data-dictionary/latest/terms-13-ver3-6-1
https://ps.powerschool-docs.com/pssis-data-dictionary/latest/cc-4-ver3-6-1
https://ps.powerschool-docs.com/pssis-data-dictionary/latest/courses-2-ver3-6-1
https://ps.powerschool-docs.com/pssis-data-dictionary/latest/sections-3-ver3-6-1
"""

# importing module
import datetime as dt # used to get current date for course info
import os  # needed to get environement variables
import sys
from datetime import *

import oracledb  # used to connect to PowerSchool database
import pysftp  # used to connect to the LittleSIS sftp site and upload the file

DB_UN = os.environ.get('POWERSCHOOL_READ_USER')  # username for read-only database user
DB_PW = os.environ.get('POWERSCHOOL_DB_PASSWORD')  # the password for the database account
DB_CS = os.environ.get('POWERSCHOOL_PROD_DB')  # the IP address, port, and database name to connect to

#set up sftp login info, stored as environment variables on system
SFTP_UN = os.environ.get('LITTLESIS_SFTP_USERNAME')
SFTP_PW = os.environ.get('LITTLESIS_SFTP_PASSWORD')
SFTP_HOST = os.environ.get('LITTLESIS_SFTP_ADDRESS')
CNOPTS = pysftp.CnOpts(knownhosts='known_hosts')  # connection options to use the known_hosts file for key validation


print(f"DBUG: Username: {DB_UN} | Password: {DB_PW} | Server: {DB_CS}")  # debug so we can see where oracle is trying to connect to/with
print(f"DBUG: SFTP Username: {SFTP_UN} | SFTP Password: {SFTP_PW} | SFTP Server: {SFTP_HOST}")  # debug so we can see where pysftp is trying to connect to/with

OUTPUT_FILE_NAME = 'littlesis_roster.csv'
EMAIL_SUFFIX = '@d118.org'
TERMYEAR_SCHOOL_NUMBER = 5

if __name__ == '__main__':  # main file execution
    with open('roster_log.txt', 'w') as log:  # open logging file
        startTime = datetime.now()
        startTime = startTime.strftime('%H:%M:%S')
        print(f'INFO: Execution started at {startTime}')
        print(f'INFO: Execution started at {startTime}', file=log)
        with oracledb.connect(user=DB_UN, password=DB_PW, dsn=DB_CS) as con:  # create the connecton to the database
            try:
                with con.cursor() as cur:  # start an entry cursor
                    with open(OUTPUT_FILE_NAME, 'w') as output:  # open the output file
                        print("Connection established: " + con.version)
                        print("Connection established: " + con.version, file=log)

                        today = datetime.now()  # get todays date and store it for finding the correct term later
                        # print("today = " + str(today)) #debug

                        # find the term year for the current school year by looking at all terms in whatever building and comparing the terms start and end dates to today's date to find a valid term and store the term year for later
                        cur.execute("SELECT id, firstday, lastday, schoolid, yearid FROM terms WHERE IsYearRec = 1 AND schoolid = :school ORDER BY dcid DESC", school=TERMYEAR_SCHOOL_NUMBER)  # get a list of terms for a building, filtering to only full years
                        termRows = cur.fetchall()
                        termyear = None
                        for term in termRows:
                            print(f'DBUG: Found term {term}', file=log)  # debug to see the terms
                            if (term[1] - dt.timedelta(days=30) < today) and term[2] > today:  # add two months past the end date to cover for the summer
                                termyear = str(term[4])  # store the yearid as the term year we really look for in each student
                                print(f'DBUG: Term year is set to {termyear}') 
                                print(f'DBUG: Term year is set to {termyear}', file=log)

                        if termyear:
                            print('CC.COURSE_NUMBER,CC.SECTION_NUMBER,CC.TERMID,CC.SCHOOLID,CC.EXPRESSION,CC.DATEENROLLED,CC.DATELEFT,COURSES.COURSE_NAME,SECTIONS.ROOM,TEACHERS.EMAIL_ADDR,U_STUDENTSUSERFIELDS.custom_student_email,STUDENTS.STUDENT_NUMBER,STUDENTS.ENTRYDATE,STUDENTS.EXITDATE,STUDENTS.ENROLL_STATUS,SCHOOLS.ABBREVIATION', file=output)  # print the header rows into the output file
                            # do a query for active students, get their enroll infor as well as the school abbreviation
                            cur.execute('SELECT students.student_number, students.entrydate, students.exitdate, students.enroll_status, students.schoolid, schools.abbreviation, students.id FROM students LEFT JOIN schools on students.schoolid = schools.school_number WHERE students.enroll_status = 0')
                            studentRows = cur.fetchall()
                            for student in studentRows:
                                try:
                                    print(f'DBUG: Starting student {student[0]} at building {student[4]} - {student[5]}, enroll status {student[3]}')  # debug
                                    print(f'DBUG: Starting student {student[0]} at building {student[4]} - {student[5]}, enroll status {student[3]}', file=log)  # debug
                                    idNum = str(int(student[0]))
                                    stuEntry = student[1].strftime('%Y-%m-%d')  # convert the full datetime value to just yyyy-mm-dd
                                    stuExit = student[2].strftime('%Y-%m-%d')  # convert the full datetime value to just yyyy-mm-dd
                                    stuEnroll = str(student[3])
                                    schoolID = str(student[4])
                                    school = str(student[5])
                                    internalID = str(student[6])
                                    stuEmail = idNum + EMAIL_SUFFIX  # append email suffix to their student ID to get email

                                    try:
                                        # find terms for the current student in the termyear found initially
                                        cur.execute('SELECT id, dcid FROM terms WHERE yearid = :year AND schoolid = :school', year=termyear, school=schoolID)  # using bind variables as best practice https://python-oracledb.readthedocs.io/en/latest/user_guide/bind.html#bind
                                        termRows = cur.fetchall()
                                        for term in termRows:
                                            termID = str(term[0])
                                            termDCID = str(term[1])
                                            print(f'DBUG: {idNum} has good term for school {schoolID}: {termID} | {termDCID}')
                                            print(f'DBUG: {idNum} has good term for school {schoolID}: {termID} | {termDCID}', file=log)
                                            # now for each term that is valid, do a query for all their courses and start processing them
                                            try:
                                                cur.execute('SELECT cc.course_number, cc.section_number, cc.termid, cc.schoolid, cc.expression, cc.dateenrolled, cc.dateleft, cc.teacherid, cc.sectionid, courses.course_name FROM cc LEFT JOIN courses ON cc.course_number = courses.course_number WHERE cc.termid = :term AND cc.studentid = :internalID', term=termID, internalID=internalID)
                                                courseRows = cur.fetchall()
                                                for course in courseRows:
                                                    # print(course)
                                                    # print(course, file=log)
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

                                                    cur.execute("SELECT users_dcid FROM schoolstaff WHERE id = :teacherID", teacherID=courseTeacherID)  # get the user dcid from the teacherid in schoolstaff
                                                    schoolStaffInfo = cur.fetchall()
                                                    # print(schoolStaffInfo, file=log) # debug
                                                    teacherDCID = str(schoolStaffInfo[0][0])  # just get the result directly without converting to list or doing loop

                                                    cur.execute("SELECT email_addr FROM teachers WHERE users_dcid = :teacherDCID", teacherDCID=teacherDCID)  # get the teacher number from the teachers table for that user dcid
                                                    teacherInfo = cur.fetchall()
                                                    # print(teacherInfo, file=log)  # debug
                                                    teacherEmail = str(teacherInfo[0][0])  # just get the result directly without converting to list or doing loop

                                                    cur.execute("SELECT room FROM sections WHERE id = :sectionID", sectionID=courseSectionID)  # get the room number assigned to the sectionid correlating to our home_room
                                                    roomRows = cur.fetchall()
                                                    roomNumber = str(roomRows[0][0])
                                                    if(teacherEmail != 'None'):  # some attendance/commons classes do not have teachers listed, we dont want to print them
                                                        print(f'{courseNum},{sectionNum},{courseTerm},{courseSchool},{courseExpression},{courseEnrolled},{courseLeft},{courseName},{roomNumber},{teacherEmail},{stuEmail},{idNum},{stuEntry},{stuExit},{stuEnroll},{school}', file=output)

                                            except Exception as er:
                                                print(f'ERROR while processing courses for student {idNum}: {er}')
                                                print(f'ERROR while processing courses for student {idNum}: {er}', file=log)
                                    except Exception as er:
                                        print(f'ERROR while finding term for student {student[0]}: {er}')
                                        print(f'ERROR while finding term for student {student[0]}: {er}', file=log)
                                except Exception as er:
                                    print(f'ERROR while processing student {student[0]}: {er}')
                                    print(f'ERROR while processing student {student[0]}: {er}', file=log)
                        else:
                            print(f'WARN: Could not find a valid term for todays date of {today}, ending execution')
                            print(f'WARN: Could not find a valid term for todays date of {today}, ending execution', file=log)
                            sys.exit()
            except Exception as er:
                print(f'ERROR while doing initial PowerSchool query or file handling: {er}')
                print(f'ERROR while doing initial PowerSchool query or file handling: {er}', file=log)
        try:
            #after all the files are done writing and now closed, open an sftp connection to the server and place the file on there
            with pysftp.Connection(SFTP_HOST, username=SFTP_UN, password=SFTP_PW, cnopts=CNOPTS, port=2225) as sftp:
                print(f'INFO: SFTP connection to LittleSIS at {SFTP_HOST} successfully established')
                print(f'INFO: SFTP connection to LittleSIS at {SFTP_HOST} successfully established', file=log)
                # print(sftp.pwd)  # debug to list current working directory
                # print(sftp.listdir())  # debug to list files and directory in current directory
                sftp.put(OUTPUT_FILE_NAME)  # upload the file onto the sftp server
                print("INFO: Roster file placed on remote server")
                print("INFO: Roster file placed on remote server", file=log)
        except Exception as er:
            print(f'ERROR while connecting or uploading to LittleSIS SFTP server: {er}')
            print(f'ERROR while connecting or uploading to LittleSIS SFTP server: {er}', file=log)

        endTime = datetime.now()
        endTime = endTime.strftime('%H:%M:%S')
        print(f'INFO: Execution ended at {endTime}')
        print(f'INFO: Execution ended at {endTime}', file=log)

