export async function onRequest(context) {
  const { request, env, next } = context;

  if (!env.SITE_USER || !env.SITE_PASSWORD) {
    return next();
  }

  const auth = request.headers.get("Authorization");
  const expected = "Basic " + btoa(`${env.SITE_USER}:${env.SITE_PASSWORD}`);
  if (auth === expected) {
    return next();
  }

  return new Response("認証が必要です。", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="tokyo-exhibitions", charset="UTF-8"' },
  });
}
