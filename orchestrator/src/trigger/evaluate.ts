import { schedules, task, wait, logger } from "@trigger.dev/sdk";

const SERVER = process.env.SERVER_URL!;
const KEY = process.env.THERAPIST_KEY!;
const headers = { "x-therapist-key": KEY, "content-type": "application/json" };

type Triggered = { patient_id: number; trigger: string };

export const evaluateSignals = schedules.task({
  id: "evaluate-signals",
  cron: "0 */3 * * *",
  run: async () => {
    const res = await fetch(`${SERVER}/decide`, { method: "POST", headers });
    if (!res.ok) throw new Error(`decide ${res.status}`);
    const { triggered } = (await res.json()) as { triggered: Triggered[] };
    logger.info("triggered", { count: triggered.length });
    for (const t of triggered) await checkin.trigger(t);
    return { count: triggered.length };
  },
});

export const checkin = task({
  id: "checkin",
  retry: { maxAttempts: 3, minTimeoutInMs: 5_000 },
  run: async (payload: Triggered) => {
    const token = await wait.createToken({ timeout: "6h" });
    const res = await fetch(`${SERVER}/checkin`, {
      method: "POST", headers, body: JSON.stringify({ ...payload, waitpoint_token: token.id }),
    });
    if (!res.ok) throw new Error(`checkin ${res.status}`);
    const result = await wait.forToken<{ status: string; mood_1_5?: number }>(token);
    if (!result.ok) { logger.warn("no reply in 6h", payload); return { status: "no_reply" }; }
    return result.output;
  },
});
