# Tailscale Connectivity Guide for LifeGame

Since the "Cyborg Host" runs on your local machine, we need a secure way for your "Physical World" devices (Phone, Home Assistant) to reach it. **Tailscale** creates a private mesh network for this purpose.

## 1. Host Setup (Your PC)
1. Ensure Tailscale is installed: `curl -fsSL https://tailscale.com/install.sh | sh`
2. Login: `sudo tailscale up`
3. Get your IP: `tailscale ip -4`
   - *Example: `100.101.102.103`* - **Memorize this.**

## 2. Phone Setup (Android)
1. Install **Tailscale App** from Play Store.
2. Login with the same account.
3. Enable "Active" (VPN Key icon should appear).
4. Verify: Open Chrome on phone and visit `http://100.101.102.103:8000/`. You should see the FastAPI welcome message.

## 3. Home Assistant Setup (Generic)
If your HA is running on a Raspberry Pi or Docker:
1. It also needs to be on the Tailscale network.
2. **Option A (HASS OS)**: Install the official Tailscale Add-on.
3. **Option B (Docker)**: Run a sidecar container or install on host.

## 4. Testing the Nerve Connection
Once all devices are green in the Tailscale Admin Console:
1. Open Tasker.
2. Create a generic HTTP Request task:
   - **URL**: `http://100.101.102.103:8000/api/nerves/perceive`
   - **Method**: POST
   - **Body**: `{"event_type": "tailscale_ping", "attributes": {"device": "android"}}`
3. Check your FastAPI logs. You should see "⚡ Nerve Signal Received".
