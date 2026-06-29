// Generates a random nonce for the webview Content-Security-Policy.
//
// A fresh nonce per HTML render lets the CSP allow exactly our own <script>
// (`script-src 'nonce-...'`) and nothing else — so injected/3rd-party scripts
// can't run inside the webview. Shared by every webview we render.

export function makeNonce(): string {
  const chars =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let text = "";
  for (let i = 0; i < 32; i++) {
    text += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return text;
}
