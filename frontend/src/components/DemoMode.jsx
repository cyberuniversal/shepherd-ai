import { useEffect, useRef, useState } from 'react';
import { Film, Play, Square } from 'lucide-react';
import { Button } from '@/components/ui/button';

const DEMO_DURATION_MS = 60000;

const DemoMode = ({ addLog, handleCommand, setFocusedDroneId, setTemp, simulateCrash, reviveDrone }) => {
  const [demoRunning, setDemoRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const stoppedRef = useRef(false);
  const progressIntervalRef = useRef(null);

  useEffect(() => {
    return () => {
      stoppedRef.current = true;
      clearInterval(progressIntervalRef.current);
    };
  }, []);

  const waitUntil = async (startTime, targetMs) => {
    while (!stoppedRef.current) {
      const remaining = targetMs - (Date.now() - startTime);
      if (remaining <= 0) return;
      await new Promise(resolve => setTimeout(resolve, Math.min(remaining, 250)));
    }
  };

  const stopDemo = () => {
    stoppedRef.current = true;
    clearInterval(progressIntervalRef.current);
    setDemoRunning(false);
    setFocusedDroneId(null);
    addLog('Demo Mode stopped.', 'info');
  };

  const runDemo = async () => {
    if (demoRunning) return;

    stoppedRef.current = false;
    setDemoRunning(true);
    setProgress(0);
    const startTime = Date.now();

    clearInterval(progressIntervalRef.current);
    progressIntervalRef.current = setInterval(() => {
      const elapsed = Date.now() - startTime;
      setProgress(Math.min(100, (elapsed / DEMO_DURATION_MS) * 100));
    }, 250);

    const demoSteps = [
      { at: 0, action: () => addLog('Demo Mode: Initiating tactical scenario...', 'info') },
      { at: 2000, action: () => handleCommand('deploy 5 drones to scan KAFD') },
      { at: 6000, action: () => setFocusedDroneId('alpha-1') },
      { at: 12000, action: () => setTemp(48) },
      { at: 16000, action: () => addLog('Environmental stress applied: thermal throttling should now be visible.', 'error') },
      { at: 22000, action: () => simulateCrash('alpha-2') },
      { at: 26000, action: () => addLog('Dynamic re-tasking checkpoint complete.', 'success') },
      { at: 32000, action: () => handleCommand('send beta-1 to secure the airport') },
      { at: 38000, action: () => setTemp(30) },
      { at: 42000, action: () => reviveDrone('alpha-2') },
      { at: 48000, action: () => handleCommand('recall all drones') },
      { at: 55000, action: () => setFocusedDroneId(null) },
      { at: 60000, action: () => addLog('Demo complete. All headline features demonstrated.', 'success') },
    ];

    for (const step of demoSteps) {
      await waitUntil(startTime, step.at);
      if (stoppedRef.current) break;
      await step.action();
    }

    clearInterval(progressIntervalRef.current);
    if (!stoppedRef.current) {
      setProgress(100);
      setDemoRunning(false);
    }
  };

  return (
    <div className="absolute bottom-5 left-5 z-40 w-64 rounded-xl border border-primary/50 bg-card/90 p-3 shadow-[0_0_24px_rgba(16,185,129,0.25)] backdrop-blur-sm">
      <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-primary">
        <Film size={16} />
        Demo Mode
      </div>
      <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
        Runs a 60-second mission script covering voice-ready NLP, search patterns, thermal stress, failure recovery, and recall.
      </p>
      <div className="mt-3 flex gap-2">
        {!demoRunning ? (
          <Button onClick={runDemo} className="h-8 flex-1 text-xs font-bold uppercase tracking-widest">
            <Play size={14} /> Run
          </Button>
        ) : (
          <Button variant="destructive" onClick={stopDemo} className="h-8 flex-1 text-xs font-bold uppercase tracking-widest">
            <Square size={14} /> Stop Demo
          </Button>
        )}
      </div>
      {demoRunning && (
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-muted">
          <div className="h-full bg-primary transition-all" style={{ width: `${progress}%` }} />
        </div>
      )}
    </div>
  );
};

export default DemoMode;
