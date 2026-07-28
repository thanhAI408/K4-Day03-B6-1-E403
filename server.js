const http = require("http");
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const root = __dirname;
const publicDir = path.join(root, "public");
const python = fs.existsSync(path.join(root, ".venv", "Scripts", "python.exe"))
  ? path.join(root, ".venv", "Scripts", "python.exe")
  : "python";

function runAgent(mode, query) {
  return new Promise((resolve, reject) => {
    const child = spawn(python, [path.join(root, "src", "ui_bridge.py")], {
      cwd: root,
      env: { ...process.env, PYTHONIOENCODING: "utf-8" },
    });
    let output = "";
    let error = "";
    child.stdout.on("data", (chunk) => (output += chunk));
    child.stderr.on("data", (chunk) => (error += chunk));
    child.on("error", reject);
    child.on("close", (code) => {
      if (code !== 0) return reject(new Error(error || `Python exited with ${code}`));
      try { resolve(JSON.parse(output)); }
      catch { reject(new Error("Bridge trả về dữ liệu không hợp lệ.")); }
    });
    child.stdin.end(JSON.stringify({ mode, query }));
  });
}

function send(res, status, body, type = "application/json; charset=utf-8") {
  res.writeHead(status, { "Content-Type": type });
  res.end(type.startsWith("application/json") ? JSON.stringify(body) : body);
}

const server = http.createServer(async (req, res) => {
  if (req.method === "POST" && req.url === "/api/run") {
    let raw = "";
    req.on("data", (chunk) => (raw += chunk));
    req.on("end", async () => {
      try {
        const data = JSON.parse(raw || "{}");
        if (!data.query || !["baseline", "react"].includes(data.mode))
          return send(res, 400, { error: "mode và query là bắt buộc." });
        send(res, 200, await runAgent(data.mode, data.query));
      } catch (error) { send(res, 500, { error: error.message }); }
    });
    return;
  }
  const requested = req.url === "/" ? "/index.html" : req.url;
  const file = path.normalize(path.join(publicDir, requested));
  if (!file.startsWith(publicDir)) return send(res, 403, { error: "Forbidden" });
  fs.readFile(file, (error, data) => {
    if (error) return send(res, 404, { error: "Not found" });
    const type = file.endsWith(".html") ? "text/html; charset=utf-8" : file.endsWith(".css") ? "text/css; charset=utf-8" : "text/javascript; charset=utf-8";
    send(res, 200, data, type);
  });
});

const port = Number(process.env.PORT || 3000);
server.listen(port, () => console.log(`Agent Lab UI: http://localhost:${port}`));
