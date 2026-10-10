import urllib.request
r = urllib.request.urlopen('http://127.0.0.1:8000/')
d = r.read().decode()
print('Looking for class="card":', 'class="card"' in d)
print('Looking for class="hero{":', 'class="hero{' in d)
# Find where class= appears
idx = d.find('class=')
if idx != -1:
    print('class= found at', idx, ':', d[idx:idx+80])