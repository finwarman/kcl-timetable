#!/usr/bin/env python
'''
Fetch Calendar from King's App

Version 2019-02-25.22

To Do:
Add command line args for date range, etc.
'''

import xml.etree.ElementTree as ET
from datetime import datetime
from datetime import timedelta
from getpass import getpass
import sys
import os
import re
import keyring
import requests
import crayons

# keyring namespace for this app
SERVICE_ID = 'kcl_timetable'
KNUM_REG_PATTERN = re.compile("[k|K]\d{7}")

file_path = "knumber.fin"
if not os.path.isfile(file_path):
    open("knumber.fin", "w").close()

with open("knumber.fin", "r+") as unamefile:
    uname = unamefile.read()

    if(bool(KNUM_REG_PATTERN.match(uname)) == False):
        print("No K-Number Saved.")

        while bool(KNUM_REG_PATTERN.match(uname)) == False:
            print("Please enter a valid K-Number:")
            uname = input()

        unamefile.write(uname)

        pwd = getpass("Enter your password: ")
        keyring.set_password(SERVICE_ID, uname, pwd)

unamefile.close()

password = keyring.get_password(SERVICE_ID, uname)  # retrieve password

UNAME = uname
PASSWD = password

# STARTDATE = (datetime.utcnow() - timedelta(days=1)).isoformat()
STARTDATE = (datetime.utcnow().replace(
    hour=0, minute=0, second=0, microsecond=0)).isoformat()
ENDDATE = (datetime.utcnow() + timedelta(days=7)).isoformat()

XML_BODY = '''<retrieveCalendar xmlns="http://campusm.gw.com/campusm">
	            <username>{}</username>
	            <password>{}</password>
	            <calType>course_timetable</calType>
	            <start>{}</start>
	            <end>{}</end>
            </retrieveCalendar>'''.format(UNAME, PASSWD, STARTDATE, ENDDATE)

APP_REQ_HEADERS = {
    'Host':	            'campusm.kcl.ac.uk',
    'Content-Type':	    'application/xml',
    'Accept-Encoding':	'gzip',
    'Pragma':	        'no-cache',
    'User-Agent':	    '''King's%20Mobile/9081458 CFNetwork/978.0.7 Darwin/18.7.0''',
    'Content-Length':	'291',
    'Accept':       	'*/*',
    'Accept-Language':	'en-gb',
    'Authorization':	'''Basic YXBwbGljYXRpb25fc2VjX3VzZXI6ZjJnaDUzNDg=''',
    'Cache-Control':	'no-cache',
    'Connection':	    'keep-alive'
}

'''
    Authorization:	Basic YXBwbGljYXRpb25fc2VjX3VzZXI6ZjJnaDUzNDg=

    This is base64 encoded, for HTTP 'Basic' authentication scheme in headers,
    https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Authorization
    When decoded it reads:
    application_sec_user:f2gh5348

    I'd like to try another user login to see if this token is unique?
'''

XML_RESPONSE = ""
try:
    XML_RESPONSE = requests.post(
        'https://campusm.kcl.ac.uk//kclNewTimetable/services/CampusMUniversityService/retrieveCalendar',
        data=XML_BODY, headers=APP_REQ_HEADERS, verify=True).text
except:
    try:
        XML_RESPONSE = requests.post(
            'https://campusm.kcl.ac.uk//kclNewTimetable/services/CampusMUniversityService/retrieveCalendar',
            data=XML_BODY, headers=APP_REQ_HEADERS, verify=False).text
        print("Was unable to verify SSL Cert. Disabled 'verify=True' flag for Request")
    except:
        print("Unable to connect - check internet connection and try again?")
        sys.exit(0)


ROOT = ET.fromstring(XML_RESPONSE)
CALITEMS = (list(list(ROOT)[0]))

dates = {}

for item in CALITEMS:
    calentry = {}
    for field in list(item):
        calentry[field.tag.replace(
            '{http://campusm.gw.com/campusm}', '')] = field.text

    date_time_str = calentry['end']
    date_time_obj = datetime.fromisoformat(date_time_str)
    calentry['end'] = date_time_obj

    date_time_str = calentry['start']
    date_time_obj = datetime.fromisoformat(date_time_str)
    calentry['start'] = date_time_obj

    date_key = date_time_obj.strftime("%Y-%m-%d")

    if('/Tut/' in calentry['desc1']):
        calentry['type'] = 'Large Group Tut.'
    elif('/Discussion/' in calentry['desc1']):
        calentry['type'] = 'Discussion'
    elif('/Prac/' in calentry['desc1']):
        calentry['type'] = 'Practical/Lab'
    elif('/Lecture' in calentry['desc1']):
        calentry['type'] = 'Lecture'
    elif('/SmG/' in calentry['desc1']):
        calentry['type'] = 'Small Group Tut.'
    else:
        calentry['type'] = 'Lesson'

    dates.setdefault(date_key, []).append(calentry)

for key in sorted(dates.keys(), reverse=True):  # Top to bottom flag
    print()
    dt = datetime.strptime(key, '%Y-%m-%d')
    if dt.date() == datetime.today().date():
        date_str = dt.strftime("%a %d %b %Y") + " (Today)"
    elif dt.date() == (datetime.today().date() + timedelta(days=1)):
        date_str = dt.strftime("%a %d %b %Y") + " (Tomorrow)"
    elif dt.date() == (datetime.today().date() - timedelta(days=1)):
        date_str = dt.strftime("%a %d %b %Y") + " (Yesterday)"
    else:
        date_str = dt.strftime("%a %d %b %Y")

    print(
        crayons.green(date_str, bold=True)
    )

    events = dates[key]
    for event in sorted(events, key=lambda k: k['start']):
        if dt.date() <= datetime.today().date() and event.get('start', '00:00') < datetime.utcnow().strftime("%H:%M"):
            print('    {} - {}\t\t{}\n  ↳ {}   {}\n'.format(
                crayons.blue(
                    event.get('start', 'No Start Time Given'), bold=True),
                crayons.blue(
                    event.get('end', 'No End Time Given'), bold=True),
                event.get('type', 'Lesson Type'),
                '{:<25}'.format(event.get('desc2', 'Description')[:25]),
                event.get('locAdd1', 'Location')
            ))
        else:
            print('    {} - {}\t\t{}\n  ↳ {}   {}\n'.format(
                crayons.magenta(
                    event.get('start', 'No Start Time Given'), bold=True),
                crayons.magenta(
                    event.get('end', 'No End Time Given'), bold=True),
                event.get('type', 'Lesson Type'),
                '{:<25}'.format(event.get('desc2', 'Description')[:25]),
                event.get('locAdd1', 'Location')
            ))

print("It is currently ", end="")
print(
    crayons.magenta("{}".format(
        datetime.utcnow().strftime("%H:%M")), bold=True), end=""
)
print(" on ", end="")
print(
    crayons.green("{}".format(
        datetime.utcnow().strftime("%a %d %b %Y")), bold=True), end=""
)
print('\n')

sys.exit

'''
<retrieveCalendar xmlns = "http://campusm.gw.com/campusm" >
	            <username > {} < /username >
	            <password > {} < /password >
	            <calType > course_timetable < /calType >
	            <start > 2019-02-25T00: 00: 00.000+00: 00 < /start >
	            <end > 2019-03-04T00: 00: 00.000+00: 00 < /end >
            </retrieveCalendar>
'''
