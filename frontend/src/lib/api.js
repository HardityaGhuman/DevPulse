import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * Request interceptor — injects Clerk session token.
 * The token getter is set once via setTokenGetter() from the app root.
 */
let _getToken = null;

export function setTokenGetter(fn) {
  _getToken = fn;
}

api.interceptors.request.use(async (config) => {
  if (_getToken) {
    try {
      const token = await _getToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (e) {
      // Silently fail — let backend return 401
    }
  }
  return config;
});

export default api;
