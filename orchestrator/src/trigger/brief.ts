import { schedules } from "@trigger.dev/sdk";

const SERVER = process.env.SERVER_URL!;
const headers = { "x-therapist-key": process.env.THERAPIST_KEY!, "content-type": "application/json" };

export const nightlyBrief = schedules.task({
  id: "nightly-brief",
  cron: { pattern: "0 18 * * *", timezone: "America/New_York" },
  run: async () => {
    const res = await fetch(`${SERVER}/brief`, { method: "POST", headers, body: JSON.stringify({}) });
    if (!res.ok) throw new Error(`brief ${res.status}`);
    return await res.json();
  },
});
