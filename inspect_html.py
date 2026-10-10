import urllib.request
r = urllib.request.urlopen('http://127.0.0.1:8000/')
d = r.read().decode()
# Find home.js script tag and examine
idx1 = d.find('src="js/home.js"')
if idx1 != -1:
    # Get a bit after the script tag
    section = d[idx1:idx1+200]
    print('home.js script tag location:', idx1)
    print('Context:', section)
else:
    print('home.js script tag NOT found')

# Look for any error indicators
if 'error' in d.lower():
    print('Word "error" found in HTML')
    
# Check for div cards
if '<div' in d:
    # Find all divs
    import re
    divs = re.findall(r'<div[^>]+>', d)
    print(f'Total divs in HTML: {len(divs)}')
    for i, div in enumerate(divs[:10]):
        print(f'  Div {i}: {div[:80]}')