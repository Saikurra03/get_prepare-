#!/usr/bin/env python3
"""Final CSS fixes for BEREADY claymorphism conversion"""

with open('frontend/styles.css', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update .bottomnav - make it display none (already hidden on desktop)
# The bottomnav is already display:none on desktop, but let's ensure it's correct
# Actually, let's just replace the glass references in the existing rule
old_bottomnav = """.bottomnav{display:flex;position:fixed;left:0;right:0;bottom:0;z-index:10;background:var(--glass-chrome);
    -webkit-backdrop-filter:blur(var(--glass-blur));backdrop-filter:blur(var(--glass-blur));
    box-shadow:var(--shadow-bottom), var(--glass-rim);
    border-top:1px solid var(--glass-line);padding:6px 4px calc(6px + env(safe-area-inset-bottom))}"""
new_bottomnav = """.bottomnav{display:none}"""
if old_bottomnav in content:
    content = content.replace(old_bottomnav, new_bottomnav)
    print("bottomnav replaced")
else:
    # Try partial match - just the background part
    old_bottomnav2 = """.bottomnav{display:flex;position:fixed;left:0;right:0;bottom:0;z-index:10;background:var(--glass-chrome);
    -webkit-backdrop-filter:blur(var(--glass-blur));backdrop-filter:blur(var(--glass-blur));
    box-shadow:var(--shadow-bottom), var(--glass-rim);
    border-top:1px solid var(--glass-line);padding:6px 4px calc(6px + env(safe-area-inset-bottom))}"""
    if old_bottomnav2 in content:
        content = content.replace(old_bottomnav2, new_bottomnav)
        print("bottomnav (partial) replaced")
    else:
        print("bottomnav NOT FOUND - checking context")
        idx = content.find('.bottomnav{')
        if idx >= 0:
            print("  Found .bottomnav{ at index", idx)
            print("  Context:", repr(content[idx:idx+60]))

# 2. Update .mock-top
old_mock_top = """.mock-top{display:flex;align-items:center;gap:16px;padding:10px 18px;background:var(--glass-chrome);
  -webkit-backdrop-filter:blur(var(--glass-blur));backdrop-filter:blur(var(--glass-blur));
  box-shadow:var(--shadow-top), var(--glass-rim);border-bottom:1px solid var(--glass-line);flex-wrap:wrap}"""
new_mock_top = """.mock-top{display:flex;align-items:center;gap:16px;padding:10px 18px;background:var(--clay-bg);
  border-bottom:1px solid var(--line);flex-wrap:wrap}"""
if old_mock_top in content:
    content = content.replace(old_mock_top, new_mock_top)
    print(".mock-top replaced")
else:
    print(".mock-top NOT FOUND")

# 3. Update .il-bottom
old_il_bottom = """.il-bottom{background:var(--glass-chrome);border-top:1px solid var(--glass-line);padding:10px 18px 12px;
  -webkit-backdrop-filter:blur(var(--glass-blur));backdrop-filter:blur(var(--glass-blur));
  box-shadow:var(--shadow-bottom), var(--glass-rim)}"""
new_il_bottom = """.il-bottom{background:var(--clay-bg);border-top:1px solid var(--line);padding:10px 18px 12px}"""
if old_il_bottom in content:
    content = content.replace(old_il_bottom, new_il_bottom)
    print(".il-bottom replaced")
else:
    print(".il-bottom NOT FOUND")

# 4. Update .il-tx
old_il_tx = """.il-tx{flex:1;min-height:64px;max-height:24vh;overflow:auto;background:var(--glass-input);
  border:1px solid var(--hair);border-radius:var(--r-sm);padding:10px 12px;outline:none;
  -webkit-backdrop-filter:blur(var(--glass-blur));backdrop-filter:blur(var(--glass-blur));
  font-size:14.5px;line-height:1.5;white-space:pre-wrap;color:var(--ink)}"""
new_il_tx = """.il-tx{flex:1;min-height:64px;max-height:24vh;overflow:auto;background:rgba(255,255,255,.05);border:1px solid var(--line);border-radius:var(--r-sm);padding:10px 12px;outline:none;font-size:14.5px;line-height:1.5;white-space:pre-wrap;color:var(--ink)}"""
if old_il_tx in content:
    content = content.replace(old_il_tx, new_il_tx)
    print(".il-tx replaced")
else:
    print(".il-tx NOT FOUND")

# 5. Update fallback rules - remove them since clay doesn't use backdrop-filter
old_fallback = """/* Glass fallbacks – no backdrop-filter support, or the user
   asked the OS for reduced transparency – solid white surfaces.
   ============================================================ */
@supports not ((backdrop-filter:blur(1px)) or (-webkit-backdrop-filter:blur(1px))){
  .sidebar,.topbar,.bottomnav,.mock-top,.mock-bottom,.il-top,.il-bottom{
    -webkit-backdrop-filter:none;backdrop-filter:none;background:var(--solid)}
  .card,.mock-stage,.mock-side-card,.il-stage,.il-hint,.qb-list,.transcript,
  button,.btn,.icon-btn,.ai-pill,.pill,.mock-pill,.il-pill{
    -webkit-backdrop-filter:none;backdrop-filter:none;background:var(--solid-strong)}
}
@media (prefers-reduced-transparency:reduce){
  .sidebar,.topbar,.bottomnav,.mock-top,.mock-bottom,.il-top,.il-bottom,
  .card,.mock-stage,.mock-side-card,.il-stage,.il-hint,.qb-list,.transcript,
  button,.btn,.icon-btn,.ai-pill,.pill,.mock-pill,.il-pill{
    -webkit-backdrop-filter:none;backdrop-filter:none;background:var(--surface)}"""

new_fallback = ""/* Claymorphism uses solid shadows, not backdrop-filter */"""

if old_fallback in content:
    content = content.replace(old_fallback, new_fallback)
    print("Fallback rules replaced")
else:
    print("OLD FALLBACK NOT FOUND - checking context")
    idx = content.find('Glass fallbacks')
    if idx >= 0:
        print("  Found at index", idx)

# 6. Update .il-tx
old_il_tx2 = """.il-tx{flex:1;min-height:64px;max-height:24vh;overflow:auto;background:var(--glass-input);
  border:1px solid var(--hair);border-radius:var(--r-sm);padding:10px 12px;outline:none;
  -webkit-backdrop-filter:blur(var(--glass-blur));backdrop-filter:blur(var(--glass-blur));
  font-size:14.5px;line-height:1.5;white-space:pre-wrap;color:var(--ink)}"""
new_il_tx2 = """.il-tx{flex:1;min-height:64px;max-height:24vh;overflow:auto;background:rgba(255,255,255,.05);border:1px solid var(--line);border-radius:var(--r-sm);padding:10px 12px;outline:none;font-size:14.5px;line-height:1.5;white-space:pre-wrap;color:var(--ink)}"""
if old_il_tx2 in content:
    content = content.replace(old_il_tx2, new_il_tx2)
    print(".il-tx (second) replaced")
else:
    print(".il-tx (second) NOT FOUND")

# Write the file
with open('frontend/styles.css', 'w', encoding='utf-8') as f:
    f.write(content)
print("File written successfully")
print("Total length:", len(content))