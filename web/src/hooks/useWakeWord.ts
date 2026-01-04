import { useCallback, useEffect, useState } from "react";
import { usePorcupine } from "@picovoice/porcupine-react";
import { BuiltInKeyword } from "@picovoice/porcupine-web";
import { useSettings } from "../components/SettingsModal";

export type WakeWordState = "idle" | "loading" | "listening" | "error";

interface UseWakeWordOptions {
  keyword?: BuiltInKeyword;
  onWakeWord?: () => void;
}

export function useWakeWord(options: UseWakeWordOptions = {}) {
  const settings = useSettings();
  const { keyword = BuiltInKeyword.Jarvis, onWakeWord } = options;
  const accessKey = settings.porcupineAccessKey;

  const [state, setState] = useState<WakeWordState>("idle");

  const {
    keywordDetection,
    isLoaded,
    isListening,
    error,
    init,
    start,
    stop,
    release,
  } = usePorcupine();

  // Initialize Porcupine when access key is available
  const initialize = useCallback(async () => {
    if (!accessKey) {
      console.warn("No Porcupine access key provided");
      return;
    }

    setState("loading");

    try {
      await init(accessKey, [keyword], {
        publicPath: "/porcupine/",
        forceWrite: true,
      });
    } catch (err) {
      console.error("Failed to initialize Porcupine:", err);
      setState("error");
    }
  }, [accessKey, keyword, init]);

  // Start listening for wake word
  const startListening = useCallback(async () => {
    if (!isLoaded) {
      await initialize();
    }
    await start();
  }, [isLoaded, initialize, start]);

  // Stop listening
  const stopListening = useCallback(async () => {
    await stop();
  }, [stop]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      release();
    };
  }, [release]);

  // Update state based on Porcupine state
  useEffect(() => {
    if (error) {
      setState("error");
    } else if (isListening) {
      setState("listening");
    } else if (isLoaded) {
      setState("idle");
    }
  }, [isLoaded, isListening, error]);

  // Handle wake word detection
  useEffect(() => {
    if (keywordDetection) {
      console.log("Wake word detected:", keywordDetection.label);
      onWakeWord?.();
    }
  }, [keywordDetection, onWakeWord]);

  return {
    state,
    isAvailable: !!accessKey,
    isListening,
    error: error?.message || null,
    initialize,
    startListening,
    stopListening,
  };
}
