const { app, BrowserWindow, shell, session } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const net = require("net");

let mainWindow = null;
let backendProcess = null;

const PROJECT_ROOT = "D:\\jarvis-local";
const BACKEND_DIR = path.join(PROJECT_ROOT, "backend");
const BACKEND_PYTHON = path.join(BACKEND_DIR, "venv", "Scripts", "python.exe");

function isPortOpen(port) {
  return new Promise((resolve) => {
    const socket = new net.Socket();

    socket.setTimeout(500);

    socket.on("connect", () => {
      socket.destroy();
      resolve(true);
    });

    socket.on("timeout", () => {
      socket.destroy();
      resolve(false);
    });

    socket.on("error", () => {
      resolve(false);
    });

    socket.connect(port, "127.0.0.1");
  });
}

async function waitForPort(port, timeoutMs = 20000) {
  const start = Date.now();

  while (Date.now() - start < timeoutMs) {
    const open = await isPortOpen(port);

    if (open) {
      return true;
    }

    await new Promise((resolve) => setTimeout(resolve, 400));
  }

  return false;
}

async function startBackend() {
  const alreadyRunning = await isPortOpen(8000);

  if (alreadyRunning) {
    console.log("Backend already running.");
    return;
  }

  backendProcess = spawn(
    BACKEND_PYTHON,
    ["-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
    {
      cwd: BACKEND_DIR,
      shell: false,
      windowsHide: true,
      env: {
        ...process.env,
        OPENBLAS_NUM_THREADS: "1",
        OMP_NUM_THREADS: "1",
        PYTHONUNBUFFERED: "1",
        OLLAMA_MODELS: "D:\\ollama\\models"
      }
    }
  );

  backendProcess.stdout.on("data", (data) => {
    console.log(`backend: ${data}`);
  });

  backendProcess.stderr.on("data", (data) => {
    console.error(`backend error: ${data}`);
  });

  backendProcess.on("error", (error) => {
    console.error("Backend spawn error:", error);
  });

  backendProcess.on("close", (code) => {
    console.log(`backend closed with code ${code}`);
  });

  const ready = await waitForPort(8000, 20000);

  if (ready) {
    console.log("Backend ready.");
  } else {
    console.log("Backend did not become ready fast enough.");
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 1100,
    minHeight: 720,
    backgroundColor: "#000000",
    title: "Assistant",
    autoHideMenuBar: true,
    show: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: true
    }
  });

  mainWindow.maximize();

  const devUrl = "http://localhost:5173";
  const prodPath = path.join(__dirname, "..", "dist", "index.html");

  if (!app.isPackaged) {
    mainWindow.loadURL(devUrl);
  } else {
    mainWindow.loadFile(prodPath);
  }

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
    mainWindow.focus();
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
}

app.whenReady().then(() => {
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    callback(true);
  });

  createWindow();

  setTimeout(() => {
    startBackend().catch((error) => {
      console.error("Backend startup failed:", error);
    });
  }, 800);
});

app.on("window-all-closed", () => {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }

  if (process.platform !== "darwin") {
    app.quit();
  }
});