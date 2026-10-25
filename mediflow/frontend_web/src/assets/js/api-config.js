(function (root) {
  "use strict";

  const hostname = root.location?.hostname || "";

  const esDesarrolloLocal =
    hostname === "localhost" ||
    hostname === "127.0.0.1";

  root.MEDIFLOW_API_BASE_URL = esDesarrolloLocal
    ? "http://127.0.0.1:8001"
    : "https://desktop-edilanti.tailf48a22.ts.net:8443";

})(typeof window !== "undefined" ? window : globalThis);