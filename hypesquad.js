/**
 * Discord HypeSquad House Claimer & Switcher
 * SahrulRD-Smatel, 2026. MIT Licensed.
 * 
 * Instructions:
 * 1. Open Discord in your Desktop App or Chromium Browser (discord.com/app).
 * 2. Press F12 (or Ctrl + Shift + I) to open Developer Tools.
 * 3. Go to the "Console" tab. (Type "allow pasting" and press Enter if prompted).
 * 4. Set HOUSE_ID to:
 *      1 = HypeSquad Bravery    (Purple 💜)
 *      2 = HypeSquad Brilliance (Red / Orange ❤️)
 *      3 = HypeSquad Balance    (Teal / Green 💚)
 * 5. Paste this script and press Enter!
 */

(async (houseId = 1) => {
  const wp = window.webpackChunkdiscord_app.push([[Symbol()], {}, (r) => r]);
  window.webpackChunkdiscord_app.pop();

  const modules = wp.m;
  const cache = wp.c;

  const findModule = (filter) => {
    for (const [id, mod] of Object.entries(modules)) {
      if (mod.toString().includes(filter)) {
        return cache[id]?.exports;
      }
    }
  };

  const findKey = (exports, key) => {
    if (!exports) return null;
    for (const k in exports) {
      if (exports[k] && exports[k][key]) return exports[k];
    }
    return null;
  };

  const api = findKey(findModule('.set("X-Audit-Log-Reason",'), "patch");
  if (!api || !api.post) {
    console.error("❌ Failed to locate Discord's internal REST API client.");
    return;
  }

  const houseNames = {
    1: "Bravery (Purple 💜)",
    2: "Brilliance (Red ❤️)",
    3: "Balance (Teal 💚)",
  };

  console.log(`⏳ Requesting HypeSquad house: ${houseNames[houseId] || houseId}...`);

  try {
    await api.post({
      url: "/hypesquad/online",
      body: { house_id: houseId },
    });
    console.log(`✅ SUCCESS! Badge claimed for HypeSquad ${houseNames[houseId] || houseId}!`);
    console.log(`👉 Press Ctrl + R in Discord to view your new badge!`);
  } catch (err) {
    console.error("❌ Failed to update HypeSquad house:", err);
  }
})(1); // <-- Change to 1 (Bravery), 2 (Brilliance), or 3 (Balance)
