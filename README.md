# LITTLESIS STUDENT ROSTER  

Script to take classes from PowerSchool and put them into a csv file for upload to LittleSIS.  
Basically just a bunch of SQL queries, the results are massaged a tiny bit to get the email and a few other fields format correct.  
Also "intelligently" finds the correct term/year based on today's date, so it should not need updating each year. Could also be customized to only do the current quarter, semester, etc.  
Then outputs one class per line to the littlesis_roster.csv file which is then uploaded to the LittleSIS SFTP server.  

I could certainly optimize it with fewer SQL queries by combining them more, but speed is not really a concern and the readability is better.  
Also experimented with multiprocessing but was getting many SQL errors when they were trying to execute multiple requests at the same time.  
Maybe I will look into it more later.  

In order to use you will need the following  

- Python (created and tested on Python 3.10.6) installed on the host <https://www.python.org/downloads/release/python-3106/>  
- A PowerSchool server that has its database accessible to the host this script is running on
- The connection info of the PowerSchool server and the LittleSIS SFTP server stored as environment variables on the host
- The oracledb driver/library installed on the host <https://python-oracledb.readthedocs.io/en/latest/user_guide/installation.html>
- The pysftp library on the host <https://pysftp.readthedocs.io/en/release_0.2.9/>
- The hostkey for the LittleSIS SFTP server saved to a file called known_hosts in the same directory as the python script
  - I do this by manually generating an ssh connection in the linux terminal and then copying from ~/.ssh/known_hosts to the file to transfer to a windows host
