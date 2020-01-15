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
import argparse

parser = argparse.ArgumentParser(description='Fetch your KCL timetable on the command line.')
parser.add_argument('-r', '--reset',
                    action="store_true", dest="reset",
                    help="Reset your login credentials", default=False)
args = parser.parse_args()

# keyring namespace for this app
SERVICE_ID = 'kcl_timetable'
KNUM_REG_PATTERN = re.compile("[k|K]\d{7}")

if (args.reset):
    try:
        keyring.delete_password(SERVICE_ID, "knumber")
    except:
        print("No K-Number stored")

    try:
        keyring.delete_password(SERVICE_ID, "password")
    except:
        print("No password stored")


knum = keyring.get_password(SERVICE_ID, "knumber")

if knum == None:
    knum = ""
    while not re.match(KNUM_REG_PATTERN, knum):
        knum = input("Enter a valid K-Number: ")
    pwd = getpass("Enter your password: ")
    keyring.set_password(SERVICE_ID, "knumber", knum)
    keyring.set_password(SERVICE_ID, "password", pwd)

password = keyring.get_password(SERVICE_ID, "password")  # retrieve password

UNAME = knum
PASSWD = password

# STARTDATE = (datetime.utcnow() - timedelta(days=1)).isoformat()
STARTDATE = (datetime.utcnow().replace(
    hour=0, minute=0, second=0, microsecond=0)).isoformat()
ENDDATE = (datetime.utcnow() + timedelta(days=14)).isoformat()

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
    calentry['end'] = date_time_obj.strftime('%H:%M')

    date_time_str = calentry['start']
    date_time_obj = datetime.fromisoformat(date_time_str)
    calentry['start'] = date_time_obj.strftime('%H:%M')

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
    elif('/DROP IN/' in calentry['desc1']):
        calentry['type'] = 'Drop-In Session'
    else:
        calentry['type'] = 'Lesson'

    if('/' in calentry['desc1']):
        m = re.search(r" \w*\/", calentry['desc1'])
        calentry['desc1'] = calentry['desc1'][:m.start()]

    if(calentry['desc2'] == None):
        calentry['desc2'] = calentry['desc1']
    

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
        if dt.date() <= datetime.today().date() and str(event.get('start', '00:00')) < datetime.utcnow().strftime("%H:%M"):
            print('    {} - {}\t\t\t{}\n  ↳ {}   {}\n'.format(
                crayons.blue(
                    event.get('start', 'No Start Time Given'), bold=True),
                crayons.blue(
                    event.get('end', 'No End Time Given'), bold=True),
                crayons.white(event.get('type', 'Lesson Type'),bold=True),
                '{:<25}'.format(event.get('desc2', 'Description')[:25]),
                event.get('locAdd1', 'Location')
            ))
        else:
            print('    {} - {}\t\t\t\t{}\n  ↳ {}   {}\n'.format(
                crayons.magenta(
                    event.get('start', 'No Start Time Given'), bold=True),
                crayons.magenta(
                    event.get('end', 'No End Time Given'), bold=True),
                crayons.white(event.get('type', 'Lesson Type'),bold=True),
                    '{:<41}'.format(event.get('desc2', 'Description')[:41]), 
                    event.get('locAdd1', 'Location')
            ))

# print("It is currently ", end="")
# print(
#     crayons.magenta("{}".format(
#         datetime.utcnow().strftime("%H:%M")), bold=True), end=""
# )
# print(" on ", end="")
# print(
#     crayons.green("{}".format(
#         datetime.utcnow().strftime("%a %d %b %Y")), bold=True), end=""
# )
# print('\n')

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
