// Profile views counter for the GitHub profile README.
//
//   GET /views.svg?theme=light|dark  counts one view and returns the badge
//   GET /peek.svg?theme=light|dark   returns the badge without counting (for previews)
//
// The count lives in a single Durable Object, so concurrent views can't overwrite each
// other. Responses are marked uncacheable so GitHub's image proxy fetches a fresh count.
import { DurableObject } from "cloudflare:workers";
import { renderBadge } from "./badge.js";

export class ViewCounter extends DurableObject {
  async hit(count) {
    let n = (await this.ctx.storage.get("views")) ?? 0;
    if (count) {
      n += 1;
      await this.ctx.storage.put("views", n);
    }
    return n;
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method not allowed", { status: 405 });
    }
    const counts = url.pathname === "/views.svg";
    if (!counts && url.pathname !== "/peek.svg") {
      return new Response("Profile views counter. Use /views.svg?theme=light|dark", {
        status: url.pathname === "/" ? 200 : 404,
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    }
    const stub = env.COUNTER.get(env.COUNTER.idFromName("profile"));
    const n = await stub.hit(counts && request.method === "GET");
    const theme = url.searchParams.get("theme") === "dark" ? "dark" : "light";
    return new Response(request.method === "HEAD" ? null : renderBadge(n, theme), {
      headers: {
        "content-type": "image/svg+xml; charset=utf-8",
        "cache-control": "max-age=0, no-cache, no-store, must-revalidate",
        expires: "0",
        etag: `"${n}-${theme}"`,
      },
    });
  },
};
