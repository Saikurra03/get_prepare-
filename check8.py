f = open('C:/Users/saiku/OneDrive/Desktop/BEREADY_BOY/frontend/js/home.js', 'r', encoding='utf-8')
content = f.read()
f.close()
# Find the innerHTML assignment
idx = content.find('page.innerHTML')
if idx != -1:
    print("innerHTML found at", idx)
    # Print from the template literal start
    idx2 = content.find('`', idx)
    if idx2 != -1:
        print("Template section:")
        print(content[idx2:idx2+300])
else:
    print("no innerHTML found")
    
# Check for hero{
if 'hero{' in content:
    print("FOUND hero{ in home.js")
else:
    print("NO hero{ in home.js - GOOD")

# Check for class="card"
if 'class="card"' in content:
    print("FOUND class=\"card\" in home.js - GOOD")
else:
    print("NO class=\"card\" in home.js")