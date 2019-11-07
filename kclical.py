#!/usr/bin/env python3
'''
Parse King's Calender to iCal format
Version 2019-02-25.22
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
from icalendar import Calendar, Event


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

password = keyring.get_password(SERVICE_ID, uname)  # retrieve password4

UNAME = uname
PASSWD = password

# STARTDATE = (datetime.utcnow() - timedelta(days=1)).isoformat()
STARTDATE = (datetime.utcnow().replace(
    hour=0, minute=0, second=0, microsecond=0)).isoformat()
ENDDATE = (datetime.utcnow() + timedelta(days=240)).isoformat()

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

cal = Calendar()

for key in sorted(dates.keys(), reverse=True):  # Top to bottom flag
    dt = datetime.strptime(key, '%Y-%m-%d')
    events = dates[key]

    for row in events:
        event = Event()
        event.add('description', row['desc1']+' - ' +
                  row.get('teacherName', 'Teaching Assistant'))
        event.add('dtstart', row['start'])
        event.add('dtend', row['end'])
        # event.add('summary', row['type']+' - '+row['desc2'])
        event.add('summary', row.get('desc2', 'Description'))
        event.add('location', row['locAdd1'])
        cal.add_component(event)

desktop = os.path.expanduser("~/Desktop")
timestamp = (datetime.now().strftime("%b%Y-%H_%M_%S")).lower()
calendar_path = "" + desktop + "/course_schedule_" + timestamp + ".ics"

f = open(calendar_path, 'wb')
f.write(cal.to_ical())
f.close()

print("Exported to " + calendar_path)

print("Opening in calendar...")
os.system('open ' + calendar_path)
print("Done! Goodbye :)")

sys.exit
