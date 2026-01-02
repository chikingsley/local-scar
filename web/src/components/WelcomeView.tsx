interface WelcomeViewProps {
  onConnect: () => void;
}

export function WelcomeView({ onConnect }: WelcomeViewProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="text-6xl mb-8">🎙️</div>
      <p className="text-gray-400 mb-8 text-center max-w-md">
        Click to connect and start talking. The assistant will listen and respond
        via voice.
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
