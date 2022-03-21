import shelve
import re

with shelve.open("LGData") as db:
    for i in db:
        if ("https://looking.house/action.php?mode=looking_glass&action="
                in i):
            tmp = db[i]
            tmp['cmdValue'].update({'traceroute': 'traceroute'})
            db[i] = tmp