// Gives the JARVIS frontend its backend session token, and nothing else.
// The token comes from the main process over IPC; pages cannot read it any other way.
const { contextBridge, ipcRenderer } = require('electron');

const token = ipcRenderer.sendSync('jarvis:get-token');

contextBridge.exposeInMainWorld('jarvis', {
  token: typeof token === 'string' ? token : '',
});
