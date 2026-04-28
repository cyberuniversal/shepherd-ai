import { useState, useEffect, useRef } from 'react';
import MapComponent from './components/Map';
import CommandConsole from './components/CommandConsole';
import DemoMode from './components/DemoMode';
import { Battery, ThermometerSun, Brain, Zap, Radio, Shield, Code2 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import './index.css';

const getApiBaseUrl = () => {
  if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL;
  if (typeof window === 'undefined') return 'http://localhost:8000';
  return `${window.location.protocol}//${window.location.hostname}:8000`;
};

const API_BASE_URL = getApiBaseUrl();
const WS_URL = typeof window === 'undefined'
  ? 'ws://localhost:8000/ws/fleet'
  : `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.hostname}:8000/ws/fleet`;

let audioContext;

const getAudioContext = () => {
  if (typeof window === 'undefined') return null;
  const AudioContext = window.AudioContext || window.webkitAudioContext;
  if (!AudioContext) return null;
  audioContext ||= new AudioContext();
  return audioContext;
};

const playTone = (frequency, duration = 0.08, volume = 0.04, type = 'sine', delay = 0) => {
  const ctx = getAudioContext();
  if (!ctx) return;
  const oscillator = ctx.createOscillator();
  const gain = ctx.createGain();
  const start = ctx.currentTime + delay;
  oscillator.type = type;
  oscillator.frequency.setValueAtTime(frequency, start);
  gain.gain.setValueAtTime(0.0001, start);
  gain.gain.exponentialRampToValueAtTime(volume, start + 0.01);
  gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
  oscillator.connect(gain);
  gain.connect(ctx.destination);
  oscillator.start(start);
  oscillator.stop(start + duration + 0.02);
};

const playCommandSound = () => playTone(880, 0.07, 0.035, 'square');
const playCrashSound = () => {
  playTone(220, 0.14, 0.05, 'sawtooth');
  playTone(140, 0.18, 0.04, 'sawtooth', 0.12);
};
const playMissionCompleteSound = () => {
  playTone(660, 0.08, 0.035, 'triangle');
  playTone(990, 0.1, 0.035, 'triangle', 0.1);
};

function App() {
  const [fleet, setFleet] = useState([]);
  const [stats, setStats] = useState(null);
  const [logs, setLogs] = useState([
    { id: 1, text: "System initialized. Swarm online.", type: "info" }
  ]);
  const [thinkingLog, setThinkingLog] = useState([]);
  const [missionPrograms, setMissionPrograms] = useState([]);
  const [actionScripts, setActionScripts] = useState([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedDrones, setSelectedDrones] = useState([]);
  const [ambientTemp, setAmbientTemp] = useState(null);
  const [tempSource, setTempSource] = useState('default');
  const [gpsDenied, setGpsDenied] = useState(false);
  const [focusedDroneId, setFocusedDroneId] = useState(null);
  const [activeTab, setActiveTab] = useState('logs'); // 'logs' | 'thinking' | 'program'
  const [wsFailureCount, setWsFailureCount] = useState(0);
  const [fleetAlert, setFleetAlert] = useState(false);
  const logsEndRef = useRef(null);
  const thinkingEndRef = useRef(null);
  const wsDisconnectLogged = useRef(false);
  const previousFleetStatusesRef = useRef({});
  const tempCommitTimeoutRef = useRef(null);

  const addLog = (text, type = "info") => {
    setLogs(prev => [...prev, { id: Date.now() + Math.random(), text, type }]);
  };

  const syncRiyadhTemp = async (force = true) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/weather/riyadh?force=${force}`);
      if (!res.ok) throw new Error('Weather sync failed');
      const data = await res.json();
      setAmbientTemp(data.temp);
      setTempSource(data.source || 'riyadh_live');
      if (force) {
        addLog(`Riyadh live temperature synced: ${data.temp}°C`, data.error ? 'error' : 'info');
      }
    } catch {
      if (force) addLog('Failed to sync Riyadh live temperature.', 'error');
    }
  };

  useEffect(() => {
    return () => clearTimeout(tempCommitTimeoutRef.current);
  }, []);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  useEffect(() => {
    thinkingEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [thinkingLog]);

  useEffect(() => {
    const previousStatuses = previousFleetStatusesRef.current;
    const hadPreviousTelemetry = Object.keys(previousStatuses).length > 0;
    const arrivedOnStation = fleet.some(
      drone => drone.status === 'on_station' && previousStatuses[drone.id] && previousStatuses[drone.id] !== 'on_station'
    );

    if (hadPreviousTelemetry && arrivedOnStation) {
      playMissionCompleteSound();
    }

    previousFleetStatusesRef.current = Object.fromEntries(fleet.map(drone => [drone.id, drone.status]));
  }, [fleet]);

  useEffect(() => {
    let ws;
    let reconnectTimeout;
    let cancelled = false;

    const connectWs = () => {
      if (cancelled) return;
      ws = new WebSocket(WS_URL);
      
      ws.onopen = () => {
        setWsConnected(true);
        setWsFailureCount(0);
        wsDisconnectLogged.current = false;
        addLog("WebSocket connected to fleet backend.", "info");
      };
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        // New format: { drones: [...], stats: {...}, thinking_log: [...] }
        if (data.drones) {
          setFleet(data.drones);
        }
        if (data.stats) {
          setStats(data.stats);
          setAmbientTemp(data.stats.ambient_temp);
          setTempSource(data.stats.ambient_temp_source || 'default');
          setGpsDenied(Boolean(data.stats.gps_denied));
        }
        if (data.thinking_log) {
          setThinkingLog(data.thinking_log);
        }
      };
      
      ws.onclose = () => {
        if (cancelled) return;
        setWsConnected(false);
        setWsFailureCount(prev => prev + 1);
        if (!wsDisconnectLogged.current) {
          addLog("WebSocket connection lost. Reconnecting...", "error");
          wsDisconnectLogged.current = true;
        }
        reconnectTimeout = setTimeout(connectWs, 3000);
      };
    };

    connectWs();
    return () => {
      cancelled = true;
      if (ws) ws.close();
      clearTimeout(reconnectTimeout);
    };
  }, []);

  const toggleDroneSelection = (id) => {
    setSelectedDrones(prev => 
      prev.includes(id) ? prev.filter(d => d !== id) : [...prev, id]
    );
  };

  const selectAllDrones = () => {
    setSelectedDrones(fleet.filter(drone => drone.status !== 'offline').map(drone => drone.id));
  };

  const deselectAllDrones = () => {
    setSelectedDrones([]);
  };

  const selectSquadron = (squadron) => {
    setSelectedDrones(
      fleet
        .filter(drone => drone.status !== 'offline' && drone.id.startsWith(`${squadron}-`))
        .map(drone => drone.id)
    );
  };

  const commitTemp = async (newTemp) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/environment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ temp: newTemp })
      });
      const data = await res.json();
      addLog(data.message, data.throttling ? "error" : "info");
    } catch {
      addLog("Failed to set temperature.", "error");
    }
  };

  const setTemp = (newTemp) => {
    setAmbientTemp(newTemp);
    setTempSource('manual');
    clearTimeout(tempCommitTimeoutRef.current);
    tempCommitTimeoutRef.current = setTimeout(() => commitTemp(newTemp), 300);
  };

  const toggleGpsDenied = async () => {
    const nextValue = !gpsDenied;
    setGpsDenied(nextValue);
    try {
      const res = await fetch(`${API_BASE_URL}/api/gps-denied`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: nextValue })
      });
      const data = await res.json();
      addLog(data.message, nextValue ? "error" : "info");
    } catch {
      setGpsDenied(!nextValue);
      addLog("Failed to toggle GPS-denied simulation.", "error");
    }
  };

  const handleCommand = async (command) => {
    setIsLoading(true);
    playCommandSound();
    addLog(`> ${command} ${selectedDrones.length > 0 ? `(Targeting: ${selectedDrones.join(', ')})` : ''}`, "info");
    try {
      const res = await fetch(`${API_BASE_URL}/api/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command, selected_drones: selectedDrones })
      });
      const data = await res.json();

      const intents = data.intents || (data.intent ? [data.intent] : []);
      intents.forEach((intent, index) => {
        addLog(
          `Intent ${index + 1}/${intents.length}: Action=${intent.action}, Target=${intent.target_zone}, Count=${intent.drone_count || 1}, Pattern=${intent.pattern || 'perimeter'}`,
          "info"
        );
      });
      if (data.assigned && data.assigned.length > 0) {
        addLog(`Tasked: ${data.assigned.join(', ')}`, "success");
      } else {
        addLog("No drones available for assignment.", "error");
        setFleetAlert(true);
        setTimeout(() => setFleetAlert(false), 1200);
      }

      if (data.mission_programs?.length) {
        setMissionPrograms(data.mission_programs);
        const droneProgramCount = data.mission_programs.reduce((total, program) => total + program.summary.drone_count, 0);
        const stepCount = data.mission_programs.reduce((total, program) => total + program.summary.step_count, 0);
        addLog(`Compiled ${data.mission_programs[0].language}: ${droneProgramCount} drone programs, ${stepCount} executable steps.`, "success");
      }
      if (data.action_scripts?.length) {
        setActionScripts(data.action_scripts);
        const sandboxPassed = data.action_scripts.every(script => script.sandbox?.passed);
        addLog(
          `Real-Time Mission Synthesis: ${data.action_scripts.length} disposable Python action script${data.action_scripts.length === 1 ? '' : 's'} generated; sandbox ${sandboxPassed ? 'passed' : 'flagged issues'}.`,
          sandboxPassed ? "success" : "error"
        );
      }
    } catch {
      addLog("Failed to execute command. Backend unreachable.", "error");
    } finally {
      setIsLoading(false);
      setSelectedDrones([]);
    }
  };

  const simulateCrash = async (droneId) => {
    try {
      playCrashSound();
      addLog(`Simulating critical failure for ${droneId}...`, "error");
      const res = await fetch(`${API_BASE_URL}/api/crash`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ drone_id: droneId })
      });
      const data = await res.json();
      addLog(data.message, "info");
      if (focusedDroneId === droneId) setFocusedDroneId(null);
    } catch {
      addLog("Failed to simulate crash.", "error");
    }
  };

  const reviveDrone = async (droneId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/revive`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ drone_id: droneId })
      });
      const data = await res.json();
      addLog(data.message, "success");
    } catch {
      addLog("Failed to revive drone.", "error");
    }
  };

  const exportManifest = () => {
    const manifest = {
      timestamp: new Date().toISOString(),
      ambient_temperature: ambientTemp,
      ambient_temperature_source: tempSource,
      fleet_status: fleet,
      fleet_stats: stats,
      mission_programs: missionPrograms,
      action_scripts: actionScripts,
      tactical_logs: logs,
      ai_thinking_log: thinkingLog
    };
    const blob = new Blob([JSON.stringify(manifest, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `shepherd_manifest_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    addLog("Mission Manifest exported to local storage.", "success");
  };

  const getStatusColor = (status) => {
    switch(status) {
      case 'assigned': return 'default';
      case 'on_station': return 'default';
      case 'returning': return 'secondary';
      case 'offline': return 'destructive';
      default: return 'secondary';
    }
  };

  const allOffline = fleet.length > 0 && fleet.every(drone => drone.status === 'offline');
  const tempValue = ambientTemp ?? 30;
  const latestOodaEvents = actionScripts.flatMap(script => script.ooda_events || []).slice(-4);

  const formatDuration = (seconds = 0) => {
    const minutes = Math.floor(seconds / 60).toString().padStart(2, '0');
    const secs = Math.floor(seconds % 60).toString().padStart(2, '0');
    return `${minutes}:${secs}`;
  };

  const getNavConfidenceColor = (confidence = 1) => {
    if (confidence < 0.3) return 'text-destructive';
    if (confidence < 0.65) return 'text-amber-400';
    return 'text-primary';
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-background text-foreground">
      {/* Top Bar */}
      <header className="flex items-center justify-between px-8 py-3 bg-card border-b shadow-lg z-50 shrink-0">
        <div className="flex items-center gap-4">
          <span className="text-3xl text-primary font-bold">الراعي</span>
          <h1 className="m-0 text-xl tracking-widest uppercase">Shepherd-AI</h1>
        </div>

        {/* Stats Bar */}
        {stats && (
          <div className="flex gap-6 text-xs font-mono">
            <div className="flex items-center gap-1.5">
              <Zap size={14} className="text-primary" />
              <span className="text-muted-foreground">ONLINE</span>
              <span className="text-foreground font-bold">{stats.online}/{stats.total}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Radio size={14} className="text-primary" />
              <span className="text-muted-foreground">ACTIVE</span>
              <span className="text-foreground font-bold">{stats.assigned}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Battery size={14} className={stats.avg_battery > 30 ? 'text-primary' : 'text-destructive'} />
              <span className="text-muted-foreground">AVG BAT</span>
              <span className="text-foreground font-bold">{stats.avg_battery}%</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Shield size={14} className="text-primary" />
              <span className="text-muted-foreground">IDLE</span>
              <span className="text-foreground font-bold">{stats.idle}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-muted-foreground">HEALTH</span>
              <span className="text-foreground font-bold">{stats.fleet_health}%</span>
            </div>
          </div>
        )}

        <div className="flex gap-4 text-sm text-muted-foreground items-center">
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full shadow-[0_0_10px_currentColor] ${wsConnected ? 'bg-primary text-primary' : 'bg-destructive text-destructive'}`}></span>
            <span className="text-xs font-mono">{wsConnected ? 'UPLINK ACTIVE' : 'UPLINK OFFLINE'}</span>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={toggleGpsDenied}
            className={`text-xs ${gpsDenied ? 'border-destructive text-destructive bg-destructive/10' : 'text-muted-foreground'}`}
          >
            GPS {gpsDenied ? 'DENIED' : 'OK'}
          </Button>
          <div className="flex items-center gap-2 text-primary min-w-44">
            <ThermometerSun size={16} className={tempValue > 45 ? 'text-destructive' : 'text-primary'} />
            <input
              type="range"
              min="20"
              max="55"
              value={Math.round(tempValue)}
              onChange={(e) => setTemp(Number(e.target.value))}
              className="w-24 cursor-pointer"
              style={{ accentColor: tempValue > 45 ? '#ef4444' : '#10b981' }}
              title="Ambient temperature"
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => syncRiyadhTemp(true)}
              className={`h-7 px-2 text-[10px] ${tempSource === 'riyadh_live' ? 'border-primary text-primary' : 'text-muted-foreground'}`}
              title="Sync live Riyadh weather"
            >
              LIVE
            </Button>
            <span className={`text-xs font-mono w-10 ${tempValue > 45 ? 'text-destructive' : 'text-primary'}`}>
              {ambientTemp !== null ? `${Math.round(tempValue)}°C` : '...'}
            </span>
            <span className="text-[9px] font-mono uppercase text-muted-foreground w-12">
              {tempSource === 'riyadh_live' ? 'Riyadh' : tempSource}
            </span>
          </div>
          <Button variant="outline" size="sm" onClick={exportManifest} className="text-primary border-primary hover:bg-primary hover:text-primary-foreground text-xs">
            EXPORT
          </Button>
        </div>
      </header>

      {wsFailureCount >= 3 && !wsConnected && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-background/90 backdrop-blur-sm">
          <div className="max-w-md rounded-xl border border-destructive/60 bg-card p-6 text-center shadow-[0_0_30px_rgba(239,68,68,0.25)]">
            <h2 className="text-lg font-bold uppercase tracking-widest text-destructive">Backend offline</h2>
            <p className="mt-3 text-sm text-muted-foreground">
              Start the app from the project root with <code className="text-primary">npm run dev</code>. It launches both backend and frontend.
            </p>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="flex flex-1 overflow-hidden relative">
        {allOffline && (
          <div className="absolute top-4 left-1/2 z-40 -translate-x-1/2 rounded-lg border border-destructive bg-destructive/15 px-5 py-2 text-xs font-bold uppercase tracking-widest text-destructive shadow-lg">
            SWARM DEPLETED - revive drones to continue
          </div>
        )}

        {gpsDenied && (
          <div className="absolute top-14 left-1/2 z-40 -translate-x-1/2 rounded-lg border border-amber-500 bg-amber-500/15 px-5 py-2 text-xs font-bold uppercase tracking-widest text-amber-400 shadow-lg">
            GPS DENIED - dead-reckoning fallback active
          </div>
        )}

        {latestOodaEvents.length > 0 && (
          <div className="absolute right-[440px] top-4 z-40 w-80 rounded-xl border border-cyan-400/50 bg-card/90 p-3 shadow-[0_0_24px_rgba(34,211,238,0.18)] backdrop-blur-sm">
            <div className="text-xs font-bold uppercase tracking-widest text-cyan-400">OODA Decision Tree</div>
            <div className="mt-2 flex flex-col gap-1.5">
              {latestOodaEvents.map((event, index) => (
                <div key={`${event.phase}-${index}`} className="rounded border border-border bg-background/40 px-2 py-1 text-[10px] font-mono text-muted-foreground">
                  <span className="text-cyan-400">{event.phase}:</span> {event.message}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Map Area */}
        <div className="flex-1 relative">
          <MapComponent fleet={fleet} focusedDroneId={focusedDroneId} />
          <DemoMode
            addLog={addLog}
            handleCommand={handleCommand}
            setFocusedDroneId={setFocusedDroneId}
            setTemp={setTemp}
            simulateCrash={simulateCrash}
            reviveDrone={reviveDrone}
          />
        </div>
        
        {/* Side Panel */}
        <aside className={`w-[420px] bg-card border-l shadow-[-4px_0_20px_rgba(0,0,0,0.5)] z-10 flex flex-col transition-all ${fleetAlert ? 'ring-2 ring-destructive shadow-[0_0_30px_rgba(239,68,68,0.35)]' : ''}`}>
          
          {/* Command Console (Sticky at top) */}
          <div className="shrink-0 border-b p-5 bg-card/50 backdrop-blur-sm">
            <CommandConsole onCommand={handleCommand} isLoading={isLoading} />
          </div>
          
          {/* Scrollable Content */}
          <div className="flex-1 overflow-y-auto min-h-0">
            <div className="p-5 flex flex-col gap-6">
              
              {/* Drone List */}
              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="m-0 text-xs text-muted-foreground uppercase tracking-widest font-semibold">
                    Fleet Status ({fleet.length} units)
                  </h3>
                  <div className="flex gap-1.5">
                    <Button variant="outline" size="sm" onClick={selectAllDrones} className="h-6 px-2 text-[9px] text-primary border-primary">
                      SELECT ALL
                    </Button>
                    <Button variant="outline" size="sm" onClick={deselectAllDrones} className="h-6 px-2 text-[9px]">
                      CLEAR
                    </Button>
                  </div>
                </div>
                <div className="grid grid-cols-4 gap-1.5">
                  {['alpha', 'beta', 'gamma', 'delta'].map((squadron) => (
                    <Button
                      key={squadron}
                      variant="outline"
                      size="sm"
                      onClick={() => selectSquadron(squadron)}
                      className="h-6 px-1 text-[9px] uppercase tracking-wider"
                    >
                      {squadron}
                    </Button>
                  ))}
                </div>
                {fleet.length === 0 && <p className="text-sm text-muted-foreground">Waiting for telemetry...</p>}
                {fleet.map(drone => (
                  <Card 
                    key={drone.id} 
                    className={`p-3 flex justify-between items-center cursor-pointer transition-colors border-2 ${
                      drone.status === 'offline' 
                        ? 'border-destructive/50 bg-destructive/10 cursor-not-allowed' 
                        : selectedDrones.includes(drone.id) 
                          ? 'border-primary bg-primary/10' 
                          : 'border-border bg-background/50 hover:border-primary/50'
                    }`}
                    onClick={() => { if (drone.status !== 'offline') toggleDroneSelection(drone.id) }}
                  >
                    <div className="flex flex-col gap-0.5">
                      <span className="font-mono font-bold text-sm">{drone.id.toUpperCase()}</span>
                      <span className="text-xs text-muted-foreground flex items-center gap-1.5">
                        <Battery size={12} className={drone.battery > 20 ? 'text-primary' : 'text-destructive'} />
                        {drone.battery.toFixed(1)}% | Rotor: {drone.rotor_speed.toFixed(0)}%
                      </span>
                      <span className={`text-[10px] font-mono ${getNavConfidenceColor(drone.nav_confidence)}`}>
                        NAV {Math.round((drone.nav_confidence ?? 1) * 100)}% | ALT {Math.round(drone.altitude_m ?? 10)}m | {drone.comms_status || 'connected'}
                      </span>
                    </div>
                    <div className="flex flex-col gap-1.5 items-end">
                      <Badge variant={getStatusColor(drone.status)} className="uppercase text-[9px] px-1.5">
                        {drone.status}
                      </Badge>
                      {drone.mission_duration_s > 0 && (
                        <span className="text-[9px] font-mono text-muted-foreground">T+{formatDuration(drone.mission_duration_s)}</span>
                      )}
                      <div className="flex gap-1.5">
                        {drone.status !== 'offline' && (
                          <>
                            <Button 
                              variant="outline" 
                              size="sm" 
                              className={`h-5 px-1.5 text-[9px] z-10 ${focusedDroneId === drone.id ? 'bg-primary text-primary-foreground border-primary' : 'text-primary border-primary hover:bg-primary hover:text-primary-foreground'}`}
                              onClick={(e) => { e.stopPropagation(); setFocusedDroneId(focusedDroneId === drone.id ? null : drone.id); }}
                              title="FPV Mode"
                            >
                              {focusedDroneId === drone.id ? 'UNFOCUS' : 'FPV'}
                            </Button>
                            <Button 
                              variant="outline" 
                              size="sm" 
                              className="h-5 px-1.5 text-[9px] border-destructive text-destructive hover:bg-destructive hover:text-destructive-foreground z-10"
                              onClick={(e) => { e.stopPropagation(); simulateCrash(drone.id); }}
                              title="Simulate Crash"
                            >
                              KILL
                            </Button>
                          </>
                        )}
                        {drone.status === 'offline' && (
                          <Button 
                            variant="outline" 
                            size="sm" 
                            className="h-5 px-1.5 text-[9px] border-primary text-primary hover:bg-primary hover:text-primary-foreground z-10"
                            onClick={(e) => { e.stopPropagation(); reviveDrone(drone.id); }}
                            title="Revive Drone"
                          >
                            REVIVE
                          </Button>
                        )}
                      </div>
                    </div>
                  </Card>
                ))}
              </div>

              {/* Tab Toggle: Logs vs Thinking vs Program */}
              <div className="flex border-b border-border">
                <button
                  className={`flex-1 py-2 text-xs uppercase tracking-widest font-semibold transition-colors ${
                    activeTab === 'logs' 
                      ? 'text-primary border-b-2 border-primary' 
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                  onClick={() => setActiveTab('logs')}
                >
                  Tactical Logs
                </button>
                <button
                  className={`flex-1 py-2 text-xs uppercase tracking-widest font-semibold transition-colors flex items-center justify-center gap-1.5 ${
                    activeTab === 'thinking' 
                      ? 'text-amber-400 border-b-2 border-amber-400' 
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                  onClick={() => setActiveTab('thinking')}
                >
                  <Brain size={12} />
                  AI Thinking
                </button>
                <button
                  className={`flex-1 py-2 text-xs uppercase tracking-widest font-semibold transition-colors flex items-center justify-center gap-1.5 ${
                    activeTab === 'program'
                      ? 'text-cyan-400 border-b-2 border-cyan-400'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                  onClick={() => setActiveTab('program')}
                >
                  <Code2 size={12} />
                  Program
                </button>
              </div>

              {/* Logs Panel */}
              {activeTab === 'logs' && (
                <div className="flex flex-col gap-2">
                  {logs.map(log => (
                    <div key={log.id} className={`p-2.5 rounded-r bg-background/30 border-l-4 text-xs font-mono leading-relaxed ${
                      log.type === 'error' ? 'border-destructive text-destructive-foreground' : 
                      log.type === 'success' ? 'border-primary text-primary' : 
                      'border-border text-muted-foreground'
                    }`}>
                      {log.text}
                    </div>
                  ))}
                  <div ref={logsEndRef} />
                </div>
              )}

              {/* Thinking Log Panel */}
              {activeTab === 'thinking' && (
                <div className="flex flex-col gap-2">
                  {thinkingLog.length === 0 && (
                    <p className="text-xs text-muted-foreground italic">No AI decisions yet. Send a command to see the AI think...</p>
                  )}
                  {thinkingLog.map((entry, i) => (
                    <div key={`${entry.time}-${i}`} className={`p-2.5 rounded-r bg-background/30 border-l-4 text-xs font-mono leading-relaxed ${
                      entry.category === 'critical' ? 'border-destructive text-destructive-foreground' :
                      entry.category === 'warning' ? 'border-amber-500 text-amber-400' :
                      entry.category === 'decision' ? 'border-primary text-primary' :
                      'border-border text-muted-foreground'
                    }`}>
                      <span className="text-muted-foreground mr-2">[{entry.timestamp}]</span>
                      {entry.message}
                    </div>
                  ))}
                  <div ref={thinkingEndRef} />
                </div>
              )}

              {/* Mission Program Panel */}
              {activeTab === 'program' && (
                <div className="flex flex-col gap-3">
                  {missionPrograms.length === 0 && actionScripts.length === 0 && (
                    <p className="text-xs text-muted-foreground italic">No mission program compiled yet. Send a command to see SHEPHERD-IR and the temporary Python action script.</p>
                  )}
                  {actionScripts.map((script) => (
                    <Card key={script.script_id} className="p-3 bg-background/40 border-cyan-400/40">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-xs font-bold text-cyan-400">Real-Time Mission Synthesis</span>
                        <Badge variant={script.sandbox?.passed ? 'default' : 'destructive'} className="text-[9px] uppercase">
                          Sandbox {script.sandbox?.passed ? 'passed' : 'blocked'}
                        </Badge>
                      </div>
                      <div className="mt-2 text-[10px] font-mono text-muted-foreground">
                        {script.language} | {script.sandbox?.runtime_ms}ms validation | {script.sandbox?.checks?.length || 0} safety checks
                      </div>
                      {script.ooda_events?.length > 0 && (
                        <div className="mt-3 grid grid-cols-2 gap-1.5">
                          {script.ooda_events.map((event, index) => (
                            <div key={`${script.script_id}-${index}`} className="rounded border border-border bg-card/60 p-2 text-[10px] leading-relaxed text-muted-foreground">
                              <span className="font-bold text-cyan-400">{event.phase}</span><br />{event.message}
                            </div>
                          ))}
                        </div>
                      )}
                      <div className="mt-3 max-h-80 overflow-auto rounded border border-border bg-black/40 p-2">
                        <pre className="whitespace-pre-wrap text-[10px] leading-relaxed text-cyan-100">
                          {script.script}
                        </pre>
                      </div>
                    </Card>
                  ))}
                  {missionPrograms.map((program) => (
                    <Card key={program.mission_id} className="p-3 bg-background/40 border-border">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-xs font-bold text-cyan-400">{program.language}</span>
                        <Badge variant="outline" className="text-[9px] uppercase">{program.mode}</Badge>
                      </div>
                      <div className="mt-2 text-[10px] font-mono text-muted-foreground">
                        {program.summary.drone_count} drone programs | {program.summary.step_count} steps | {program.summary.transport}
                      </div>
                      <div className="mt-3 max-h-64 overflow-auto rounded border border-border bg-card/60 p-2">
                        <pre className="whitespace-pre-wrap text-[10px] leading-relaxed text-muted-foreground">
                          {JSON.stringify(program, null, 2)}
                        </pre>
                      </div>
                    </Card>
                  ))}
                </div>
              )}

            </div>
          </div>
        </aside>
      </main>
    </div>
  );
}

export default App;
