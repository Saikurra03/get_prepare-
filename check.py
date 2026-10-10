import urllib.request
r = urllib.request.urlopen('http://127.0.0.1:8000/')
d = r.read().decode()
has_card = 'class="card"' in d
has_hero = 'class="hero{' in d
print('card class present:', has_card)
print('broken hero{ present:', has_hero)
print('PASS' if has_card and not has_hero else 'FAIL')