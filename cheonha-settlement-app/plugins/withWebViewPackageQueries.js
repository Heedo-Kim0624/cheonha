const { withAndroidManifest } = require("expo/config-plugins");

const WEBVIEW_PACKAGES = [
  "com.google.android.webview",
  "com.android.webview",
  "com.android.chrome",
];

module.exports = function withWebViewPackageQueries(config) {
  return withAndroidManifest(config, (config) => {
    const manifest = config.modResults.manifest;
    manifest.queries = manifest.queries || [{}];
    const queries = manifest.queries[0] || {};
    manifest.queries[0] = queries;
    queries.package = queries.package || [];

    for (const packageName of WEBVIEW_PACKAGES) {
      const exists = queries.package.some(
        (entry) => entry?.$?.["android:name"] === packageName
      );
      if (!exists) {
        queries.package.push({ $: { "android:name": packageName } });
      }
    }

    return config;
  });
};
