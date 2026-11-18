import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import {
  Activity, AppWindow, ArrowLeft, ArrowUpRight, Bell, BrainCircuit,
  ChevronRight, CircleHelp,
  Code2, Copy, Cpu, ExternalLink, FileCode2, FileText, Folder, FolderOpen,
  HardDrive, Home, Layers3, MemoryStick, MessageSquare, Mic, MicOff,
  Monitor, Plus, RotateCcw, Save, Search, Send, Settings2, ShieldCheck,
  Trash2, Volume2, VolumeX, Wifi, X,
} from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import GlobeScene from './GlobeScene';
import { api, json, type Message, type Mode, type Section, type LiveStatus,
  type Metrics, type Models, type FileEntry, type FolderResponse, type Profile,
  type ToolResult } from './api';
import './App.css';

type AppItem = { name: string; url?: string };
type Note = { file: string; content: string };
const NAV = [
  { id: 'home', title: 'HOME', icon: Home },
  { id: 'chat', title: 'CHAT', icon: MessageSquare },
  { id: 'reasoning', title: 'REASONING', icon: BrainCircuit },
  { id: 'coding', title: 'CODING', icon: Code2 },
  { id: 'apps', title: 'APPS', icon: Layers3 },
  { id: 'files', title: 'FILES', icon: FileText },
  { id: 'settings', title: 'SETTINGS', icon: Settings2 },
] as const;

const MODES: Record<'home' | 'chat' | 'reasoning' | 'coding', Mode> = {
  home: 'fast', chat: 'normal', reasoning: 'reasoning', coding: 'coding',
};
const LABELS: Record<Mode, string> = {
  fast: 'FAST RESPONSE', normal: 'CONVERSATION', reasoning: 'DEEP REASONING', coding: 'CODE ASSISTANT',
};
function formatClock(date: Date) {
  return new Intl.DateTimeFormat('en-US', { hour: '2-digit', minute: '2-digit', hour12: true }).format(date);
}
function formatDate(date: Date) {
  return new Intl.DateTimeFormat('en-US', { weekday: 'short', month: 'short', day: '2-digit', year: 'numeric' })
    .format(date).toUpperCase();
}
function formatBytes(bytes = 0) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}
function shortPath(path: string) {
  return path.replace(/\\/g, '/').split('/').filter(Boolean).slice(-3).join(' / ') || path;
}

function CircularMetric({ label, value, detail }: { label: string; value: number | null; detail?: string }) {
  const shown = value === null ? 'N/A' : `${Math.round(value)}%`;
  return (
    <div className="metric-row" title={detail}>
      <span className="metric-gauge" style={{ '--progress': `${Math.max(0, Math.min(value ?? 0, 100))}%` } as CSSProperties} />
      <div className="metric-main"><div className="metric-line"><span>{label}</span><strong>{shown}</strong></div>
        <div className="metric-track"><span style={{ width: `${value ?? 0}%` }} /></div>
      </div>
    </div>
  );
}

function StatusItem({ label, on }: { label: string; on: boolean }) {
  return <div className="status-item"><span className={`status-led ${on ? 'lit' : ''}`} /><span>{label}</span></div>;
}

function HUD() {
  return <div className="hud-orbits" aria-hidden="true">
    <div className="hud-ring ring-outer" />
    <div className="hud-ring ring-middle" />
    <div className="hud-ring ring-inner" />
    <div className="hud-arc arc-one" /><div className="hud-arc arc-two" />
    <div className="hud-cross cross-top" /><div className="hud-cross cross-bottom" />
    <div className="hud-cross cross-left" /><div className="hud-cross cross-right" />
    <div className="hud-notch notch-a" /><div className="hud-notch notch-b" />
    <div className="hud-notch notch-c" /><div className="hud-notch notch-d" />
  </div>;
}

export default function App() {
  const [section, setSection] = useState<Section>('home');
  const [messages, setMessages] = useState<Message[]>([]);
  const [entry, setEntry] = useState('');
  const [sending, setSending] = useState(false);
  const [listening, setListening] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(() => localStorage.getItem('jarvis-voice') === 'true');
  const [status, setStatus] = useState<LiveStatus | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [models, setModels] = useState<Models | null>(null);
  const [selectedModel, setSelectedModel] = useState(() => localStorage.getItem('jarvis-model') || '');
  const [now, setNow] = useState(new Date());
  const [notice, setNotice] = useState('');
  const [expandedFile, setExpandedFile] = useState<{ name: string; content: string } | null>(null);
  const [fileList, setFileList] = useState<FolderResponse | null>(null);
  const [folder, setFolder] = useState('project');
  const [locations, setLocations] = useState<{ key: string; path: string; exists: boolean }[]>([]);
  const [folderBusy, setFolderBusy] = useState(false);
  const [fileQuery, setFileQuery] = useState('');
  const [apps, setApps] = useState<string[]>([]);
  const [websites, setWebsites] = useState<AppItem[]>([]);
  const [appTab, setAppTab] = useState<'launch' | 'notes' | 'memory'>('launch');
  const [notes, setNotes] = useState<Note[]>([]);
  const [newNote, setNewNote] = useState({ title: '', content: '' });
  const [memory, setMemory] = useState('');
  const [newMemory, setNewMemory] = useState('');
  const [profile, setProfile] = useState<Profile>({ preferred_name: '', tone: '', style: '' });
  const [profileSaving, setProfileSaving] = useState(false);
  const [historyReady, setHistoryReady] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const micRef = useRef<any>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const sendRef = useRef<(value?: string) => Promise<void>>(async () => {});
  const notificationTimeout = useRef<number | undefined>(undefined);

  const mode: Mode = MODES[section as keyof typeof MODES] || 'normal';
  const notify = useCallback((message: string) => {
    setNotice(message);
    window.clearTimeout(notificationTimeout.current);
    notificationTimeout.current = window.setTimeout(() => setNotice(''), 4500);
  }, []);

  const refreshStatus = useCallback(async () => {
    try { setStatus(await api<LiveStatus>('/api/status')); }
    catch { setStatus(null); }
  }, []);
  const refreshMetrics = useCallback(async () => {
    try { setMetrics(await api<Metrics>('/api/system')); }
    catch { setMetrics(null); }
  }, []);
  const refreshModels = useCallback(async () => {
    try { setModels(await api<Models>('/api/models')); }
    catch { setModels(null); }
  }, []);
  const refreshNotes = useCallback(async () => {
    try { const data = await api<{ notes: Note[] }>('/api/notes'); setNotes(data.notes ?? []); }
    catch { setNotes([]); }
  }, []);
  const refreshMemory = useCallback(async () => {
    try { const data = await api<{ memory: string }>('/api/memory'); setMemory(data.memory || ''); }
    catch { setMemory(''); }
  }, []);

  useEffect(() => {
    const tick = window.setInterval(() => setNow(new Date()), 1000);
    refreshStatus(); refreshMetrics(); refreshModels();
    api<{ messages: Message[] }>('/api/history')
      .then(data => setMessages(data.messages || []))
      .catch(() => {})
      .finally(() => setHistoryReady(true));
    const s = window.setInterval(refreshStatus, 12000);
    const m = window.setInterval(refreshMetrics, 3500);
    const n = window.setInterval(refreshModels, 30000);
    return () => { clearInterval(tick); clearInterval(s); clearInterval(m); clearInterval(n);
      clearTimeout(notificationTimeout.current); };
  }, [refreshStatus, refreshMetrics, refreshModels]);

  useEffect(() => {
    localStorage.setItem('jarvis-voice', String(voiceEnabled));
  }, [voiceEnabled]);
  useEffect(() => { localStorage.setItem('jarvis-model', selectedModel); }, [selectedModel]);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [messages, sending]);

  const navigate = useCallback((next: Section) => {
    setSection(next); setMobileNavOpen(false);
    if (next === 'apps') {
      api<{ apps: string[]; websites: AppItem[] }>('/api/apps')
        .then(d => { setApps(d.apps || []); setWebsites(d.websites || []); })
        .catch(() => notify('App list requires the local backend.'));
      refreshNotes(); refreshMemory();
    }
    if (next === 'files') {
      api<{ folders: { key: string; path: string; exists: boolean }[] }>('/api/locations')
        .then(d => setLocations(d.folders)).catch(() => {});
    }
    if (next === 'settings') {
      api<Profile>('/api/profile').then(setProfile).catch(() => {});
      refreshModels();
    }
  }, [notify, refreshMemory, refreshModels, refreshNotes]);

  const loadFolder = useCallback(async (target: string) => {
    setFolderBusy(true); setExpandedFile(null);
    try {
      const listing = await api<FolderResponse>(`/api/files?folder=${encodeURIComponent(target)}`);
      setFileList(listing); setFolder(target); setFileQuery('');
    } catch (error) {
      notify(error instanceof Error ? error.message : 'Could not access that folder.');
    } finally { setFolderBusy(false); }
  }, [notify]);
  useEffect(() => { if (section === 'files' && !fileList) loadFolder('project'); }, [section, fileList, loadFolder]);

  const sendMessage = useCallback(async (custom?: string) => {
    const message = (custom ?? entry).trim();
    if (!message || sending) return;
    if (['stop', 'stop talking', 'stop speaking', 'be quiet'].includes(message.toLowerCase())) {
      try { await api('/stop-speech', json('POST')); } catch { /* speech already stopped locally */ }
      notify('Voice playback stopped'); setEntry(''); return;
    }
    const modeToSend = MODES[section as keyof typeof MODES] || 'normal';
    setEntry(''); setSending(true);
    setSection(current => current === 'home' ? 'chat' : current === 'apps' || current === 'files' || current === 'settings' ? 'chat' : current);
    setMessages(current => [...current, { role: 'user', content: message }]);
    try {
      const response = await api<{ reply: string; model_used: string }>('/chat', json('POST', {
        message, mode: modeToSend, speak: voiceEnabled, ...(selectedModel ? { model: selectedModel } : {}),
      }));
      setMessages(current => [...current, { role: 'assistant', content: response.reply, model: response.model_used }]);
    } catch (error) {
      const reason = error instanceof Error ? error.message : 'Unknown connection error';
      setMessages(current => [...current, {
        role: 'assistant', model: 'connection-error',
        content: `I couldn't reach the AI backend. Check FastAPI (port 8000) and Ollama (port 11434).\n${reason}`,
      }]);
    } finally { setSending(false); }
  }, [entry, sending, section, voiceEnabled, selectedModel, notify]);
  useEffect(() => { sendRef.current = sendMessage; }, [sendMessage]);

  const toggleMic = useCallback(() => {
    if (listening) {
      micRef.current?.stop(); setListening(false); return;
    }
    const BrowserSpeech = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!BrowserSpeech) { notify('Speech recognition is unavailable here. Try Chrome/Edge or type a command.'); return; }
    try {
      const speech = new BrowserSpeech();
      micRef.current = speech;
      speech.lang = 'en-US'; speech.interimResults = true; speech.continuous = false;
      speech.onstart = () => setListening(true);
      speech.onresult = (event: any) => {
        const result = Array.from(event.results).map((r: any) => r[0].transcript).join(' ').trim();
        setEntry(result);
        if (event.results[event.results.length - 1].isFinal) {
          speech.stop(); void sendRef.current(result);
        }
      };
      speech.onerror = (event: any) => {
        setListening(false);
        notify(event.error === 'not-allowed' ? 'Microphone denied. Allow microphone access in your browser.' : `Microphone: ${event.error}`);
      };
      speech.onend = () => { setListening(false); micRef.current = null; };
      speech.start();
    } catch { setListening(false); notify('Could not start microphone.'); }
  }, [listening, notify]);

  useEffect(() => {
    const keyboard = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault(); inputRef.current?.focus();
      }
      if (event.key === 'Escape') { setSection('home'); setMobileNavOpen(false); }
    };
    window.addEventListener('keydown', keyboard);
    return () => { window.removeEventListener('keydown', keyboard); micRef.current?.abort(); };
  }, []);

  const launch = async (name: string, kind: 'app' | 'website') => {
    if (kind === 'website') {
      const site = websites.find(a => a.name === name);
      if (site?.url) { window.open(site.url, '_blank', 'noopener,noreferrer'); return; }
    }
    try {
      const result = await api<ToolResult>('/api/apps/launch', json('POST', { name, kind }));
      notify(result.message || (result.status === 'success' ? `${name} launched` : `Could not launch ${name}`));
    } catch (error) { notify(error instanceof Error ? error.message : 'Launch failed'); }
  };
  const readFile = async (file: FileEntry) => {
    try {
      const response = await api<{ content: string }>(`/api/files/read?path=${encodeURIComponent(file.path)}`);
      setExpandedFile({ name: file.name, content: response.content });
    } catch (error) { notify(error instanceof Error ? error.message : 'Could not read file'); }
  };
  const clearConversation = async () => {
    try { await api('/api/history', json('DELETE')); setMessages([]); notify('Conversation cleared'); }
    catch { notify('Could not clear conversation'); }
  };
  const addNote = async () => {
    if (!newNote.title.trim()) return notify('Give your note a title');
    try { const result = await api<ToolResult>('/api/notes', json('POST', newNote));
      if (result.status !== 'success') throw new Error(result.message || 'Unable to save note');
      setNewNote({ title: '', content: '' }); await refreshNotes(); notify('Note saved on this computer');
    } catch (error) { notify(error instanceof Error ? error.message : 'Unable to save note'); }
  };
  const remember = async () => {
    if (!newMemory.trim()) return;
    try { const result = await api<ToolResult>('/api/memory', json('POST', { fact: newMemory }));
      if (result.status !== 'success') throw new Error(result.message || 'Memory save failed');
      setNewMemory(''); await refreshMemory(); notify('Memory saved locally');
    } catch (error) { notify(error instanceof Error ? error.message : 'Memory save failed'); }
  };
  const saveProfile = async () => {
    setProfileSaving(true);
    try { setProfile(await api<Profile>('/api/profile', json('PATCH', {
      preferred_name: profile.preferred_name || '', tone: profile.tone || '', style: profile.style || '',
    }))); notify('Preferences saved'); }
    catch { notify('Could not save preferences'); }
    finally { setProfileSaving(false); }
  };

  const visibleFiles = useMemo(() => {
    const all = [...(fileList?.folders || []), ...(fileList?.files || [])];
    return all.filter(item => item.name.toLowerCase().includes(fileQuery.toLowerCase()));
  }, [fileList, fileQuery]);
  const showPanel = section !== 'home';
  const isConversation = section === 'chat' || section === 'reasoning' || section === 'coding';

  return (
    <div className="jarvis-shell">
      <div className="grain" aria-hidden="true" />
      <div className={`world-stage ${showPanel ? 'world-muted' : ''}`}>
        <HUD />
        <div className="world-render"><GlobeScene active={sending || listening} /></div>
      </div>
      <header className="top-header">
        <button className="brand" aria-label="JARVIS home" onClick={() => navigate('home')}>
          <span className="brand-emblem"><span className="brand-emblem-core" /></span>
          <span className="brand-type"><strong>JARVIS</strong><small>LOCAL OS V2.0</small></span>
        </button>
        <div className="header-right"><div className="current-clock">{formatClock(now)}</div>
          <div className="current-date">{formatDate(now)}</div><span className="time-bracket" />
        </div>
        <button className="menu-mobile" onClick={() => setMobileNavOpen(!mobileNavOpen)} aria-label="Open navigation">
          <Layers3 size={21} /></button>
      </header>
      <aside className={`sidebar ${mobileNavOpen ? 'sidebar-open' : ''}`} aria-label="Primary navigation">
        <div className="nav-rule" />
        <nav className="sidebar-links">
          {NAV.map(item => { const Icon = item.icon; return (
            <button key={item.id} className={`nav-item ${section === item.id ? 'nav-active' : ''}`}
              onClick={() => navigate(item.id)} aria-current={section === item.id ? 'page' : undefined}>
              <Icon size={24} strokeWidth={1.65} /><span>{item.title}</span>
              {section === item.id && <span className="nav-arrow" />}
            </button>
          ); })}
        </nav>
        <div className="sidebar-bottom"><span className="tiny-pulse" /> SYSTEM {status?.backend_online ? 'CONNECTED' : 'OFFLINE'}</div>
      </aside>
      <aside className="telemetry" aria-label="Live system telemetry">
        <div className="corner-panel system-panel">
          <div className="panel-heading">SYSTEM <Activity size={13}/></div>
          <CircularMetric label="CPU" value={metrics?.cpu ?? null} />
          <CircularMetric label="RAM" value={metrics?.ram ?? null} detail={metrics ? `${metrics.ram_used_gb} / ${metrics.ram_total_gb} GB` : undefined}/>
          <CircularMetric label="GPU" value={metrics?.gpu ?? null} detail={metrics?.gpu == null ? 'NVIDIA telemetry unavailable on this system' : undefined}/>
        </div>
        <div className="corner-panel status-panel">
          <div className="panel-heading">STATUS <Wifi size={13}/></div>
          <StatusItem label={status ? 'JARVIS Online' : 'Backend Offline'} on={!!status?.backend_online} />
          <StatusItem label={status?.models_ready ? 'Models Ready' : 'Models Unavailable'} on={!!status?.models_ready} />
          <StatusItem label="Memory Active" on={!!status?.memory_active} />
          <StatusItem label={status?.ollama_online ? 'Ollama Connected' : 'Ollama Offline'} on={!!status?.ollama_online} />
        </div>
        <button className="telemetry-refresh" onClick={() => {refreshStatus();refreshMetrics();refreshModels();}}>
          <RotateCcw size={13}/> REFRESH TELEMETRY
        </button>
      </aside>

      <AnimatePresence mode="wait">
        {showPanel && <motion.main key={section} className="content-layer"
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 6 }}
          transition={{ duration: .23 }}>
          <div className="workspace-panel">
            <div className="workspace-header">
              <div><div className="eyebrow">JARVIS / {section.toUpperCase()} <span className="separator-dot">•</span> ACTIVE WORKSPACE</div>
                <h1>{isConversation ? section === 'reasoning' ? 'REASONING ENGINE' : section === 'coding' ? 'CODING STUDIO' : 'COMMAND CENTER'
                  : section === 'apps' ? 'APPLICATIONS' : section === 'files' ? 'FILE EXPLORER' : 'SYSTEM SETTINGS'}</h1>
              </div>
              <button className="icon-button close-workspace" title="Back to home" onClick={() => navigate('home')}><X size={18}/></button>
            </div>

            {isConversation && <div className="conversation">
              <div className="conversation-tools">
                <span className="mono-status"><span className={`tiny-pulse ${sending ? 'busy' : ''}`} /> {sending ? 'PROCESSING QUERY' : LABELS[mode]}</span>
                <div className="row-actions"><span className="model-caption">{selectedModel || models?.defaults[mode] || 'LOCAL INFERENCE'}</span>
                  <button className="subtle-button" onClick={clearConversation} title="Clear conversation"><Trash2 size={14}/> CLEAR</button></div>
              </div>
              <div className="messages-scroll">
                {historyReady && messages.length === 0 && <div className="conversation-empty">
                  <div className="empty-symbol">{section === 'coding' ? <Code2 size={37}/> : section === 'reasoning' ? <BrainCircuit size={37}/> : <MessageSquare size={37}/>}</div>
                  <h2>{section === 'coding' ? 'Let’s build something.' : section === 'reasoning' ? 'Ready to think deeper.' : 'How can I assist you?'}</h2>
                  <p>{section === 'coding' ? 'Ask for code, debugging, or architecture guidance.' : section === 'reasoning' ? 'Explore a complex question with a local reasoning model.' : 'Enter a command below or use your microphone.'}</p>
                  <div className="suggestions">
                    {(section === 'coding' ? ['Write a Python API', 'Explain this stack trace'] : section === 'reasoning' ? ['Help me plan a project', 'Break down a difficult concept'] : ['What can you do?', 'Check system status']).map(s =>
                      <button key={s} onClick={() => sendMessage(s)}>{s}<ArrowUpRight size={13}/></button>
                    )}
                  </div>
                </div>}
                {messages.map((message, i) => <div key={i} className={`chat-message ${message.role}`}>
                  <div className="message-avatar">{message.role === 'assistant' ? <Cpu size={17}/> : 'U'}</div>
                  <div className="message-body"><div className="message-heading">{message.role === 'assistant' ? 'JARVIS' : 'YOU'}
                    {message.model && <span>{message.model}</span>}</div><div className="message-content">{message.content}</div></div>
                  {message.role === 'assistant' && <button className="copy-message" title="Copy response" onClick={() => { navigator.clipboard?.writeText(message.content);notify('Response copied'); }}><Copy size={14}/></button>}
                </div>)}
                {sending && <div className="chat-message assistant"><div className="message-avatar"><Cpu size={17}/></div>
                  <div className="message-body"><div className="message-heading">JARVIS</div><div className="typing"><i/><i/><i/></div></div></div>}
                <div ref={bottomRef} />
              </div>
            </div>}

            {section === 'apps' && <div className="workspace-content">
              <div className="tab-row"><button className={appTab === 'launch' ? 'tab-active' : ''} onClick={() => setAppTab('launch')}><AppWindow size={16}/> LAUNCHPAD</button>
                <button className={appTab === 'notes' ? 'tab-active' : ''} onClick={() => setAppTab('notes')}><FileText size={16}/> NOTES</button>
                <button className={appTab === 'memory' ? 'tab-active' : ''} onClick={() => setAppTab('memory')}><MemoryStick size={16}/> MEMORY</button></div>
              {appTab === 'launch' && <div className="launch-content"><p className="helper-text">Open configured desktop apps and trusted websites. Application launch requires the local backend.</p>
                <div className="section-label">DESKTOP APPLICATIONS</div>
                <div className="launch-grid">{apps.map(a => <button key={a} className="launch-tile" onClick={() => launch(a, 'app')}><Monitor size={23}/><span>{a.toUpperCase()}</span><ArrowUpRight size={14}/></button>)}
                  {apps.length === 0 && <p className="muted">Connect the backend to list configured applications.</p>}</div>
                <div className="section-label">WEB DESTINATIONS</div>
                <div className="launch-grid">{websites.map(a => <button key={a.name} className="launch-tile" onClick={() => launch(a.name,'website')}><ExternalLink size={23}/><span>{a.name.toUpperCase()}</span><ArrowUpRight size={14}/></button>)}</div>
              </div>}
              {appTab === 'notes' && <div className="notes-layout"><div className="notes-editor"><div className="section-label">CREATE A NOTE</div>
                <input className="field" placeholder="Note title" value={newNote.title} maxLength={100} onChange={e => setNewNote(n => ({...n,title:e.target.value}))}/>
                <textarea className="field" rows={5} placeholder="Write something worth keeping..." value={newNote.content} onChange={e=>setNewNote(n=>({...n,content:e.target.value}))}/>
                <button className="action-button" onClick={addNote}><Plus size={16}/> SAVE NOTE</button></div>
                <div className="notes-library"><div className="section-label">SAVED NOTES</div>
                  {notes.length ? notes.map(n => <div className="note-card" key={n.file}><strong>{n.file.replace(/\.txt$/,'')}</strong><p>{n.content}</p></div>) : <p className="muted">No notes saved yet.</p>}</div></div>}
              {appTab === 'memory' && <div className="memory-layout"><div className="section-label">LONG-TERM LOCAL MEMORY</div>
                <p className="helper-text">Saved facts are included in the assistant's context when you chat.</p>
                <div className="memory-box">{memory || 'No stored memories yet.'}</div>
                <div className="memory-add"><input className="field" placeholder="Remember that..." value={newMemory} onChange={e=>setNewMemory(e.target.value)} onKeyDown={e=>{if(e.key==='Enter')remember();}}/>
                  <button className="action-button" onClick={remember}><Plus size={16}/> REMEMBER</button></div></div>}
            </div>}

            {section === 'files' && <div className="workspace-content file-workspace">
              <div className="file-toolbar"><select aria-label="Choose accessible folder" value={locations.some(l=>l.key===folder) ? folder : ''}
                onChange={e => loadFolder(e.target.value)} className="field compact-select">
                <option value="" disabled>FOLDERS</option>
                {locations.filter(l=>l.exists).map(l=><option key={l.key} value={l.key}>{l.key.toUpperCase()}</option>)}
              </select><button className="subtle-button" onClick={()=>loadFolder('project')}><Home size={15}/> PROJECT</button>
                <div className="files-search"><Search size={15}/><input placeholder="Filter files..." value={fileQuery} onChange={e=>setFileQuery(e.target.value)}/></div></div>
              <div className="file-path"><FolderOpen size={16}/><span>{fileList?.folder ? shortPath(fileList.folder) : 'Loading workspace...'}</span>
                <button title="Parent folder" onClick={()=>{
                  if (!fileList?.folder) return;
                  const current=fileList.folder.replace(/\\/g,'/');
                  const parent=current.slice(0,current.lastIndexOf('/')) || '/';loadFolder(parent);
                }}><ArrowLeft size={16}/></button></div>
              <div className="files-scroll">{folderBusy ? <div className="muted">Reading folder...</div> : visibleFiles.length ? visibleFiles.map((file,i) =>
                <button key={`${file.path}-${i}`} className="file-row" onClick={()=>file.type==='folder'?loadFolder(file.path):readFile(file)}>
                  {file.type==='folder'?<Folder size={18}/>:file.extension?.match(/\.(ts|js|tsx|jsx|py|json|css)$/)?<FileCode2 size={18}/>:<FileText size={18}/>}
                  <span className="file-name">{file.name}</span><span className="file-size">{file.type==='folder'?'FOLDER':formatBytes(file.size_bytes)}</span><ChevronRight size={16}/></button>
              ) : <div className="muted">No matching files in this folder.</div>}</div>
              <AnimatePresence>{expandedFile && <motion.div className="file-reader" initial={{opacity:0,y:15}} animate={{opacity:1,y:0}} exit={{opacity:0,y:10}}>
                <div className="file-reader-head"><strong>{expandedFile.name}</strong><button onClick={()=>setExpandedFile(null)} title="Close file preview"><X size={17}/></button></div>
                <pre>{expandedFile.content}</pre></motion.div>}</AnimatePresence>
              <div className="file-footer"><ShieldCheck size={15}/> Folders restricted by backend allowlist. File contents are only read on click.</div>
            </div>}

            {section === 'settings' && <div className="workspace-content settings-workspace">
              <div className="settings-section"><div className="section-label">AI CONFIGURATION</div>
                <label className="settings-row"><span><strong>Model override</strong><small>Choose an installed Ollama model or use mode defaults</small></span>
                  <select className="field settings-select" value={selectedModel} onChange={e=>setSelectedModel(e.target.value)}>
                    <option value="">AUTO / MODE DEFAULT</option>
                    {models?.installed.map(m=><option value={m} key={m}>{m}</option>)}
                  </select></label>
                {!models?.online && <div className="info-line"><CircleHelp size={16}/> Ollama is offline. Run <code>ollama serve</code> and install a model to enable AI responses.</div>}
                <label className="settings-row"><span><strong>Voice responses</strong><small>Read AI responses aloud using the backend speech engine</small></span>
                  <button role="switch" aria-checked={voiceEnabled} className={`switch ${voiceEnabled?'switch-on':''}`} onClick={()=>setVoiceEnabled(!voiceEnabled)}><span/></button></label>
              </div>
              <div className="settings-section"><div className="section-label">PERSONALIZATION</div>
                <label className="settings-field">Preferred name<input className="field" value={profile.preferred_name || ''} onChange={e=>setProfile(v=>({...v, preferred_name:e.target.value}))} placeholder="How should JARVIS address you?"/></label>
                <label className="settings-field">Tone<input className="field" value={profile.tone || ''} onChange={e=>setProfile(v=>({...v,tone:e.target.value}))} placeholder="Clear, helpful, composed"/></label>
                <label className="settings-field">Response style<input className="field" value={profile.style || ''} onChange={e=>setProfile(v=>({...v,style:e.target.value}))} placeholder="Concise and direct"/></label>
                <button className="action-button" disabled={profileSaving} onClick={saveProfile}><Save size={16}/> {profileSaving?'SAVING...':'SAVE PREFERENCES'}</button>
              </div>
              <div className="settings-section"><div className="section-label">DATA & DIAGNOSTICS</div>
                <div className="setting-diagnostics"><span><Cpu size={16}/> BACKEND</span><strong>{status ? 'ONLINE' : 'OFFLINE'}</strong>
                  <span><HardDrive size={16}/> LOCAL INFERENCE</span><strong>{status?.ollama_online ? 'CONNECTED' : 'DISCONNECTED'}</strong>
                  <span><MemoryStick size={16}/> INSTALLED MODELS</span><strong>{models?.installed.length ?? 0}</strong></div>
                <button className="danger-button" onClick={clearConversation}><Trash2 size={16}/> CLEAR CONVERSATION HISTORY</button>
              </div>
            </div>}
          </div>
        </motion.main>}
      </AnimatePresence>

      <div className="bottom-console">
        <div className="dock-ear left-ear" /><div className="dock-ear right-ear" />
        <button className={`mic-button ${listening ? 'mic-listening' : ''}`} onClick={toggleMic} title={listening?'Stop recording':'Speak a command'} aria-label="Microphone">
          {listening ? <MicOff size={29} strokeWidth={1.7}/> : <Mic size={29} strokeWidth={1.7}/>}</button>
        <div className="command-field"><input ref={inputRef} aria-label="Command input" value={entry} onChange={e=>setEntry(e.target.value)}
          onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey) {e.preventDefault();void sendMessage();}}}
          placeholder={listening ? 'Listening for your command...' : sending ? 'Processing your command...' : 'Give a command, ask a question, or run a task...'} />
          <div className={`signal-waves ${listening?'wave-listening':''}`} title={listening ? 'Listening' : 'Voice activity'}>
            {[8,15,24,12,28,17,9,20,12].map((h,i)=><i key={i} style={{height:h,animationDelay:`${i*.075}s`}} />)}
          </div>
          <button className={`voice-toggle ${voiceEnabled?'voice-on':''}`} onClick={()=>setVoiceEnabled(!voiceEnabled)} title={voiceEnabled?'Disable spoken responses':'Enable spoken responses'}>
            {voiceEnabled?<Volume2 size={16}/>:<VolumeX size={16}/>}</button>
          <button className="send-button" disabled={sending||!entry.trim()} title="Send command" aria-label="Send command" onClick={()=>void sendMessage()}>
            {sending?<span className="send-spinner"/>:<Send size={26} strokeWidth={1.5}/>}</button>
        </div>
        <div className="dock-label"><span>{listening?'VOICE INPUT ACTIVE':sending?'ASSISTANT PROCESSING':'COMMAND INTERFACE READY'}</span><span>CTRL + K TO FOCUS</span></div>
      </div>
      <AnimatePresence>{notice && <motion.div role="status" key={notice} className="toast" initial={{opacity:0,y:15}} animate={{opacity:1,y:0}} exit={{opacity:0,y:5}}>
        <Bell size={16}/><span>{notice}</span><button title="Dismiss" onClick={()=>setNotice('')}><X size={13}/></button></motion.div>}</AnimatePresence>
    </div>
  );
}
