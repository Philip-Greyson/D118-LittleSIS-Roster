
# D118-LittleSIS-Roser

Script to export class section info for all students to a .csv which is uploaded to LittleSIS.

## Overview

The script first finds the current  term year by taking terms from any school and comparing their start and end dates against the current date. Then a query is done for all actively enrolled students in PowerSchool, getting their basic information. Their current terms for the year are found using their school information and the term year found at the start, then their courses are retrieved for those terms. For each course, the teacher information such as name and email, as well as section information such as room number are retrieved and then the information about the course is output to the .csv file.
Once all students are processed, the .csv file is uploaded via SFTP to the LittleSIS server.

## Requirements

The following Environment Variables must be set on the machine running the script:

- POWERSCHOOL_READ_USER
- POWERSCHOOL_DB_PASSWORD
- POWERSCHOOL_PROD_DB
- LITTLESIS_SFTP_USERNAME
- LITTLESIS_SFTP_PASSWORD
- LITTLESIS_SFTP_ADDRESS

These are fairly self explanatory, and just relate to the usernames, passwords, and host IP/URLs for PowerSchool and the LittleSIS SFTP server (provided by them). If you wish to directly edit the script and include these credentials, you can.

Additionally, the following Python libraries must be installed on the host machine (links to the installation guide):

- [Python-oracledb](https://python-oracledb.readthedocs.io/en/latest/user_guide/installation.html)
- [pysftp](https://pypi.org/project/pysftp/)

**As part of the pysftp connection to the output SFTP server, you must include the server host key in a file** with no extension named "known_hosts" in the same directory as the Python script. You can see [here](https://pysftp.readthedocs.io/en/release_0.2.9/cookbook.html#pysftp-cnopts) for details on how it is used, but the easiest way to include this I have found is to create an SSH connection from a linux machine using the login info and then find the key (the newest entry should be on the bottom) in ~/.ssh/known_hosts and copy and paste that into a new file named "known_hosts" in the script directory.

## Customization

This script should mostly work for any district that uses PowerSchool and LittleSIS, as it uses standard tables/fields and exports in the format LittleSIS wants. However, there are a few things you will need to change or want to change depending on your situation:

- `EMAIL_SUFFIX` is obvious, it is the way the emails are constructed. In our district it is the student number and then the suffix, if you use something like firstlast you will also need to change `stuEmail = idNum + EMAIL_SUFFIX` to use the relevant fields instead of the student ID number.
- `OUTPUT_FILE_NAME` defines the file name for the export file, change it if needed.
- `TERMYEAR_SCHOOL_NUMBER` needs to be the school ID for a school that has terms for the current year, but it does not matter which one. It is just used to find the term year value for the current year.
- If for some reason you want to limit it to only full year classes, you can add `IsYearRec=1` to the SQL query starting with `cur.execute('SELECT id, dcid FROM terms...)` to limit to only full year terms.
