const { withDangerousMod } = require("expo/config-plugins");
const fs = require("fs");
const path = require("path");

module.exports = function withNetworkSecurityConfig(config) {
  return withDangerousMod(config, [
    "android",
    async (config) => {
      const xmlDir = path.join(
        config.modRequest.platformProjectRoot,
        "app",
        "src",
        "main",
        "res",
        "xml"
      );
      fs.mkdirSync(xmlDir, { recursive: true });

      const xmlContent = `<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="true">
        <trust-anchors>
            <certificates src="system" />
        </trust-anchors>
    </base-config>
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">3.35.218.152</domain>
        <domain includeSubdomains="true">ec2-3-35-218-152.ap-northeast-2.compute.amazonaws.com</domain>
        <domain includeSubdomains="true">3.34.125.138</domain>
        <domain includeSubdomains="true">ec2-3-34-125-138.ap-northeast-2.compute.amazonaws.com</domain>
    </domain-config>
</network-security-config>`;

      fs.writeFileSync(path.join(xmlDir, "network_security_config.xml"), xmlContent);
      return config;
    },
  ]);
};
