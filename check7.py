import urllib.request
r = urllib.request.urlopen("http://127.0.0.1:8000/")
d = r.read().decode()
idx = d.find("<div class=")
if idx != -1:
    print("div found:", repr(d[idx:idx+150]))
else:
    print("no div class= found")