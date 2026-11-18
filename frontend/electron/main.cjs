const { app, BrowserWindow, shell, session } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const net = require('net');

let mainWindow = null;
let backendProcess = null;

const PROJECT_ROOT = path.resolve(__dirname, '..', '..');
const BACKEND_DIR = app.isPackaged
  ? path.join(process.resourcesPath, 'backend')
  : path.join(PROJECT_ROOT, 'backend');

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
      LOCALOS_DATA_DIR: path.join(app.getPath('userData'), 'data'),
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
    webPreferences: { contextIsolation: true, nodeIntegration: false, webSecurity: true },
  });
  mainWindow.maximize();
  if (app.isPackaged) {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
  } else {
    mainWindow.loadURL('http://127.0.0.1:5173');
  }
  mainWindow.once('ready-to-show', () => mainWindow.show());
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//.test(url)) shell.openExternal(url);
    return { action: 'deny' };
  });
}
app.whenReady().then(async () => {
  // Do not auto-grant camera/location/notifications to arbitrary content.
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    const source = webContents.getURL();
    const localFrontend = source.startsWith('file://') || /^http:\/\/127\.0\.0\.1:5173/.test(source);
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
