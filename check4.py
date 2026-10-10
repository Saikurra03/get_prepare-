import urllib.request
r = urllib.request.urlopen('http://127.0.0.1:8000/')
d = r.read().decode()
# Search for card in the div
idx = d.find('card')
if idx != -1:
    print('card found at', idx, ':', repr(d[idx:idx+50]))
else:
    print('card NOT found in response')

# Search for hero
idx2 = d.find('hero')
if idx2 != -1:
    print('hero found at', idx2, ':', repr(d[idx2:idx2+50]))
else:
    print('hero NOT found in response')

# Show the div we care about
idx3 = d.find('<div class=')
if idx3 != -1:
    print('div class= found at', idx3, ':', repr(d[idx3:idx3+120]))
else:
    print('div class= NOT found')