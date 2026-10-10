import urllib.request
r = urllib.request.urlopen('http://127.0.0.1:8000/')
d = r.read().decode()
print('FIRST 800 CHARS:')
print(d[:800])
print('---END---')