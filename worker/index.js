export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const expectedToken = env.SUB_TOKEN;
    if (!expectedToken) {
      return new Response("Subscription endpoint is not configured.", { status: 503 });
    }

    // URL shape: https://your-worker.workers.dev/<SUB_TOKEN>/subscription.txt
    const parts = url.pathname.split("/").filter(Boolean);
    if (parts.length !== 2 || parts[0] !== expectedToken || parts[1] !== "subscription.txt") {
      return new Response("Not found", { status: 404 });
    }

    const content = await env.SUBSCRIPTIONS.get("latest");
    if (!content) {
      return new Response("Subscription has not been published yet.", { status: 404 });
    }

    return new Response(content, {
      headers: {
        "content-type": "text/plain; charset=utf-8",
        "cache-control": "no-store",
        "x-content-type-options": "nosniff"
      }
    });
  }
};
