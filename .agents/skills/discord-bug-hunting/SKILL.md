---
name: discord-bug-hunting
description: >-
  Use this skill when the user asks for help writing code to find bugs in Discord, interacting with the Discord API, automating Discord client behavior, or analyzing Discord's telemetry/science endpoints.
---

# Discord Bug Hunting & Automation

This skill provides context and patterns for interacting with Discord's internal APIs (like `/api/v9/science`) based on previous reverse-engineering and automation work. Use these patterns when helping the user write tools to find bugs or automate client behavior.

## Authentication & Headers

Interacting with Discord's private APIs requires mimicking an official client perfectly.

1.  **Account Token**: Required in the `authorization` header. On Windows, store this securely (e.g., using DPAPI) to tie it to the user's machine.
2.  **Cloudflare Cookie**: The `cf_clearance` cookie is often required to bypass Cloudflare protection. Send it in the `cookie` header.
3.  **Super Properties**: The `x-super-properties` header contains a base64-encoded JSON object detailing the client's OS, browser, build numbers (e.g., `client_build_number`, `native_build_number`), and session UUIDs (`client_launch_id`, `client_heartbeat_session_id`). This needs to be up-to-date.
4.  **Analytics Token**: For telemetry/science endpoints, you often need an `analytics_token`. Fetch this from `GET /api/v9/users/@me?with_analytics_token=true` using the main token and super properties.

## Executable Fingerprinting

Discord verifies the authenticity of game launches and some client actions using an `executable_fingerprint`.

*   **What it is**: A base64 string containing PE metadata of the executable (file size, timestamps, section hashes, certificate info), bound to the user's ID and the machine GUID (from Windows Registry).
*   **Generation**: This is specific to Windows and involves hashing the executable's headers and sections, and XOR-obfuscating it with a key derived from the user ID. Without a valid fingerprint, telemetry events may be ignored or flagged.

## Rate Limiting and Network Handling

When sending bulk requests or automating endpoints:

*   **Cloudflare Drops**: You may encounter `SSL: UNEXPECTED_EOF_WHILE_READING` or `WinError 10054`. This is normal. Implement a retry mechanism (e.g., up to 3 retries) with exponential backoff.
*   **Auth Rejection**: If you receive HTTP `401` or `403`, the `cf_clearance` cookie or the token is likely expired. The script must pause and prompt the user to refresh the cookie.
*   **Batching**: Group events into batches (e.g., 50 events per request) and add delays (e.g., 0.3s - 1s) between requests to avoid triggering spam filters.

## Example Workflow (Science Endpoint)

When simulating a game session to `/api/v9/science`:

1.  Send a `running_game_heartbeat` event with `initial_heartbeat: true`.
2.  Send a `launch_game` event.
3.  Send a closing `running_game_heartbeat` event with `duration_tracked_ms` set to the desired playtime.
4.  Ensure all events in a session share the same `client_heartbeat_session_id` and `game_session_id`.
