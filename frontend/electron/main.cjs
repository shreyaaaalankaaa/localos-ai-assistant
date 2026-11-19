const { app, BrowserWindow, shell, session, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const { spawn } = require('child_process');
const net = require('net');

let mainWindow = null;
let backendProcess = null;

const PROJECT_ROOT = path.resolve(__dirname, '..', '..');
const BACKEND_DIR = app.isPackaged
  ? path.join(process.resourcesPath, 'backend')
  : path.join(PROJECT_ROOT, 'backend');

const DEV_URL = 'http://127.0.0.1:5173';
let sessionToken = '';

function dataDir() {
  return path.join(app.getPath('userData'), 'data');
}

// One token per install, shared with the backend. If a backend is already running
// (started by hand from backend/), reuse the token file it created instead.
function readOrCreateToken(file) {
  try {
    const existing = fs.readFileSync(file, 'utf8').trim();
    if (existing.length >= 32) return existing;
  } catch { /* create below */ }
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const token = crypto.randomBytes(32).toString('hex');
  fs.writeFileSync(file, token, { mode: 0o600 });
  return token;
}

function isOwnFrontend(url) {
  return url.startsWith('file://') || url.startsWith(DEV_URL);
}

function pythonExecutable() {
  const candidates = process.platform === 'win32'
    ? [path.join(BACKEND_DIR, 'venv', 'Scripts', 'python.exe'), path.join(PROJECT_ROOT, '.venv', 'Scripts', 'python.exe')]
    : [path.join(BACKEND_DIR, 'venv', 'bin', 'python'), path.join(PROJECT_ROOT, '.venv', 'bin', 'python')];
  const found = candidates.find(p => fs.existsSync(p));
  if (found) return { executable: found, extra: [] };
  return process.platform === 'win32'
    ? { executable: 'py', extra: ['-3'] }
    : { executable: 'python3', extra: [] };
}
function isPortOpen(port) {
  return new Promise(resolve => {
    const socket = new net.Socket();
    const finish = (open) => { socket.destroy(); resolve(open); };
    socket.setTimeout(500);
    socket.once('connect', () => finish(true));
    socket.once('timeout', () => finish(false));
    socket.once('error', () => finish(false));
    socket.connect(port, '127.0.0.1');
  });
}
async function startBackend() {
  if (process.env.JARVIS_TOKEN) {
    sessionToken = process.env.JARVIS_TOKEN;
  } else if (await isPortOpen(8000)) {
    // A backend is already running: use the newest token file it could have written.
    const candidates = [path.join(dataDir(), '.jarvis_token'), path.join(BACKEND_DIR, 'data', '.jarvis_token')]
      .filter(f => fs.existsSync(f))
      .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
    sessionToken = candidates.length ? readOrCreateToken(candidates[0]) : '';
    if (!sessionToken) console.error('Backend already running but no token file was found. Restart the backend.');
    return;
  } else {
    sessionToken = readOrCreateToken(path.join(dataDir(), '.jarvis_token'));
  }
  if (await isPortOpen(8000)) return;
  if (!fs.existsSync(path.join(BACKEND_DIR, 'main.py'))) {
    console.error('Backend files not found:', BACKEND_DIR);
    return;
  }
  const py = pythonExecutable();
  backendProcess = spawn(py.executable, [...py.extra, '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000'], {
    cwd: BACKEND_DIR,
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: {
      ...process.env,
      LOCALOS_DATA_DIR: dataDir(),
      JARVIS_TOKEN: sessionToken,
      PYTHONUNBUFFERED: '1',
      OPENBLAS_NUM_THREADS: '1',
    },
  });
  backendProcess.stdout.on('data', data => console.log(`backend: ${data}`));
  backendProcess.stderr.on('data', data => console.error(`backend: ${data}`));
  backendProcess.on('error', err => console.error('Failed to start backend. Check Python dependencies.', err));
  backendProcess.on('close', code => { console.log('Backend exited:', code); backendProcess = null; });
}
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1600,
    height: 900,
    minWidth: 800,
    minHeight: 580,
    backgroundColor: '#010101',
    title: 'JARVIS // LOCAL OS V2.0',
    autoHideMenuBar: true,
    show: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      preload: path.join(__dirname, 'preload.cjs'),
    },
  });
  mainWindow.maximize();
  if (app.isPackaged) {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
  } else {
    mainWindow.loadURL(DEV_URL);
  }
  mainWindow.once('ready-to-show', () => mainWindow.show());
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//.test(url)) shell.openExternal(url);
    return { action: 'deny' };
  });
}
// Only the JARVIS frontend itself may ask for the token.
ipcMain.on('jarvis:get-token', (event) => {
  event.returnValue = isOwnFrontend(event.senderFrame?.url || '') ? sessionToken : '';
});

app.whenReady().then(async () => {
  // Do not auto-grant camera/location/notifications to arbitrary content.
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    const source = webContents.getURL();
    const localFrontend = isOwnFrontend(source);
    callback(permission === 'media' && localFrontend);
  });
  await startBackend();
  createWindow();
});
app.on('window-all-closed', () => {
  if (backendProcess) backendProcess.kill();
  if (process.platform !== 'darwin') app.quit();
});
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
