import os

dir_path = 'C:/Users/saiku/OneDrive/Desktop/BEREADY_BOY/frontend/js'
issues = []

for f in os.listdir(dir_path):
    if f.endswith('.js'):
        path = os.path.join(dir_path, f)
        try:
            content = open(path, 'r', encoding='utf-8').read()
            if 'hero{' in content:
                issues.append(f"{f}: FOUND broken hero{{ pattern")
        except:
            pass

if issues:
    print("ISSUES FOUND:")
    for i in issues:
        print("  " + i)
else:
    print("OK: No broken hero{ patterns found in any JS file")

print()
print("=== CHECKING FIXED files HAVE class=\"card\" ===")

for f in ['home.js', 'hub.js']:
    path = os.path.join(dir_path, f)
    try:
        content = open(path, 'r', encoding='utf-8').read()
        if 'class="card"' in content:
            print(f"OK: {f} has class=\"card\"")
        else:
            print(f"ISSUE: {f} missing class=\"card\"")
    except Exception as e:
        print(f"ERROR reading {f}: {e}")