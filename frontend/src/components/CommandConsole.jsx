import { useEffect, useRef, useState } from 'react';
import { Terminal, AlertTriangle, Mic, Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

const CommandConsole = ({ onCommand, isLoading }) => {
  const [input, setInput] = useState('');
  const [voiceLang, setVoiceLang] = useState('en-US');
  const [isListening, setIsListening] = useState(false);
  const [isVoiceProcessing, setIsVoiceProcessing] = useState(false);
  const recognitionRef = useRef(null);
  const processingTimeoutRef = useRef(null);

  const speechSupported = typeof window !== 'undefined' &&
    ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window);

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
      clearTimeout(processingTimeoutRef.current);
    };
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onCommand(input);
      setInput('');
    }
  };

  const startListening = () => {
    if (!speechSupported || isLoading) return;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = voiceLang;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript;
      if (transcript) setInput(transcript);
      setIsListening(false);
      setIsVoiceProcessing(true);
      clearTimeout(processingTimeoutRef.current);
      processingTimeoutRef.current = setTimeout(() => setIsVoiceProcessing(false), 500);
    };

    recognition.onerror = () => {
      setIsListening(false);
      setIsVoiceProcessing(false);
    };
    recognition.onend = () => setIsListening(false);

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
  };

  const stopListening = () => {
    recognitionRef.current?.stop();
    setIsListening(false);
  };

  const toggleListening = () => {
    if (isListening) stopListening();
    else startListening();
  };

  return (
    <form className={`flex flex-col gap-4 rounded-xl transition-all ${isListening ? 'ring-2 ring-destructive/50 shadow-[0_0_24px_rgba(239,68,68,0.25)]' : ''}`} onSubmit={handleSubmit}>
      <h3 className="m-0 text-xs text-muted-foreground uppercase tracking-widest font-semibold">
        Tactical Input
      </h3>
      
      <div className="relative flex gap-2 w-full">
        <div className="relative flex-1">
          <Terminal className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={16} />
          <Input 
            type="text" 
            placeholder="Enter command (e.g., تمشيط الوادي الشمالي)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
            dir="auto"
            className="pl-10 bg-background/50 border-border focus-visible:ring-primary h-12 text-base"
          />
        </div>
        <Button
          type="button"
          variant="outline"
          disabled={!speechSupported || isLoading}
          onClick={toggleListening}
          title={speechSupported ? (isListening ? 'Listening...' : 'Start voice input') : 'Voice not supported in this browser'}
          className={`h-12 w-12 p-0 border-border ${isListening ? 'border-destructive text-destructive bg-destructive/10 animate-pulse' : 'text-muted-foreground hover:text-primary'}`}
        >
          {isVoiceProcessing ? <Loader2 className="animate-spin" size={18} /> : <Mic size={18} fill={isListening ? 'currentColor' : 'none'} />}
        </Button>
        <Button 
          type="submit" 
          disabled={!input.trim() || isLoading}
          className="h-12 px-6 font-bold tracking-widest uppercase"
        >
          {isLoading ? 'Wait' : 'Plan'}
        </Button>
      </div>

      <div className="flex items-center justify-between gap-3">
        <div className="inline-flex rounded-lg border border-border bg-background/40 p-1 text-xs font-mono uppercase">
          <button
            type="button"
            onClick={() => setVoiceLang('en-US')}
            className={`rounded-md px-3 py-1 transition-colors ${voiceLang === 'en-US' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
          >
            EN
          </button>
          <button
            type="button"
            onClick={() => setVoiceLang('ar-SA')}
            className={`rounded-md px-3 py-1 transition-colors ${voiceLang === 'ar-SA' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
          >
            AR
          </button>
        </div>
        <span className={`text-[10px] font-mono uppercase ${isListening ? 'text-destructive' : 'text-muted-foreground'}`}>
          {isListening ? 'Listening...' : speechSupported ? `Voice: ${voiceLang}` : 'Voice unavailable'}
        </span>
      </div>
      
      <div className="flex items-center gap-2 text-xs text-muted-foreground bg-accent/10 px-3 py-2 rounded-md">
        <AlertTriangle size={14} className="text-accent" />
        <span>Plan-first mode active. Confirm before dispatch.</span>
      </div>
    </form>
  );
};

export default CommandConsole;
