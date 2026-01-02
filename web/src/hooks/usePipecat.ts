import { useCallback, useRef, useState } from "react";

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

  // WebRTC connection refs
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const agentUrl = import.meta.env.VITE_AGENT_URL || "ws://localhost:8765";

  const connect = useCallback(async () => {
    setState("connecting");
    setError(null);

    try {
      // Create WebSocket connection for signaling
      const ws = new WebSocket(agentUrl);
      wsRef.current = ws;

      ws.onopen = async () => {
        console.log("WebSocket connected");

        // Create peer connection
        const pc = new RTCPeerConnection({
          iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
        });
        pcRef.current = pc;

        // Add audio track
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: true,
          video: false,
        });
        stream.getTracks().forEach((track) => pc.addTrack(track, stream));

        // Handle incoming audio
        pc.ontrack = (event) => {
          const audio = new Audio();
          audio.srcObject = event.streams[0];
          audio.play();
        };

        // Handle ICE candidates
        pc.onicecandidate = (event) => {
          if (event.candidate) {
            ws.send(
              JSON.stringify({
                type: "ice-candidate",
                candidate: event.candidate,
              })
            );
          }
        };

        // Create and send offer
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        ws.send(JSON.stringify({ type: "offer", sdp: offer.sdp }));
      };

      ws.onmessage = async (event) => {
        const data = JSON.parse(event.data);

        if (data.type === "answer" && pcRef.current) {
          await pcRef.current.setRemoteDescription({
            type: "answer",
            sdp: data.sdp,
          });
          setState("connected");
        } else if (data.type === "ice-candidate" && pcRef.current) {
          await pcRef.current.addIceCandidate(data.candidate);
        } else if (data.type === "transcript") {
          setTranscript((prev) => [
            ...prev,
            {
              role: data.role,
              content: data.content,
              timestamp: new Date(),
            },
          ]);
        }
      };

      ws.onerror = (event) => {
        console.error("WebSocket error:", event);
        setError("Connection failed");
        setState("error");
      };

      ws.onclose = () => {
        console.log("WebSocket closed");
        if (state === "connected") {
          setState("idle");
        }
      };
    } catch (err) {
      console.error("Connection error:", err);
      setError(err instanceof Error ? err.message : "Connection failed");
      setState("error");
    }
  }, [agentUrl, state]);

  const disconnect = useCallback(() => {
    if (pcRef.current) {
      pcRef.current.close();
      pcRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setState("idle");
  }, []);

  return {
    state,
    transcript,
    error,
    connect,
    disconnect,
  };
}
