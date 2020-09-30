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
from icalendar import Calendar, Event
import argparse

parser = argparse.ArgumentParser(
    description='Download your KCL timetable as a calendar on the command line.')
parser.add_argument('-r', '--reset',
                    action="store_true", dest="reset",
                    help="Reset your login credentials", default=False)
parser.add_argument('--reverse',
                    action="store_true", dest="reverse",
                    help="Print timetable dates in reverse order", default=False)
parser.add_argument('-d', '--days', nargs='?', default='300', const='const',
                    help="The number of days to look ahead")

args = parser.parse_args()

days = 300
if args.days.isnumeric():
    days = int(args.days)
else:
    exit("'days' parameter must be int")

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

if len(dates.keys()) < 1:
    print("\n[No Events Found]\n")
else:
    print("\nExported timetable for the next {} days:".format(days))


cal = Calendar()

for key in sorted(dates.keys(), reverse=True):  # Top to bottom flag
    dt = datetime.strptime(key, '%Y-%m-%d')
    events = dates[key]

    for row in events:
        event = Event()

        start = datetime.combine(
            dt, datetime.strptime(row.get('start', '08:00'), '%H:%M').time()
        )
        end = datetime.combine(
            dt, datetime.strptime(row.get('end', '20:00'), '%H:%M').time()
        )

        event.add('dtstart', start)
        event.add('dtend', end)

        event.add('description', row['desc1']+' - ' +
                  row.get('teacherName', 'Teaching Assistant'))
        # event.add('summary', row['type']+' - '+row['desc2'])
        event.add('summary', row.get('desc2', 'Description'))

        # location data: locAdd1, locCode
        event.add('location', row.get(
            'locAdd1', 'Online/Remote' if 'locCode' not in row else ''))

        uid = '{}{}{}{}'.format(start, end, event.get(
            'location'), event.get('description'))
        uid = ''.join(c for c in uid if (c.isalnum()
                                         or c in '_-'))  # strip to alphanum/_/-
        event.add('uid', uid)

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
