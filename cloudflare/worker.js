const BACKEND_URL = "https://jstock-c2ctfydbgbcrhmf2.eastasia-01.azurewebsites.net";

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const targetUrl = BACKEND_URL + url.pathname + url.search;

    const backendRequest = new Request(targetUrl, {
      method: request.method,
      headers: request.headers,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
      redirect: "follow",
    });

    const response = await fetch(backendRequest);

    // Pass through headers, fix CORS if needed
    const newHeaders = new Headers(response.headers);
    newHeaders.set("Access-Control-Allow-Origin", "*");

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: newHeaders,
    });
  },
};
