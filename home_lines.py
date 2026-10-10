f = open('C:/Users/saiku/OneDrive/Desktop/BEREADY_BOY/frontend/js/home.js', 'r', encoding='utf-8')
content = f.read()
f.close()

# Print lines 40-83 to see the full code
lines = content.split('\n')
for i, line in enumerate(lines[39:83], start=40):
    print(f"{i}: {line}")