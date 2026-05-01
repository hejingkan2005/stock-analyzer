export default {
  async fetch(request, env) {
    // Cloudflare Workers cannot run a long-lived Dash/Flask server process directly.
    // This worker can proxy traffic to a backend where app.py is running.
    const backend = env.BACKEND_URL;

    if (!backend) {
      const message = [
        "Cloudflare worker is configured.",
        "Set BACKEND_URL in Cloudflare to proxy this endpoint to your running Dash backend.",
        "Example:",
        "wrangler secret put BACKEND_URL",
      ].join("\n");

      return new Response(message, {
        status: 200,
        headers: { "content-type": "text/plain; charset=UTF-8" },
      });
    }

    const incoming = new URL(request.url);
    const target = new URL(backend);
    target.pathname = incoming.pathname;
    target.search = incoming.search;

    const proxiedRequest = new Request(target.toString(), request);
    return fetch(proxiedRequest);
  },
};
