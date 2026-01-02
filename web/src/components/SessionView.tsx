import { ConnectionState, TranscriptEntry } from "../hooks/usePipecat";
import { ChatTranscript } from "./ChatTranscript";

interface SessionViewProps {
  state: ConnectionState;
  transcript: TranscriptEntry[];
  onDisconnect: () => void;
}

export function SessionView({ state, transcript, onDisconnect }: SessionViewProps) {
  return (
    <div className="flex flex-col h-[70vh]">
      {/* Status bar */}
      <div className="flex items-center justify-between mb-4 px-4 py-2 bg-gray-900 rounded-lg">
        <div className="flex items-center gap-2">
          <div
            className={`w-3 h-3 rounded-full ${
              state === "connected"
                ? "bg-green-500"
                : state === "connecting"
                ? "bg-yellow-500 animate-pulse"
                : "bg-red-500"
            }`}
          />
          <span className="text-sm text-gray-400">
            {state === "connected"
              ? "Connected"
              : state === "connecting"
              ? "Connecting..."
              : "Disconnected"}
          </span>
        </div>
        <button
          onClick={onDisconnect}
          className="px-4 py-1 text-sm bg-red-600 hover:bg-red-700 rounded-full transition-colors"
        >
          Disconnect
        </button>
      </div>

      {/* Transcript */}
      <div className="flex-1 overflow-hidden">
        <ChatTranscript entries={transcript} />
      </div>

      {/* Listening indicator */}
      {state === "connected" && (
        <div className="mt-4 flex items-center justify-center gap-2 text-gray-400">
          <div className="flex gap-1">
            <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" />
            <span
              className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"
              style={{ animationDelay: "0.1s" }}
            />
            <span
              className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"
              style={{ animationDelay: "0.2s" }}
            />
          </div>
          <span className="text-sm">Listening...</span>
        </div>
      )}
    </div>
  );
}
