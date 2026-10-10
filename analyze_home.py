f = open('C:/Users/saiku/OneDrive/Desktop/BEREADY_BOY/frontend/js/home.js', 'r', encoding='utf-8')
content = f.read()
f.close()

# Print first 500 chars
print("FIRST 500 CHARS:")
print(content[:500])

# Check for hero{ pattern
idx = content.find('hero{')
if idx != -1:
    print(f"\nFOUND hero{{ at position {idx}")
else:
    print("\nNO hero{{ found - GOOD")

# Check for class="card
idx2 = content.find('class="card"')
if idx2 != -1:
    print(f"FOUND class=\"card\" at position {idx2}")
else:
    print("NO class=\"card\" found")

# Check for div class
idx3 = content.find('<div class=')
if idx3 != -1:
    print(f"FOUND <div class= at position {idx3}")
    print("Context:", repr(content[idx3:idx3+120]))
else:
    print("NO <div class= found")