import { useCallback, useRef, useState, useEffect } from "react";
import { PipecatClient } from "@pipecat-ai/client-js";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";
import { useSettings } from "../components/SettingsModal";

export type ConnectionState = "idle" | "connecting" | "connected" | "error";

export interface TranscriptEntry {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export function usePipecat() {
  const [state, setState] = useState<ConnectionState>("idle");
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isMuted, setIsMuted] = useState(false);
  const [activeTool, setActiveTool] = useState<string | null>(null);

  const clientRef = useRef<PipecatClient | null>(null);
  const settings = useSettings();

  const agentUrl = settings.agentUrl || "http://localhost:8765";

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (clientRef.current) {
        clientRef.current.disconnect();
        clientRef.current = null;
      }
    };
  }, []);

  const connect = useCallback(async () => {
    if (clientRef.current) {
      console.warn("Already connected or connecting");
      return;
    }

    setState("connecting");
    setError(null);
    setTranscript([]);

    try {
      // Create transport with SmallWebRTC and ICE servers for NAT traversal
      const transport = new SmallWebRTCTransport({
        iceServers: [
          { urls: "stun:stun.l.google.com:19302" },
          { urls: "stun:stun1.l.google.com:19302" },
        ],
        waitForICEGathering: true,
      });

      // Create Pipecat client
      const client = new PipecatClient({
        transport,
        enableMic: true,
        enableCam: false,
        callbacks: {
          // Connection events
          onConnected: () => {
            console.log("Pipecat connected");
            setState("connected");
          },
          onDisconnected: () => {
            console.log("Pipecat disconnected");
            setState("idle");
            clientRef.current = null;
          },
          onError: (err) => {
            console.error("Pipecat error:", err);
            setError("Connection error");
            setState("error");
          },

          // Transcript events
          onUserTranscript: (data) => {
            if (data.text && data.final) {
              setTranscript((prev) => [
                ...prev,
                {
                  role: "user",
                  content: data.text,
                  timestamp: new Date(),
                },
              ]);
            }
          },
          onBotTranscript: (data) => {
            if (data.text) {
              setTranscript((prev) => {
                // Update last assistant entry if it exists, otherwise add new
                const lastEntry = prev[prev.length - 1];
                if (lastEntry?.role === "assistant") {
                  // Streaming update - replace last entry
                  return [
                    ...prev.slice(0, -1),
                    {
                      ...lastEntry,
                      content: data.text,
                    },
                  ];
                }
                // New entry
                return [
                  ...prev,
                  {
                    role: "assistant",
                    content: data.text,
                    timestamp: new Date(),
                  },
                ];
              });
            }
          },

          // Tool call events
          onLLMFunctionCall: (data) => {
            console.log("Tool call:", data.function_name);
            setActiveTool(data.function_name);
            // Clear after a short delay since there's no result callback
            setTimeout(() => setActiveTool(null), 2000);
          },
        },
      });

      clientRef.current = client;

      // Connect to the agent
      await client.connect({
        webrtcUrl: `${agentUrl}/offer`,
      });
    } catch (err) {
      console.error("Connection error:", err);
      setError(err instanceof Error ? err.message : "Connection failed");
      setState("error");
      clientRef.current = null;
    }
  }, [agentUrl]);

  const disconnect = useCallback(async () => {
    if (clientRef.current) {
      await clientRef.current.disconnect();
      clientRef.current = null;
    }
    setState("idle");
  }, []);

  const toggleMute = useCallback(() => {
    if (clientRef.current) {
      const newMuted = !isMuted;
      clientRef.current.enableMic(!newMuted);
      setIsMuted(newMuted);
    }
  }, [isMuted]);

  return {
    state,
    transcript,
    error,
    isMuted,
    activeTool,
    connect,
    disconnect,
    toggleMute,
  };
}
