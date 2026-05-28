---
title: "1 token on your wrist: a $40 Claude meter"
description: "A $40 ESP32 smartwatch reads my Claude quota in real time. The trick is that the watch never talks to Claude. An OCI VM pings the API every five minutes with max_tokens 1, reads the quota out of the response headers, and pushes the result through Tailscale, an Android foreground service, and BLE to a wrist."
pubDate: 2026-06-03
tags: [clawdmeter, esp32, ble, tailscale, oci, claude, agentic, finops]
draft: false
heroImage: https://lucianomori.cloud/images/clawdmeter/watch-demo-poster.jpg
heroImageAlt: Close-up of a Waveshare ESP32 smartwatch on a wrist; the AMOLED face shows a green dial reading "5h 47%" with a small orange pixel-art crab mascot in the corner.
heroImageWidth: 1200
heroImageHeight: 1200
heroImageType: image/jpeg
---

<figure class="hero-figure">
  <video src="/images/clawdmeter/watch-demo.mp4" poster="/images/clawdmeter/watch-demo-poster.jpg" autoplay muted loop playsinline width="720" height="720">
    <img src="/images/clawdmeter/watch-demo.gif" alt="A short loop of the Waveshare smartwatch showing the Clawdmeter mascot reacting, then a finger tapping the screen and the face switching to a live green quota gauge reading the Claude five-hour window." />
  </video>
  <figcaption>The watch reacts; the tap switches to the quota readout. Everything behind the glass is bookkeeping.</figcaption>
</figure>

<blockquote class="lead-quote">

**TL;DR.** [OpenClaw on Oracle Cloud](/writing/openclaw-on-oci-free-tier/) was the lesson "the leash is the product." The [town of $0 AI characters](/writing/holtwick-in-a-week/) was the lesson "the gate is the product." This one is `watch → BLE → Android → Tailscale → OCI VM → Claude Haiku 4.5`, and the lesson is that for an AI subscription you already pay for, the response headers are the product. The wrist meter spends exactly one Haiku token per poll, which is approximately one ten-thousandth of a cent. The watch itself cost forty dollars one time. Everything else is plumbing.

</blockquote>

Three weeks of using a personal assistant on Claude made one habit visible: I kept opening a terminal to check whether my five-hour window was full. The dashboard exists. The information exists. The dashboard is just not where my eyes are at 11 a.m. when I am about to fire a long agent run that might burn through the rest of the window. The fix is not more inference. The fix is a glance.

## The watch doesn't run the AI

<figure class="section-figure" aria-hidden="true">
  <svg viewBox="0 0 80 80" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" focusable="false">
    <rect x="6" y="34" width="10" height="12" rx="1" />
    <line x1="16" y1="40" x2="24" y2="40" />
    <rect x="24" y="30" width="14" height="20" rx="1" />
    <line x1="38" y1="40" x2="46" y2="40" />
    <rect x="46" y="26" width="18" height="28" rx="1" />
    <line x1="64" y1="40" x2="72" y2="40" />
    <circle cx="75" cy="40" r="3" fill="currentColor" stroke="none" />
  </svg>
</figure>

The diagram people draw in their head when they hear "AI on a smartwatch" is wrong in a useful way. They imagine the watch running a model. The watch is a forty-dollar Waveshare ESP32-S3 with a 2.06 inch AMOLED. It cannot run a model and is not trying to. What it can do is render a number that some other machine has computed, and let me tap a button.

```
watch  ──BLE──▶  Android phone
                  │
                  └─Tailscale─▶  OCI free-tier VM
                                  │
                                  └─HTTPS─▶  api.anthropic.com
                                              │
                                              └─headers─▶  state.json
                                                            │
                                              ◀────────────┘
                              ◀──HTTP/Tailscale──────────
       ◀──BLE GATT write──────
```

Five hops, four machines, one direction of travel for the actual byte. Inference happens at the far right of the diagram; the four hops to the left are how a single integer ("forty-seven percent") gets to a wrist. The watch firmware speaks a tiny BLE GATT protocol and updates a dial. The Android app is a foreground service that polls an HTTP endpoint on a tailnet and writes whatever it gets to the watch's RX characteristic. The OCI VM runs a systemd timer that pings Anthropic every five minutes and writes a JSON file. The Claude API tier is the only piece of paid infrastructure in the chain, and it is paid in the broader subscription, not per ping.

The generalized lesson, before the trick that follows: a wearable does not need to host inference to feel intelligent. It needs to render *state* that was computed somewhere with enough resources to compute it cheaply. If you can name the state, the watch is a peripheral and the question is how to keep it fed without burning what you are trying to measure.

## One token, full state

<figure class="section-figure" aria-hidden="true">
  <svg viewBox="0 0 80 80" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" focusable="false">
    <circle cx="26" cy="40" r="14" />
    <text x="26" y="46" font-size="14" fill="currentColor" stroke="none" text-anchor="middle" font-family="ui-monospace, monospace" font-weight="700">1</text>
    <line x1="42" y1="40" x2="68" y2="40" />
    <polyline points="62 34 68 40 62 46" />
  </svg>
</figure>

The first version of the poller asked Claude for a one-sentence summary every five minutes. Roughly thirty tokens out per poll, two hundred and eighty-eight polls a day, eight thousand six hundred forty tokens of Haiku spent per day to find out how much Claude was left. It worked, but it was funny. The meter was burning what it was measuring.

The fix is structural. Anthropic's API returns the rate-limit state of your account in the *response headers*, before the model has produced any meaningful body. You do not need any output to know how much of your window you have used. You need the round-trip to complete. So the poller sends the minimum body that the endpoint accepts, with `max_tokens: 1`, and reads the headers off the response.

```python
API_BODY = {
    "model": "claude-haiku-4-5-20251001",
    "max_tokens": 1,
    "messages": [{"role": "user", "content": "hi"}],
}
# ... fire request, then ...
payload = {
    "s":  pct("anthropic-ratelimit-unified-5h-utilization"),
    "sr": mins("anthropic-ratelimit-unified-5h-reset"),
    "w":  pct("anthropic-ratelimit-unified-7d-utilization"),
    "wr": mins("anthropic-ratelimit-unified-7d-reset"),
    "st": resp_headers.get("anthropic-ratelimit-unified-5h-status", "allowed"),
}
```

Two hundred and eighty-eight tokens a day total, of the cheapest model on the menu. Mathematically negligible against a Claude subscription. The watch tells me what fraction of the 5-hour window is gone, what fraction of the rolling 7-day quota is gone, how many minutes until each resets, and the status code Anthropic itself is reporting. The body of the response, the actual `"Hi"` Haiku would have generated, is read and discarded.

<blockquote class="pull-quote">

AI is on sale today. The meter is the hedge for tomorrow.

</blockquote>

There is a thematic point hiding in this trick. When you are already paying for a subscription, the best inference is the inference you do not run. The infrastructure around the model knows things the model itself does not have to tell you. Treat the response envelope as a first-class data source, not a transport detail.

## Tailscale fixed the network, then broke the TLS

<figure class="section-figure" aria-hidden="true">
  <svg viewBox="0 0 80 80" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" focusable="false">
    <rect x="8" y="34" width="16" height="20" rx="1.5" />
    <path d="M11 34 V28 a5 5 0 0 1 10 0 V34" />
    <line x1="24" y1="44" x2="56" y2="44" />
    <rect x="56" y="34" width="16" height="20" rx="1.5" />
    <path d="M59 34 V28 a5 5 0 0 1 10 0 V40" stroke-dasharray="3 3" />
    <line x1="63" y1="48" x2="67" y2="42" />
  </svg>
</figure>

Tailscale should have been the easy part. The OCI VM is on the tailnet, my phone is on the tailnet, and `tailscale serve` will hand you an HTTPS URL with a real certificate. I wired the Android app at the HTTPS endpoint, ran it, and got an immediate `SSLHandshakeException`. Newer Android versions are stricter about cert pinning and chain validation than I gave them credit for, and the Tailscale-issued cert path was not making them happy.

The trap is that the obvious fix (disable certificate validation in the Android client) is real malpractice in any other context. The non-obvious fix is to notice that the encryption you actually need is already there, one layer down. WireGuard is what makes Tailscale Tailscale. Every byte between the phone and the VM is already inside a WireGuard tunnel, AEAD-encrypted at the transport layer. The TLS on top of that is a belt over a belt. If you drop the TLS, you have not removed encryption, you have removed one of two.

| Path | Works | Encryption in transit |
|------|-------|-----------------------|
| `https://...ts.net/quota.json` | No (Android cert chain) | TLS over WireGuard |
| `http://...ts.net/quota.json`  | Yes                    | WireGuard only        |
| `http://203.0.113.x/quota.json` | N/A (no public IP)    | (would be cleartext)  |

The fix in the Android app is a scoped `network_security_config.xml` that permits cleartext traffic only to subdomains of the tailnet, never to the public internet:

```xml
<domain-config cleartextTrafficPermitted="true">
    <domain includeSubdomains="true">tail7526df.ts.net</domain>
</domain-config>
<base-config cleartextTrafficPermitted="false">
    <trust-anchors><certificates src="system" /></trust-anchors>
</base-config>
```

The generalized lesson is about where encryption lives. Encryption is a property of the channel, not the URL scheme. Defaulting to HTTPS everywhere is a useful habit that can hide where the real encryption sits, and when an HTTPS handshake fails on a path that is already inside a VPN, the right reflex is to ask which guarantee actually got removed by dropping it.

## The watch reboots, the meter doesn't

<figure class="section-figure" aria-hidden="true">
  <svg viewBox="0 0 80 80" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" focusable="false">
    <rect x="22" y="20" width="36" height="40" rx="6" />
    <rect x="32" y="6" width="16" height="10" rx="2" />
    <rect x="32" y="64" width="16" height="10" rx="2" />
    <circle cx="40" cy="40" r="10" />
    <line x1="40" y1="40" x2="40" y2="33" />
    <line x1="40" y1="40" x2="46" y2="44" />
    <path d="M14 40 a26 26 0 1 0 8 -18" />
    <polyline points="14 24 22 22 22 30" />
  </svg>
</figure>

The first night I left the watch charging, it disconnected, came back up an hour later, and stopped getting updates. The Android service still ran. The BLE stack still believed it had a connection. The watch, on the other side, had a fresh boot and had never heard of this phone. The classic asymmetric-state failure mode of any wireless protocol, and the reason consumer BLE is so much harder than it looks in the demo.

The Android service got two changes. First, a `wakeOnDisconnect` flag that breaks the service's long sleep loop the instant any unexpected disconnect arrives, so a watch reboot mid-overnight reconnects in roughly thirty seconds instead of waiting for the two-hour poll interval to elapse. Second, every connection attempt does a teardown first, because Nordic's `BleManager` holds internal state about the last device and a half-broken prior session can swallow the next connect:

```kotlin
private suspend fun connectAndWait(device: BluetoothDevice) {
    // Tear down any zombie connection state before the new attempt.
    runCatching { ble.disconnect().enqueue() }
    delay(200)

    ble.connect(device)
        .useAutoConnect(false)
        .retry(5, 800)
        .timeout(12_000)
        .enqueue()
}
```

Five quick connect attempts at 800 ms apart usually succeed, because the watch is right there on my wrist. When five strikes in a row fail (`consecutiveConnectFails >= RECONNECT_FAILS_BEFORE_RESCAN`), the service drops the cached MAC and falls back to a fresh scan. The cached MAC is usually right; when it is wrong, it is wrong because the watch BLE bond reset or the peripheral re-paired somewhere else, and the only honest move is to forget and re-discover.

There is a thematic sidebar to this section worth saying out loud. The firmware on the watch is not mine. A community port to the exact Waveshare board I had landed as a pull request the same day the device arrived in the mail. I flashed it from the branch knowing perfectly well that an untested commit on a forty-dollar device might brick it. In the AI-speed agentic-engineering era, you do not get to wait. If I had bricked the watch I would have ordered another and tried again the next day. That is the deal you take when the rest of the stack ships faster than the firmware can stabilize.

The generalized lesson is about reliability on stacks you don't own. In any consumer-grade BLE setup, assume the cheapest gain is treating every peer as if it has just rebooted. Tear down before connecting. Retry tight. Distrust your cached state past a small strike count. Half of what looks like "BLE is broken" is one side having more state than the other.

## What a forty-dollar meter buys

The five-hour window is now a number on my wrist. It moves a few percent when I run an agent, a lot when I run several, and zero when I am doing something else. The thing that has changed is not how I use Claude. It is how often I notice. A dashboard is a place I go. A watch is a place I already am.

For a subscription you are already paying for, the most useful unit of value isn't more inference. It is more visibility. The wrist meter cost forty dollars and one Haiku token every five minutes. The watch firmware came from a stranger. The middleware that holds it all together is the work, and the engine at the far end is the cheapest part of the whole story.
