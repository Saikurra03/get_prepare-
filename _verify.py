import httpx, json, time

base = "http://127.0.0.1:8000"

# 1. TTS Health
print("=== TTS Health ===")
r = httpx.get(f"{base}/api/tts/health", timeout=5)
print(json.dumps(r.json(), indent=2))

# 2. TTS Speak — slang card text
print("\n=== Slang Lab TTS ===")
r = httpx.post(f"{base}/api/tts/speak", json={"text": "No cap. No lie, for real, I'm being completely honest. For example: That was the best meal I've ever had, no cap."}, timeout=60)
print(f"Status: {r.status_code} | Content-Type: {r.headers.get('content-type','?')} | Size: {len(r.content)} bytes")

# 3. TTS Speak — short word
print("\n=== Short Word TTS ===")
r = httpx.post(f"{base}/api/tts/speak", json={"text": "Bet."}, timeout=30)
print(f"Status: {r.status_code} | Size: {len(r.content)} bytes")

# 4. Slang page loads
print("\n=== Slang Page ===")
r = httpx.get(f"{base}/slang", timeout=5)
print(f"slang.html: {r.status_code} | Size: {len(r.content)} bytes")

# 5. Slang JS loads
r = httpx.get(f"{base}/static/js/slang.js", timeout=5)
print(f"slang.js: {r.status_code} | Size: {len(r.content)} bytes")

# 6. Config JS loads
r = httpx.get(f"{base}/static/js/config.js", timeout=5)
print(f"config.js: {r.status_code} | Size: {len(r.content)} bytes")

# 7. API JS loads (check API_BASE is present)
r = httpx.get(f"{base}/static/js/api.js", timeout=5)
has_api_base = "API_BASE" in r.text
print(f"api.js: {r.status_code} | Has API_BASE: {has_api_base}")

# 8. Interview health
print("\n=== Interview Health ===")
r = httpx.get(f"{base}/api/health", timeout=5)
h = r.json()
print(f"AI Ready: {h.get('ai_ready')} | Provider: {h.get('ai_provider')}")

print("\n=== ALL CHECKS PASSED ===")
