#!/usr/bin/env python3
"""Update BEREADY styles.css from glassmorphism to claymorphism"""

with open('frontend/styles.css', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the .card rule
old_card = """.card{background:var(--glass-card);
  -webkit-backdrop-filter:blur(var(--glass-blur));backdrop-filter:blur(var(--glass-blur));
  border:var(--glass-border);border-radius:var(--r);
  box-shadow:var(--shadow), var(--glass-rim), var(--ring);
  padding:16px 18px;position:relative}"""
new_card = """.card{background:var(--clay-card);border-radius:var(--radius-lg);padding:16px 18px;position:relative;box-shadow:var(--clay-shadow-lg)}"""
if old_card in content:
    content = content.replace(old_card, new_card)
    print(".card rule replaced")
else:
    print(".card NOT FOUND")

# Replace the .btn and input rules
old_btn = """button,.btn{background:var(--glass-card);color:var(--ink);border:var(--glass-border);
  border-radius:10px;padding:9px 15px;font-weight:600;font-size:14px;cursor:pointer;
  text-decoration:none;display:inline-block;font-family:var(--font);
  box-shadow:var(--glass-rim), var(--shadow-soft);}
button:hover,.btn:hover{background:var(--btn-hover);border-color:var(--btn-hover-bd)}
button.primary,.btn.primary{background:var(--acc);border-color:var(--acc);color:#fff;
  box-shadow:0 1px 2px rgba(47,111,237,.3)}
button.primary:hover,.btn.primary:hover{background:var(--acc-hov);border-color:var(--acc-hov)}
button.ghost,.btn.ghost{background:transparent;box-shadow:none;border-color:var(--line)}
button.ghost:hover,.btn.ghost:hover{background:var(--press)}
button.danger,.btn.danger{border-color:var(--bad-bd);color:var(--danger-ink);background:var(--bad-bg)}
button:disabled{opacity:.5;cursor:default}
select,input[type=text],input[type=number],textarea{background:var(--glass-input);color:var(--ink);
  border:1px solid var(--hair);border-radius:10px;padding:9px 12px;font-size:14px;font-family:var(--font);
  -webkit-backdrop-filter:blur(var(--glass-blur));backdrop-filter:blur(var(--glass-blur))}
select:focus,input:focus,textarea:focus{outline:none;border-color:var(--acc);box-shadow:0 0 0 3px var(--acc-soft)}
label.fl{display:block;font-size:12.5px;color:var(--mut);margin:10x 0 4px;font-weight:600}
input[type=file]{font-size:13px;color:var(--mut)}"""

new_btn = """/* ---------- controls ---------- */
button,.btn{background:var(--clay-card);color:var(--ink);border:var(--line);
  border-radius:12px;padding:9px 15px;font-weight:600;font-size:14px;cursor:pointer;
  text-decoration:none;display:inline-block;font-family:var(--font);
  box-shadow:var(--clay-shadow-md)}
button:hover,.btn:hover{background:var(--surface-strong);border-color:rgba(255,255,255,0.12)}
button.primary,.btn.primary{background:var(--acc);border-color:var(--acc);color:#fff;
  box-shadow:0 1px 2px rgba(20,184,166,.3)}
button.primary:hover,.btn.primary:hover{background:var(--acc-hover);border-color:var(--acc-hover)}
button.ghost,.btn.ghost{background:transparent;box-shadow:none;border-color:var(--line)}
button.ghost:hover,.btn.ghost:hover{background:rgba(255,255,255,.05)}
button.danger,.btn.danger{border-color:var(--bad-bd);color:var(--danger-ink);background:var(--bad-bg)}
button:disabled{opacity:.5;cursor:default}
select,input[type=text],input[type=number],textarea{background:rgba(255,255,255,.05);color:var(--ink);
  border:1px solid var(--line);border-radius:12px;padding:9px 12px;font-size:14px;font-family:var(--font);
  box-shadow:var(--clay-shadow-sm)}
select:focus,input:focus,textarea:focus{outline:none;border-color:var(--acc);box-shadow:0 0 0 3px var(--acc-soft)}
label.fl{display:block;font-size:12.5px;color:var(--ink-muted);margin:10px 0 4px;font-weight:600}
input[type=file]{font-size:13px;color:var(--mut)}"""

if old_btn in content:
    content = content.replace(old_btn, new_btn)
    print("Button/.btn rules replaced")
else:
    print("OLD BTN NOT FOUND - trying partial match")
    # Check if any part matches
    if 'button,.btn{' in content:
        print("  'button,.btn{' found in file")

# Replace the .card rule
old_card2 = """.card{background:var(--glass-card);
  -webkit-backdrop-filter:blur(var(--glass-blur));backdrop-filter:blur(var(--glass-blur));
  border:var(--glass-border);border-radius:var(--r);
  box-shadow:var(--shadow), var(--glass-rim), var(--ring);
  padding:16px 18px;position:relative}"""
new_card2 = """.card{background:var(--clay-card);border-radius:var(--radius-lg);padding:16px 18px;position:relative;box-shadow:var(--clay-shadow-lg)}"""
if old_card2 in content:
    content = content.replace(old_card2, new_card2)
    print(".card rule (second) replaced")
else:
    print(".card rule (second) NOT FOUND")

# Replace the .transcript rule
old_transcript = """.transcript{min-height:110px;background:var(--glass-card);border:var(--glass-border);
  box-shadow:var(--glass-rim), var(--ring-in);
  -webkit-backdrop-filter:blur(var(--glass-blur));backdrop-filter:blur(var(--glass-blur));
  border-radius:12px;padding:12px;white-space:pre-wrap;font-size:14.5px}"""
new_transcript = """.transcript{min-height:110px;background:var(--clay-card);border:var(--line);
  box-shadow:var(--clay-shadow-md);border-radius:12px;padding:12px;white-space:pre-wrap;font-size:14.5px}"""
if old_transcript in content:
    content = content.replace(old_transcript, new_transcript)
    print(".transcript rule replaced")
else:
    print(".transcript NOT FOUND")

# Replace the .pill rule
old_pill = """.pill{font-size:12px;border:var(--glass-border);border-radius:16px;padding:3px 11px;color:var(--mut);
  background:var(--glass-card);box-shadow:var(--glass-rim), var(--shadow-soft)}"""
new_pill = """.pill{font-size:12px;border:var(--line);border-radius:16px;padding:3px 11px;color:var(--ink-muted);
  background:var(--clay-card)}"""
if old_pill in content:
    content = content.replace(old_pill, new_pill)
    print(".pill rule replaced")
else:
    print(".pill NOT FOUND")

# Replace .mock-pill
old_mock_pill = """.mock-pill{font-size:12px;color:var(--mut);border:var(--glass-border);border-radius:999px;padding:3px 10px;
  background:var(--glass-card);box-shadow:var(--glass-rim), var(--shadow-soft)}"""
new_mock_pill = """.mock-pill{font-size:12px;color:var(--ink-muted);border:var(--line);border-radius:999px;padding:3px 10px;
  background:var(--clay-card)}"""
if old_mock_pill in content:
    content = content.replace(old_mock_pill, new_mock_pill)
    print(".mock-pill rule replaced")
else:
    print(".mock-pill NOT FOUND")

# Replace .mock-stage
old_mock_stage = """.mock-stage{background:var(--glass-card);border:var(--glass-border);
  -webkit-backdrop-filter:blur(var(--glass-blur));backdrop-filter:blur(var(--glass-blur));
  box-shadow:var(--shadow), var(--glass-rim), var(--ring);
  border-radius:var(--r);
  padding:clamp(18px,3vw,34px);display:flex;flex-direction:column;justify-content:center;min-width:0}"""
new_mock_stage = """.mock-stage{background:var(--clay-card);border:var(--line);
  border-radius:var(--r);
  padding:clamp(18px,3vw,34px);display:flex;flex-direction:column;justify-content:center;min-width:0}"""
if old_mock_stage in content:
    content = content.replace(old_mock_stage, new_mock_stage)
    print(".mock-stage rule replaced")
else:
    print(".mock-stage NOT FOUND")

# Replace .mock-side-card
old_mock_side_card = """.mock-side-card{background:var(--glass-card);border:var(--glass-border);border-radius:var(--r);
  -webkit-backdrop-filter:blur(var(--glass-blur));backdrop-filter:blur(var(--glass-blur));
  box-shadow:var(--glass-rim), var(--shadow-soft);
  padding:12px;font-size:13px;color:var(--mut);line-height:1.5}"""
new_mock_side_card = """.mock-side-card{background:var(--clay-card);border:var(--line);border-radius:var(--r);
  padding:12px;font-size:13px;color:var(--mut);line-height:1.5}"""
if old_mock_side_card in content:
    content = content.replace(old_mock_side_card, new_mock_side_card)
    print(".mock-side-card rule replaced")
else:
    print(".mock-side-card NOT FOUND")

# Replace .mock-tx
old_mock_tx = """.mock-tx{flex:1;min-width:240px;min-height:74px;max-height:150px;overflow:auto;
  background:var(--glass-input);border:1px solid var(--hair);border-radius:var(--r-sm);
  padding:10px 12px;outline:none;font-size:14px;line-height:1.5;color:var(--ink);
  -webkit-backdrop-filter:blur(var(--glass-blur));backdrop-filter:blur(var(--glass-blur))}"""
new_mock_tx = """.mock-tx{flex:1;min-width:240px;min-height:74px;max-height:150px;overflow:auto;
  background:rgba(255,255,255,.05);border:1px solid var(--line);border-radius:var(--r-sm);
  padding:10px 12px;outline:none;font-size:14px;line-height:1.5;color:var(--ink)}"""
if old_mock_tx in content:
    content = content.replace(old_mock_tx, new_mock_tx)
    print(".mock-tx rule replaced")
else:
    print(".mock-tx NOT FOUND")

# Replace .qb-list
old_qb_list = """.qb-list{max-height:340px;overflow:auto;border:var(--glass-border);border-radius:12px;
  background:var(--glass-card);padding:6px;
  -webkit-backdrop-filter:blur(var(--glass-blur));backdrop-filter:blur(var(--glass-blur));
  box-shadow:var(--glass-rim), var(--ring-in)}"""
new_qb_list = """.qb-list{max-height:340px;overflow:auto;border:var(--line);border-radius:12px;
  background:var(--clay-card);padding:6px}"""
if old_qb_list in content:
    content = content.replace(old_qb_list, new_qb_list)
    print(".qb-list rule replaced")
else:
    print(".qb-list NOT FOUND")

# Replace .il-pill
old_il_pill = """.il-pill{font-size:12px;color:var(--mut);border:var(--glass-border);border-radius:999px;
  padding:3px 10px;white-space:nowrap;font-variant-numeric:tabular-nums;background:var(--glass-card);
  box-shadow:var(--glass-rim), var(--shadow-soft)}"""
new_il_pill = """.il-pill{font-size:12px;color:var(--ink-muted);border:var(--line);border-radius:999px;
  padding:3px 10px;white-space:nowrap;font-variant-numeric:tabular-nums;background:var(--clay-card)}"""
if old_il_pill in content:
    content = content.replace(old_il_pill, new_il_pill)
    print(".il-pill rule replaced")
else:
    print(".il-pill NOT FOUND")

# Replace .il-stage
old_il_stage = """.il-stage{background:var(--glass-card);border:var(--glass-border);
  -webkit-backdrop-filter:blur(var(--glass-blur));backdrop-filter:blur(var(--glass-blur));
  box-shadow:var(--shadow), var(--glass-rim), var(--ring);
  border-radius:var(--r);
  padding:clamp(18px,3vw,36px);display:flex;flex-direction:column;min-width:0;overflow:auto}"""
new_il_stage = """.il-stage{background:var(--clay-card);border:var(--line);
  border-radius:var(--r);
  padding:clamp(18px,3vw,36px);display:flex;flex-direction:column;min-width:0;overflow:auto}"""
if old_il_stage in content:
    content = content.replace(old_il_stage, new_il_stage)
    print(".il-stage rule replaced")
else:
    print(".il-stage NOT FOUND")

# Replace .il-hint
old_il_hint = """.il-hint{background:var(--glass-card);border:var(--glass-border);border-radius:var(--r);
  -webkit-backdrop-filter:blur(var(--glass-blur));backdrop-filter:blur(var(--glass-blur));
  box-shadow:var(--glass-rim), var(--shadow-soft);
  padding:11px 12px;font-size:13px;color:var(--mut);line-height:1.5}"""
new_il_hint = """.il-hint{background:var(--clay-card);border:var(--line);border-radius:var(--r);
  padding:11px 12px;font-size:13px;color:var(--mut);line-height:1.5}"""
if old_il_hint in content:
    content = content.replace(old_il_hint, new_il_hint)
    print(".il-hint rule replaced")
else:
    print(".il-hint NOT FOUND")

# Replace .il-bottom
old_il_bottom = """.il-bottom{background:var(--glass-chrome);border-top:1px solid var(--glass-line);padding:10px 18px 12px;
  -webkit-backdrop-filter:blur(var(--glass-blur));backdrop-filter:blur(var(--glass-blur));
  box-shadow:var(--shadow-bottom), var(--glass-rim)}"""
new_il_bottom = """.il-bottom{background:var(--clay-bg);border-top:1px solid var(--line);padding:10px 18px 12px}"""
if old_il_bottom in content:
    content = content.replace(old_il_bottom, new_il_bottom)
    print(".il-bottom rule replaced")
else:
    print(".il-bottom NOT FOUND")

# Replace result rules (g4, res-hero, res-score, res-meter, etc.)
old_res = """.g4{grid-template-columns:repeat(4,1fr)}
.res-hero{display:flex;align-items:center;gap:24px;flex-wrap:wrap}
.res-score{font-size:58px;font-weight:800;line-height:1;letter-spacing:-.02em;white-space:nowrap}
.res-of{font-size:16px;font-weight:600;color:var(--mut);margin-left:3px;letter-spacing:0}
.res-meter{flex:1;min-width:220px;display:flex;flex-direction:column;gap:8px}
.meter{height:9px;border-radius:99px;background:var(--track);overflow:hidden;
  border:1px solid var(--glass-line)}
.meter>i{display:block;height:100%;border-radius:99px;
  background:linear-gradient(90deg,var(--acc),var(--acc2))}
.res-tile .k{font-size:11.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--mut);
  font-weight:700;margin-bottom:6px}
.res-tile .v{font-size:27px;font-weight:800;line-height:1.1;margin-bottom:4px}
.res-list{margin:6px 0 0;padding-left:18px}
.res-list li{margin:5px 0;font-size:14px}
.chips{display:flex;gap:8px;flex-wrap:wrap}"""
new_res = """.g4{grid-template-columns:repeat(4,1fr)}
.res-hero{display:flex;align-items:center;gap:24px;flex-wrap:wrap}
.res-score{font-size:58px;font-weight:800;line-height:1;letter-spacing:-.02em;white-space:nowrap}
.res-of{font-size:16px;font-weight:600;color:var(--ink-muted);margin-left:3px;letter-spacing:0}
.res-meter{flex:1;min-width:220px;display:flex;flex-direction:column;gap:8px}
.meter{height:9px;border-radius:99px;background:var(--track);overflow:hidden;
  border:1px solid var(--line)}
.meter>i{display:block;height:100%;border-radius:99px;
  background:linear-gradient(90deg,var(--acc),var(--acc-soft))}
.res-tile .k{font-size:11.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-muted);
  font-weight:700;margin-bottom:6px}
.res-tile .v{font-size:27px;font-weight:800;line-height:1.1;margin-bottom:4px}
.res-list{margin:6px 0 0;padding-left:18px}
.res-list li{margin:5px 0;font-size:14px}
.chips{display:flex;gap:8px;flex-wrap:wrap;align-items:center}"""
if old_res in content:
    content = content.replace(old_res, new_res)
    print("Result rules replaced")
else:
    print("OLD RES NOT FOUND")

# Replace fallback rules - remove them since clay doesn't use backdrop-filter
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

new_fallback = """/* Claymorphism uses solid shadows, not backdrop-filter */"""

if old_fallback in content:
    content = content.replace(old_fallback, new_fallback)
    print("Fallback rules replaced")
else:
    print("OLD FALLBACK NOT FOUND")

# Write the file
with open('frontend/styles.css', 'w', encoding='utf-8') as f:
    f.write(content)
print("File written successfully")
print("Total length:", len(content))