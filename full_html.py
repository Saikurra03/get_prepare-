import urllib.request
r = urllib.request.urlopen('http://127.0.0.1:8000/')
d = r.read().decode()
# Print the full HTML to examine
print(d)