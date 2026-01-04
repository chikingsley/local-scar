import { useEffect } from "react";
import { useWakeWord } from "../hooks/useWakeWord";

interface WelcomeViewProps {
  onConnect: () => void;
}

export function WelcomeView({ onConnect }: WelcomeViewProps) {
  const { state, isAvailable, isListening, startListening, stopListening } =
    useWakeWord({
      onWakeWord: onConnect,
    });

  // Auto-start wake word listening if available
  useEffect(() => {
    if (isAvailable && state === "idle") {
      startListening();
    }
    return () => {
      if (isListening) {
        stopListening();
      }
    };
  }, [isAvailable, state, isListening, startListening, stopListening]);

  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="text-6xl mb-8">🎙️</div>

      {/* Wake word status */}
      {isAvailable && (
        <div className="mb-4 flex items-center gap-2 text-sm">
          {isListening ? (
            <>
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-gray-400">Say "Jarvis" to connect</span>
            </>
          ) : state === "loading" ? (
            <>
              <span className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse" />
              <span className="text-gray-400">Loading wake word...</span>
            </>
          ) : state === "error" ? (
            <>
              <span className="w-2 h-2 bg-red-500 rounded-full" />
              <span className="text-gray-400">Wake word unavailable</span>
            </>
          ) : null}
        </div>
      )}

      <p className="text-gray-400 mb-8 text-center max-w-md">
        {isAvailable
          ? 'Say "Jarvis" or click below to start talking.'
          : "Click to connect and start talking. The assistant will listen and respond via voice."}
      </p>

      <button
        onClick={onConnect}
        className="px-8 py-4 bg-blue-600 hover:bg-blue-700 rounded-full text-lg font-medium transition-colors"
      >
        Connect
      </button>
    </div>
  );
}
