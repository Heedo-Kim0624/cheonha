#!/usr/bin/env node
const fs = require("fs");
const http = require("http");
const https = require("https");
const path = require("path");
const { URL } = require("url");

const HOST = process.env.HOST || "127.0.0.1";
const PORT = Number(process.env.PORT || 8787);
const API_ORIGIN = process.env.CHEONHA_API_ORIGIN || "http://43.201.160.163";
const HTML_PATH = path.join(__dirname, "tracking_csv_downloader.html");

const apiOriginUrl = new URL(API_ORIGIN);
const apiClient = apiOriginUrl.protocol === "https:" ? https : http;

function withCors(headers = {}) {
  return {
    ...headers,
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
    "Access-Control-Allow-Headers": "Authorization,Content-Type,Accept",
  };
}

function send(res, statusCode, headers, body) {
  res.writeHead(statusCode, withCors(headers));
  res.end(body);
}

function serveHtml(res) {
  fs.readFile(HTML_PATH, (error, content) => {
    if (error) {
      send(
        res,
        500,
        { "Content-Type": "text/plain; charset=utf-8" },
        `HTML 파일을 읽을 수 없습니다: ${HTML_PATH}\n${error.message}`
      );
      return;
    }

    send(res, 200, { "Content-Type": "text/html; charset=utf-8" }, content);
  });
}

function proxyApi(req, res) {
  const upstreamUrl = new URL(req.url, apiOriginUrl);
  const upstreamHeaders = { ...req.headers, host: upstreamUrl.host };

  delete upstreamHeaders.connection;
  delete upstreamHeaders["proxy-connection"];

  const upstreamReq = apiClient.request(
    upstreamUrl,
    {
      method: req.method,
      headers: upstreamHeaders,
    },
    (upstreamRes) => {
      res.writeHead(
        upstreamRes.statusCode || 502,
        withCors(upstreamRes.headers)
      );
      upstreamRes.pipe(res);
    }
  );

  upstreamReq.on("error", (error) => {
    send(
      res,
      502,
      { "Content-Type": "application/json; charset=utf-8" },
      JSON.stringify({
        detail: "운영 API에 연결할 수 없습니다.",
        target: upstreamUrl.origin,
        error: error.message,
      })
    );
  });

  req.pipe(upstreamReq);
}

const server = http.createServer((req, res) => {
  const requestUrl = new URL(req.url, `http://${req.headers.host || HOST}`);

  if (req.method === "OPTIONS") {
    send(res, 204, {}, "");
    return;
  }

  if (requestUrl.pathname === "/" || requestUrl.pathname === "/tracking_csv_downloader.html") {
    serveHtml(res);
    return;
  }

  if (requestUrl.pathname.startsWith("/api/")) {
    proxyApi(req, res);
    return;
  }

  send(res, 404, { "Content-Type": "text/plain; charset=utf-8" }, "Not found");
});

server.listen(PORT, HOST, () => {
  console.log(`근무기록 CSV 다운로드 페이지: http://${HOST}:${PORT}`);
  console.log(`운영 API 프록시 대상: ${apiOriginUrl.origin}`);
  console.log("종료: Ctrl+C");
});
