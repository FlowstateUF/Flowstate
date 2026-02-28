export function getAccessToken() {
  return localStorage.getItem("access_token");
}

export async function authFetch(url, options = {}) {
  const token = getAccessToken();

  const res = await fetch(url, {
    ...options,
    headers: {
      ...(options.headers || {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  // If token is rejected, clear it so UI doesn’t pretend you’re logged in
  if (res.status === 401) {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
  }

  return res;
}
