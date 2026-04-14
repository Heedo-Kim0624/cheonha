const { withMainApplication } = require("expo/config-plugins");

module.exports = function withAndroidNetworkTuning(config) {
  return withMainApplication(config, (config) => {
    if (config.modResults.language !== "kt") {
      return config;
    }

    let contents = config.modResults.contents;

    const imports = [
      "import com.facebook.react.modules.network.OkHttpClientProvider",
      "import java.net.Inet4Address",
      "import java.net.InetAddress",
      "import java.util.concurrent.TimeUnit",
      "import okhttp3.Dns",
    ].join("\n");

    if (!contents.includes("OkHttpClientProvider")) {
      contents = contents.replace(
        "import com.facebook.react.defaults.DefaultReactNativeHost\n",
        `import com.facebook.react.defaults.DefaultReactNativeHost\n${imports}\n`
      );
    }

    const helper = `\n  private fun configureAndroidNetworking() {\n    System.setProperty(\"java.net.preferIPv4Stack\", \"true\")\n    System.setProperty(\"java.net.preferIPv6Addresses\", \"false\")\n    OkHttpClientProvider.setOkHttpClientFactory {\n      OkHttpClientProvider.createClientBuilder(applicationContext)\n        .dns(object : Dns {\n          override fun lookup(hostname: String): List<InetAddress> {\n            val addresses = Dns.SYSTEM.lookup(hostname)\n            val ipv4 = addresses.filterIsInstance<Inet4Address>()\n            return if (ipv4.isNotEmpty()) ipv4 else addresses\n          }\n        })\n        .connectTimeout(15, TimeUnit.SECONDS)\n        .readTimeout(30, TimeUnit.SECONDS)\n        .writeTimeout(30, TimeUnit.SECONDS)\n        .build()\n    }\n  }\n`;

    if (!contents.includes("configureAndroidNetworking()")) {
      contents = contents.replace(
        "\n  override fun onCreate() {",
        `${helper}\n  override fun onCreate() {`
      );
      contents = contents.replace(
        "  override fun onCreate() {\n    super.onCreate()",
        "  override fun onCreate() {\n    super.onCreate()\n    configureAndroidNetworking()"
      );
    }

    config.modResults.contents = contents;
    return config;
  });
};
