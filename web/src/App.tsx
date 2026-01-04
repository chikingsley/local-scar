import { useState } from "react";
import { SessionView } from "./components/SessionView";
import { SettingsModal } from "./components/SettingsModal";
import { WelcomeView } from "./components/WelcomeView";
import { usePipecat } from "./hooks/usePipecat";

function App() {
  const {
    state,
    connect,
    disconnect,
    transcript,
    isMuted,
    activeTool,
    toggleMute,
  } = usePipecat();
  const [showSettings, setShowSettings] = useState(false);

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <div className="container mx-auto px-4 py-8 max-w-2xl">
        <header className="text-center mb-8 relative">
          <h1 className="text-3xl font-bold">Voice Agent</h1>
          <p className="text-gray-400 mt-2">
            Local voice assistant with Pipecat
          </p>

          {/* Settings button */}
          <button
            onClick={() => setShowSettings(true)}
            className="absolute right-0 top-0 p-2 text-gray-400 hover:text-white transition-colors"
            title="Settings"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
          </button>
        </header>

        {state === "idle" ? (
          <WelcomeView onConnect={connect} />
        ) : (
          <SessionView
            state={state}
            transcript={transcript}
            isMuted={isMuted}
            activeTool={activeTool}
            onDisconnect={disconnect}
            onToggleMute={toggleMute}
          />
        )}
      </div>

      {/* Settings modal */}
      <SettingsModal
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
      />
    </div>
  );
}

export default App;
