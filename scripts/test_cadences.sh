#!/usr/bin/env bash
#
# test_cadences.sh — end-to-end cadence smoke test for DevPulse (DB-direct method).
#
# For each cadence (6h, 12h, daily, weekly) it:
#   1. sets users.digest_frequency = <cadence>   (so the digest pulls that lookback window
#      and stamps the matching period_key)
#   2. clears the idempotency guard: DELETE the user's rows in `digests`
#   3. POSTs /internal/digest/{user_id} — the per-user worker, which bypasses the `_is_due`
#      schedule gate and runs generate_and_deliver synchronously (returns after the email sends)
# Then restores your real setting (daily @ 12:00 IST) and prints the resulting digest rows.
#
# Secrets (INTERNAL_CRON_SECRET, SUPABASE_URL, SUPABASE_SERVICE_KEY) are pulled from the live
# Cloud Run service via gcloud — nothing is hardcoded or echoed. Requires: gcloud authed, curl,
# python3.
#
# Usage:  ./scripts/test_cadences.sh
# Each run sends you 4 real emails (one per cadence). ~15-25s each (LLM-bound).

set -euo pipefail

# ── config ───────────────────────────────────────────────────────────────────
USER_ID="f2837764-01b3-43ba-a5e0-e422e9f706c1"
API="https://devpulse-api-813251153590.asia-south1.run.app"
REGION="asia-south1"
SERVICE="devpulse-api"
CADENCES=("6h" "12h" "daily" "weekly")
# restore target (your real preference) — edit if it changes
RESTORE_FREQ="daily"; RESTORE_HOUR=12; RESTORE_TZ="Asia/Kolkata"

# ── pull an env var value out of the deployed Cloud Run service ───────────────
svc_env() {
  gcloud run services describe "$SERVICE" --region "$REGION" --format=json \
    | python3 -c "import json,sys;print(next(e['value'] for e in json.load(sys.stdin)['spec']['template']['spec']['containers'][0]['env'] if e['name']=='$1'))"
}

echo "→ loading secrets from Cloud Run ($SERVICE)…"
SEC="$(svc_env INTERNAL_CRON_SECRET)"
SB_URL="$(svc_env SUPABASE_URL)"
SB_KEY="$(svc_env SUPABASE_SERVICE_KEY)"
[ -n "$SEC" ] && [ -n "$SB_URL" ] && [ -n "$SB_KEY" ] || { echo "✗ failed to load one or more secrets"; exit 1; }
echo "  ok (secret ${#SEC} chars, supabase ${SB_URL})"

# ── supabase REST helpers ─────────────────────────────────────────────────────
sb() {  # sb <METHOD> <path+query> [json-body]
  local method="$1" path="$2" body="${3:-}"
  local args=(-s -X "$method" "$SB_URL/rest/v1/$path"
    -H "apikey: $SB_KEY" -H "Authorization: Bearer $SB_KEY"
    -H "Content-Type: application/json" -H "Prefer: return=minimal")
  [ -n "$body" ] && args+=(-d "$body")
  curl "${args[@]}"
}

set_freq()   { sb PATCH  "users?id=eq.$USER_ID" "{\"digest_frequency\":\"$1\"}"; }
clear_guard(){ sb DELETE "digests?user_id=eq.$USER_ID" >/dev/null; }
trigger()    { curl -s -X POST "$API/internal/digest/$USER_ID" -H "X-Internal-Secret: $SEC"; }

# ── clear idempotency ONCE (the 4 cadences all produce distinct period_keys, so a single
#    up-front wipe both removes today's real rows AND makes the script safely re-runnable) ─────
echo ""
echo "→ clearing idempotency guard (delete this user's digests rows)…"
clear_guard
echo "  cleared"

# ── run each cadence ──────────────────────────────────────────────────────────
for c in "${CADENCES[@]}"; do
  echo ""
  echo "════════ cadence: $c ════════"
  echo "  set frequency=$c"; set_freq "$c" >/dev/null
  echo "  trigger worker → sending…"
  resp="$(trigger)"
  echo "  response: $resp"
  case "$resp" in
    *'"sent":true'*)  echo "  ✅ $c sent — check your inbox" ;;
    *'"sent":false'*) echo "  ⚠️  $c generated but email send returned false (check Resend logs)" ;;
    *)                echo "  ✗ $c unexpected response (see above)" ;;
  esac
  sleep 3
done

# ── show what landed (before the restore wipe) ────────────────────────────────
echo ""
echo "════════ digest rows produced (expect 4 distinct period_keys) ════════"
curl -s "$SB_URL/rest/v1/digests?user_id=eq.$USER_ID&select=period_key,period_start,period_end,email_sent_at&order=created_at.desc" \
  -H "apikey: $SB_KEY" -H "Authorization: Bearer $SB_KEY" | python3 -m json.tool

# ── restore real setting + clean slate ────────────────────────────────────────
echo ""
echo "════════ restoring: $RESTORE_FREQ @ ${RESTORE_HOUR}:00 $RESTORE_TZ ════════"
sb PATCH "users?id=eq.$USER_ID" \
  "{\"digest_frequency\":\"$RESTORE_FREQ\",\"digest_hour\":$RESTORE_HOUR,\"digest_timezone\":\"$RESTORE_TZ\",\"last_digest_at\":null}" >/dev/null
clear_guard   # wipe test rows so the next scheduled run isn't blocked by a test's period_key
echo "  restored; last_digest_at=NULL + test rows cleared → next scheduled ${RESTORE_HOUR}:00 fires normally"

echo ""
echo "done — expect 4 emails (6h / 12h / daily / weekly), each §1-§5 over its own window, §6 fixed 7-day."
