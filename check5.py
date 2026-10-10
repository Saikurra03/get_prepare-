import urllib.request
r = urllib.request.urlopen('http://127.0.0.1:8000/')
d = r.read().decode()
idx = d.find('class=')
if idx != -1:
    print('class= found at', idx, ':', repr(d[idx:idx+100]))
else:
    print('no class= found')

idx2 = d.find('hero{')
if idx2 != -1:
    print('hero{ found at', idx2)
else:
    print('hero{ NOT found')

idx3 = d.find('class="card')
if idx3 != -1:
    print('class="card" found at', idx3)
else:
    print('class="card" NOT found')