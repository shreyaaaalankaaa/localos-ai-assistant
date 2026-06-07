import { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Stars } from "@react-three/drei";
import * as THREE from "three";
import { Mic, Send } from "lucide-react";
import "./App.css";

type Message = {
  role: "user" | "assistant";
  content: string;
  model?: string;
};

type Mode = "fast" | "normal" | "reasoning" | "coding";

function HologramCore({
  thinking,
  listening,
  awakened,
}: {
  thinking: boolean;
  listening: boolean;
  awakened: boolean;
}) {
  const globeRef = useRef<THREE.Mesh>(null);
  const ringOneRef = useRef<THREE.Mesh>(null);
  const ringTwoRef = useRef<THREE.Mesh>(null);
  const ringThreeRef = useRef<THREE.Mesh>(null);
  const pointsRef = useRef<THREE.Points>(null);

  const particlePositions = useMemo(() => {
    const count = 560;
    const positions = new Float32Array(count * 3);

    for (let i = 0; i < count; i++) {
      const radius = 1.36 + Math.random() * 0.08;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);

      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = radius * Math.cos(phi);
    }

    return positions;
  }, []);

  useFrame((state) => {
    const elapsed = state.clock.elapsedTime;

    if (globeRef.current) {
      globeRef.current.rotation.y = elapsed * 0.18;
      globeRef.current.rotation.x = Math.sin(elapsed * 0.3) * 0.08;
    }

    if (ringOneRef.current) {
      ringOneRef.current.rotation.z = elapsed * 0.25;
      ringOneRef.current.rotation.x = Math.PI / 2.7;
    }

    if (ringTwoRef.current) {
      ringTwoRef.current.rotation.z = -elapsed * 0.32;
      ringTwoRef.current.rotation.y = Math.PI / 3.4;
    }

    if (ringThreeRef.current) {
      ringThreeRef.current.rotation.z = elapsed * 0.42;
      ringThreeRef.current.rotation.x = Math.PI / 2.2;
    }

    if (pointsRef.current) {
      pointsRef.current.rotation.y = elapsed * 0.12;
    }
  });

  const glowColor = listening
    ? "#ffffff"
    : thinking
      ? "#eeeeee"
      : awakened
        ? "#cfcfcf"
        : "#8f9aa3";

  return (
    <group>
      <ambientLight intensity={0.55} />
      <pointLight position={[4, 4, 4]} intensity={5} color={glowColor} />
      <pointLight position={[-4, -2, 3]} intensity={2.4} color="#9ca3af" />

      <mesh ref={globeRef}>
        <sphereGeometry args={[1.22, 96, 96]} />
        <meshStandardMaterial
          color="#c9c9c9"
          emissive={glowColor}
          emissiveIntensity={thinking || listening || awakened ? 0.38 : 0.22}
          roughness={0.18}
          metalness={0.82}
          transparent
          opacity={0.9}
        />
      </mesh>

      <mesh>
        <sphereGeometry args={[1.235, 64, 64]} />
        <meshBasicMaterial color="#f5f5f5" wireframe transparent opacity={0.14} />
      </mesh>

      <points ref={pointsRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[particlePositions, 3]} />
        </bufferGeometry>
        <pointsMaterial
          size={0.012}
          color="#ffffff"
          transparent
          opacity={0.82}
          sizeAttenuation
        />
      </points>

      <mesh ref={ringOneRef}>
        <torusGeometry args={[1.55, 0.006, 16, 180]} />
        <meshBasicMaterial color="#ffffff" transparent opacity={0.42} />
      </mesh>

      <mesh ref={ringTwoRef}>
        <torusGeometry args={[1.82, 0.004, 16, 180]} />
        <meshBasicMaterial color="#c0c0c0" transparent opacity={0.32} />
      </mesh>

      <mesh ref={ringThreeRef}>
        <torusGeometry args={[2.08, 0.003, 16, 180]} />
        <meshBasicMaterial color="#9ca3af" transparent opacity={0.24} />
      </mesh>
    </group>
  );
}

function CoreScene({
  thinking,
  listening,
  awakened,
}: {
  thinking: boolean;
  listening: boolean;
  awakened: boolean;
}) {
  return (
    <Canvas camera={{ position: [0, 0, 5.3], fov: 48 }}>
      <color attach="background" args={["#000000"]} />
      <fog attach="fog" args={["#000000", 5, 10]} />
      <Stars radius={90} depth={44} count={2200} factor={4} saturation={0} fade speed={1} />
      <HologramCore thinking={thinking} listening={listening} awakened={awakened} />
      <OrbitControls
        enableZoom={false}
        enablePan={false}
        autoRotate
        autoRotateSpeed={0.32}
        minPolarAngle={Math.PI / 2.6}
        maxPolarAngle={Math.PI / 1.6}
      />
    </Canvas>
  );
}

function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "System initializing...",
      model: "startup",
    },
  ]);

  const [input, setInput] = useState("");
  const [mode] = useState<Mode>("fast");
  const [speak, setSpeak] = useState(false);
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const [feedOpen, setFeedOpen] = useState(false);
  const [awakened, setAwakened] = useState(false);

  const recognitionRef = useRef<any>(null);
  const finalTranscriptRef = useRef("");
  const startedAtRef = useRef(0);
  const shouldListenRef = useRef(false);
  const manuallyStoppedRef = useRef(false);
  const silenceTimerRef = useRef<number | null>(null);
  const hardStopTimerRef = useRef<number | null>(null);

  const clearListeningTimers = () => {
    if (silenceTimerRef.current) {
      window.clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }

    if (hardStopTimerRef.current) {
      window.clearTimeout(hardStopTimerRef.current);
      hardStopTimerRef.current = null;
    }
  };

  const stopTalking = async () => {
    try {
      await axios.post("http://127.0.0.1:8000/stop-speech");
    } catch {
      // backend may be down
    }

    setLoading(false);
    setListening(false);
    setInput("");
    setFeedOpen(true);

    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: "Stopped.",
        model: "speech-control",
      },
    ]);
  };

  useEffect(() => {
    const loadStartup = async () => {
      try {
        const response = await axios.get("http://127.0.0.1:8000/startup");

        setMessages([
          {
            role: "assistant",
            content: response.data.startup_text || "System online. Local core ready.",
            model: "startup",
          },
        ]);
      } catch {
        setMessages([
          {
            role: "assistant",
            content: "Frontend is open, but the backend is not connected yet.",
            model: "startup-error",
          },
        ]);
      }
    };

    loadStartup();
  }, []);

  const sendMessage = async (customMessage?: string) => {
    const messageToSend = customMessage || input;
    const normalized = messageToSend.trim().toLowerCase();

    if (
      normalized === "stop" ||
      normalized === "stop talking" ||
      normalized === "stop speaking" ||
      normalized === "be quiet" ||
      normalized === "silence"
    ) {
      await stopTalking();
      return;
    }

    if (!messageToSend.trim() || loading || messageToSend === "Listening...") return;

    setFeedOpen(true);
    setAwakened(true);

    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        content: messageToSend,
      },
    ]);

    setInput("");
    setLoading(true);

    try {
      const response = await axios.post("http://127.0.0.1:8000/chat", {
        message: messageToSend,
        mode,
        speak,
      });

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.data.reply,
          model: response.data.model_used,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Backend link failed. Start FastAPI on port 8000 and make sure the local model is running.",
          model: "system-error",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const finishListeningAndSend = () => {
    const finalText = finalTranscriptRef.current.trim();

    shouldListenRef.current = false;
    manuallyStoppedRef.current = true;
    clearListeningTimers();

    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // ignore
      }
    }

    recognitionRef.current = null;
    setListening(false);

    if (!finalText) {
      setInput("");
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "I didn’t catch that. Tap the mic and speak right away.",
          model: "voice",
        },
      ]);
      return;
    }

    setInput("");
    sendMessage(finalText);
  };

  const startRecognitionInstance = () => {
    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert(
        "Speech recognition is not available in this app window. Use typing for now, or run in Chrome/Edge for mic support."
      );
      return;
    }

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;

    recognition.lang = "en-US";
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setListening(true);
      setInput(finalTranscriptRef.current || "Listening...");
    };

    recognition.onresult = async (event: any) => {
      let interimTranscript = "";
      let confirmedTranscript = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcriptChunk = event.results[i][0].transcript;

        if (event.results[i].isFinal) {
          confirmedTranscript += transcriptChunk;
        } else {
          interimTranscript += transcriptChunk;
        }
      }

      if (confirmedTranscript.trim()) {
        finalTranscriptRef.current = `${finalTranscriptRef.current} ${confirmedTranscript}`.trim();
      }

      const visibleText = `${finalTranscriptRef.current} ${interimTranscript}`.trim();

      if (visibleText) {
        const lower = visibleText.toLowerCase();

        if (
          lower.includes("stop talking") ||
          lower.includes("stop speaking") ||
          lower === "stop" ||
          lower.includes("be quiet") ||
          lower.includes("silence")
        ) {
          await stopTalking();
          finishListeningAndSend();
          return;
        }

        setInput(visibleText);
      }

      if (silenceTimerRef.current) {
        window.clearTimeout(silenceTimerRef.current);
      }

      silenceTimerRef.current = window.setTimeout(() => {
        finishListeningAndSend();
      }, 2200);
    };

    recognition.onerror = (event: any) => {
      const errorName = event?.error || "unknown";

      if (errorName === "not-allowed" || errorName === "service-not-allowed") {
        shouldListenRef.current = false;
        setListening(false);
        setInput("");

        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "Microphone permission is blocked. Allow mic access for the app, then try again.",
            model: "voice",
          },
        ]);
        return;
      }

      if (errorName === "no-speech") {
        // Do not fail instantly. Electron often throws no-speech too early.
        return;
      }

      console.log("Speech recognition error:", errorName);
    };

    recognition.onend = () => {
      const elapsed = Date.now() - startedAtRef.current;
      const hasText = finalTranscriptRef.current.trim().length > 0;

      if (manuallyStoppedRef.current) {
        setListening(false);
        return;
      }

      if (shouldListenRef.current && elapsed < 12000 && !hasText) {
        // Auto-restart because Electron ended too early.
        setTimeout(() => {
          if (shouldListenRef.current && !recognitionRef.current) {
            startRecognitionInstance();
          }
        }, 250);

        recognitionRef.current = null;
        return;
      }

      if (shouldListenRef.current && hasText) {
        finishListeningAndSend();
        return;
      }

      setListening(false);
      recognitionRef.current = null;
    };

    try {
      recognition.start();
    } catch {
      recognitionRef.current = null;

      if (shouldListenRef.current) {
        setTimeout(() => {
          startRecognitionInstance();
        }, 300);
      }
    }
  };

  const startListening = () => {
    if (listening) {
      finishListeningAndSend();
      return;
    }

    finalTranscriptRef.current = "";
    startedAtRef.current = Date.now();
    shouldListenRef.current = true;
    manuallyStoppedRef.current = false;

    clearListeningTimers();

    setListening(true);
    setAwakened(true);
    setFeedOpen(true);
    setInput("Listening...");

    hardStopTimerRef.current = window.setTimeout(() => {
      finishListeningAndSend();
    }, 12000);

    startRecognitionInstance();
  };

  return (
    <div className="black-core">
      <div className="scene">
        <CoreScene thinking={loading} listening={listening} awakened={awakened} />
      </div>

      <div className="black-vignette" />
      <div className="minimal-grid" />

      {loading && (
        <div className="advanced-dispersion">
          <div className="dispersion-ring ring-one" />
          <div className="dispersion-ring ring-two" />
          <div className="dispersion-ring ring-three" />
          <div className="dispersion-scan" />

          {Array.from({ length: 96 }).map((_, index) => {
            const angle = index * 0.392;
            const radius = 80 + (index % 9) * 18;

            return (
              <span
                key={index}
                className={index % 3 === 0 ? "spark shard" : "spark"}
                style={
                  {
                    "--x": `${Math.cos(angle) * radius}px`,
                    "--y": `${Math.sin(angle) * radius}px`,
                    "--delay": `${index * 0.018}s`,
                    "--size": `${1.8 + (index % 5) * 0.7}px`,
                    "--blur": `${index % 4}px`,
                  } as React.CSSProperties
                }
              />
            );
          })}
        </div>
      )}

      <header className="minimal-top">
        <div className="status-corner">
          <span>{listening ? "LISTENING" : loading ? "PROCESSING" : awakened ? "AWAKE" : "STANDBY"}</span>
        </div>

        <button
          className={`voice-state ${speak ? "on" : ""}`}
          onClick={() => setSpeak((prev) => !prev)}
        >
          {speak ? "VOICE ON" : "VOICE OFF"}
        </button>
      </header>

      {feedOpen && (
        <section className="mini-feed">
          <div className="mini-feed-head">
            <span>FEED</span>
            <button onClick={() => setFeedOpen(false)}>Hide</button>
          </div>

          <div className="mini-feed-body">
            {messages.map((message, index) => (
              <div key={`${message.role}-${index}`} className={`mini-message ${message.role}`}>
                <strong>{message.role === "assistant" ? "SYSTEM" : "YOU"}</strong>
                <p>{message.content}</p>
              </div>
            ))}

            {loading && <div className="mini-processing">Processing...</div>}
          </div>
        </section>
      )}

      <footer className="minimal-dock">
        <button className={`mic ${listening ? "active" : ""}`} onClick={startListening}>
          <Mic size={22} />
        </button>

        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onFocus={() => setFeedOpen(true)}
          onKeyDown={(event) => {
            if (event.key === "Enter") sendMessage();
          }}
          placeholder={listening ? "Listening..." : "Ask anything..."}
        />

        <button className="send" onClick={() => sendMessage()}>
          <Send size={22} />
        </button>
      </footer>
    </div>
  );
}

export default App;