import { ConnectionState, TranscriptEntry } from "../hooks/usePipecat";
import { ChatTranscript } from "./ChatTranscript";

interface SessionViewProps {
  state: ConnectionState;
  transcript: TranscriptEntry[];
  isMuted: boolean;
  activeTool: string | null;
  onDisconnect: () => void;
  onToggleMute: () => void;
}

export function SessionView({
  state,
  transcript,
  isMuted,
  activeTool,
  onDisconnect,
  onToggleMute,
}: SessionViewProps) {
  return (
    <div className="flex flex-col h-[70vh]">
      {/* Status bar */}
      <div className="flex items-center justify-between mb-4 px-4 py-2 bg-gray-900 rounded-lg">
        <div className="flex items-center gap-4">
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

          {/* Tool status indicator */}
          {activeTool && (
            <div className="flex items-center gap-2 px-2 py-1 bg-purple-900/50 rounded text-xs">
              <span className="w-2 h-2 bg-purple-500 rounded-full animate-pulse" />
              <span className="text-purple-300">{activeTool}</span>
            </div>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={onToggleMute}
            className={`px-4 py-1 text-sm rounded-full transition-colors ${
              isMuted
                ? "bg-yellow-600 hover:bg-yellow-700"
                : "bg-gray-700 hover:bg-gray-600"
            }`}
          >
            {isMuted ? "Unmute" : "Mute"}
          </button>
          <button
            onClick={onDisconnect}
            className="px-4 py-1 text-sm bg-red-600 hover:bg-red-700 rounded-full transition-colors"
          >
            Disconnect
          </button>
        </div>
      </div>

      {/* Transcript */}
      <div className="flex-1 overflow-hidden">
        <ChatTranscript entries={transcript} />
      </div>

      {/* Listening indicator */}
      {state === "connected" && (
        <div className="mt-4 flex items-center justify-center gap-2 text-gray-400">
          {isMuted ? (
            <span className="text-sm text-yellow-500">Microphone muted</span>
          ) : (
            <>
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
            </>
          )}
        </div>
      )}
    </div>
  );
}
