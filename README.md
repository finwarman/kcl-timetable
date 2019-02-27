# kcl-timetable (kcl.py & kclical.py)
## Tools for viewing and exporting your KCL timetable.

For Python3 - To install dependencies paste the following in your terminal:

```
pip3 install crayons
pip3 install requests
pip3 install keyring
pip3 install icalendar
```
---

### iCalendar export:  (kclical.py)

```
python3 /[path]/[to]/kclical.py
```

Then login with your k-number and password - your password will be stored locally and securly in keyring.
If you mistype your login, simply delete the 'knumber.fin' file in the script directory and log in again.

---

### View timetable in terminal:  (kcl.py)

```
python3 /[path]/[to]/kcl.py
```

Login with your k-number and password - your credentials are stored locally for the next time you run it.

To add as a terminal command, add it as an alias, e.g. for macOS:
Edit __~/.bash_profile__, with
```sudo nano ~/.bash_profile__```

then add the the line

> alias timetable='python3 '/[path]/[to]/kcl.py'

---

![kcl.py timetable fetch](https://raw.githubusercontent.com/finwarman/kcl-timetable/master/screenshots/timetable_fetch_kclpy.png "kcl.py Timetable View")
