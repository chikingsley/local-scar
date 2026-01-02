import { TranscriptEntry } from "../hooks/usePipecat";

interface ChatTranscriptProps {
  entries: TranscriptEntry[];
}

export function ChatTranscript({ entries }: ChatTranscriptProps) {
  if (entries.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500">
        <p>Start speaking to see the conversation...</p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto space-y-4 px-2">
      {entries.map((entry, index) => (
        <div
          key={index}
          className={`flex ${
            entry.role === "user" ? "justify-end" : "justify-start"
          }`}
        >
          <div
            className={`max-w-[80%] px-4 py-2 rounded-2xl ${
              entry.role === "user"
                ? "bg-blue-600 text-white"
                : "bg-gray-800 text-gray-100"
            }`}
          >
            <p>{entry.content}</p>
            <span className="text-xs opacity-50 mt-1 block">
              {entry.timestamp.toLocaleTimeString()}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
