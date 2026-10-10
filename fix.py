#!/usr/bin/env python3
"""Fix the blank page caused by malformed HTML in home.js"""

with open('frontend/js/home.js', 'r', encoding='utf-8') as f:
    content = f.read()

# The exact broken block found at index 138
# Replace class="hero{ with class="card" and move styles to style attribute
old_block = '''class="hero{\n    background:var(--glass-card);\n    backdrop-filter:blur(var(--glass-blur));\n    border-radius:var(--radius-lg);\n    padding:var(--space-lg)var(--space-xl);\n    margin-bottom:var(--space-lg);'''

new_block = '''class="card" style="background:var(--glass-card);backdrop-filter:blur(var(--glass-blur));border-radius:var(--radius-lg);padding:var(--space-lg)var(--space-xl);margin-bottom:var(--space-lg);'''

if old_block in content:
    content = content.replace(old_block, new_block)
    with open('frontend/js/home.js', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: home.js fixed - replaced malformed hero{ with card + inline style")
else:
    print("OLD BLOCK NOT MATCHED - trying alternative")
    # Try simpler replacement
    content = content.replace('class="hero{', 'class="card"')
    with open('frontend/js/home.js', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Applied simple fix: replaced class=\"hero{ with class=\"card\"")