import { useState } from "react";
import { SessionView } from "./components/SessionView";
import { WelcomeView } from "./components/WelcomeView";
import { usePipecat } from "./hooks/usePipecat";

function App() {
  const { state, connect, disconnect, transcript } = usePipecat();

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <div className="container mx-auto px-4 py-8 max-w-2xl">
        <header className="text-center mb-8">
          <h1 className="text-3xl font-bold">Voice Agent</h1>
          <p className="text-gray-400 mt-2">Local voice assistant with Pipecat</p>
        </header>

        {state === "idle" ? (
          <WelcomeView onConnect={connect} />
        ) : (
          <SessionView
            state={state}
            transcript={transcript}
            onDisconnect={disconnect}
          />
        )}
      </div>
    </div>
  );
}

export default App;
