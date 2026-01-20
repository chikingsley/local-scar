/* eslint-disable react-refresh/only-export-components */
import { useEffect, useState } from "react";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface Settings {
  agentUrl: string;
  webhookUrl: string;
  porcupineAccessKey: string;
}

const STORAGE_KEY = "voice-agent-settings";

function loadSettings(): Settings {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch {
    // Ignore parse errors
  }
  return {
    agentUrl: import.meta.env.VITE_AGENT_URL || "http://localhost:8765",
    webhookUrl: import.meta.env.VITE_WEBHOOK_URL || "http://localhost:8889",
    porcupineAccessKey: import.meta.env.VITE_PORCUPINE_ACCESS_KEY || "",
  };
}

function saveSettings(settings: Settings) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [settings, setSettings] = useState<Settings>(loadSettings);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setSettings(loadSettings());
      setSaved(false);
    }
  }, [isOpen]);

  const handleSave = () => {
    saveSettings(settings);
    setSaved(true);
    setTimeout(() => {
      onClose();
      // Reload to apply new settings
      window.location.reload();
    }, 500);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-900 rounded-lg p-6 w-full max-w-md mx-4">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold">Settings</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
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
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="space-y-4">
          {/* Agent URL */}
          <div>
            <label className="block text-sm text-gray-400 mb-1">
              Agent URL
            </label>
            <input
              type="url"
              value={settings.agentUrl}
              onChange={(e) =>
                setSettings({ ...settings, agentUrl: e.target.value })
              }
              placeholder="http://localhost:8765"
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              WebRTC signaling server URL
            </p>
          </div>

          {/* Webhook URL */}
          <div>
            <label className="block text-sm text-gray-400 mb-1">
              Webhook URL
            </label>
            <input
              type="url"
              value={settings.webhookUrl}
              onChange={(e) =>
                setSettings({ ...settings, webhookUrl: e.target.value })
              }
              placeholder="http://localhost:8889"
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              Webhook API for announcements
            </p>
          </div>

          {/* Porcupine Access Key */}
          <div>
            <label className="block text-sm text-gray-400 mb-1">
              Picovoice Access Key
            </label>
            <input
              type="password"
              value={settings.porcupineAccessKey}
              onChange={(e) =>
                setSettings({ ...settings, porcupineAccessKey: e.target.value })
              }
              placeholder="Enter your access key"
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              For wake word detection.{" "}
              <a
                href="https://console.picovoice.ai/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-400 hover:underline"
              >
                Get one free
              </a>
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3 mt-6">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            {saved ? "Saved!" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}

// Hook to use settings throughout the app
export function useSettings(): Settings {
  return loadSettings();
}
