import React, { useState, useEffect, useRef } from "react";
import { sessionAPI, audioAPI } from "./api";
import "./App.css";

function App() {
  const [sessions, setSessions] = useState([]);
  const [mode, setMode] = useState("online");
  const [isRecording, isRecordingRecording] = useState(false);
  const [currentSession, setCurrentSession] = useState(null);
  const [microphones, setMicrophones] = useState([]);
  const [selectedMicrophone, setSelectedMicrophone] = useState("");
  const [pendingUploads, setPendingUploads] = useState([]);
  const [isSyncing, setIsSyncing] = useState(false);
  const [selectedTranscript, setSelectedTranscript] = useState(null);
  const [liveTranscript, setLiveTranscript] = useState("");
  const [transcriptMode, setTranscriptMode] = useState("batch");
  const audioContextRef = useRef(null);
  const processorRef = useRef(null);
  const pcmBufferRef = useRef([]);
  const streamRef = useRef(null);
  const sseRef = useRef(null);
  const chunkIntervalRef = useRef(null);
  const audioFormatRef = useRef({ sampleRate: 16000, channels: 1, bitDepth: 16 });

  useEffect(() => {
    loadConfig();
    loadSessions();
    getMicrophones();
    syncOfflineRecordings();
  }, []);

  const loadConfig = async () => {
    try {
      const response = await fetch("http://localhost:8000/config");
      const config = await response.json();
      setTranscriptMode(config.transcript_mode);
      console.log(`%c[CONFIG] Loaded: transcript_mode = ${config.transcript_mode}`, "color: green; font-weight: bold;");
    } catch (error) {
      console.error("Failed to load config:", error);
    }
  };

  const loadSessions = async () => {
    try {
      const data = await sessionAPI.getSessions();
      setSessions(data);
    } catch (error) {
      console.error("Failed to load sessions:", error);
    }
  };

  const syncOfflineRecordings = async () => {
    console.log("Checking for pending offline recordings...");
    const pending = [];

    // Find all offline recordings in localStorage
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith("audio_")) {
        const sessionId = key.replace("audio_", "");
        pending.push({ sessionId, key });
      }
    }

    console.log(`Found ${pending.length} pending offline recordings`);
    setPendingUploads(pending);
  };

  const uploadPendingRecordings = async () => {
    if (pendingUploads.length === 0) {
      alert("No pending recordings to sync");
      return;
    }

    setIsSyncing(true);
    let successCount = 0;
    const failedSessions = [];

    for (const pending of pendingUploads) {
      try {
        console.log(`Uploading offline recording for session ${pending.sessionId}...`);
        const storedData = localStorage.getItem(pending.key);
        const audioData = JSON.parse(storedData);

        // Convert array back to ArrayBuffer
        const arrayBuffer = new ArrayBuffer(audioData.data.length);
        const view = new Uint8Array(arrayBuffer);
        audioData.data.forEach((byte, i) => {
          view[i] = byte;
        });

        const audioBlob = new Blob([arrayBuffer], { type: "application/octet-stream" });

        const formData = new FormData();
        formData.append("file", audioBlob, "audio.pcm");

        const params = new URLSearchParams({
          is_final: "true",
          ...(audioData.format === "pcm" && {
            sample_rate: audioData.sampleRate,
            channels: audioData.channels,
            bit_depth: audioData.bitDepth,
          }),
        });

        const response = await fetch(
          `http://localhost:8000/api/v1/sessions/${pending.sessionId}/audio?${params}`,
          {
            method: "POST",
            body: formData,
          }
        );

        if (!response.ok) {
          throw new Error(`Upload failed: ${response.status}`);
        }

        console.log(`Successfully uploaded recording for session ${pending.sessionId}`);

        // Remove from localStorage after successful upload
        localStorage.removeItem(pending.key);
        successCount++;
      } catch (error) {
        console.error(
          `Failed to upload recording for session ${pending.sessionId}:`,
          error
        );
        failedSessions.push(pending.sessionId);
      }
    }

    setIsSyncing(false);

    // Refresh pending uploads list
    syncOfflineRecordings();
    loadSessions();

    // Show result message
    if (successCount === pendingUploads.length) {
      alert(`✓ Successfully synced ${successCount} recording(s)`);
    } else {
      alert(
        `Synced ${successCount}/${pendingUploads.length} recordings.\nFailed: ${failedSessions.join(
          ", "
        )}`
      );
    }
  };

  const getMicrophones = async () => {
    try {
      // Request microphone permission first to get device labels
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((track) => track.stop());

      // Now enumerate devices with permission granted
      const devices = await navigator.mediaDevices.enumerateDevices();
      const audioInputs = devices.filter((device) => device.kind === "audioinput");
      setMicrophones(audioInputs);
      if (audioInputs.length > 0) {
        setSelectedMicrophone(audioInputs[0].deviceId);
      }
    } catch (error) {
      console.error("Failed to get microphones:", error);
    }
  };

  const startSession = async () => {
    try {
      const session = await sessionAPI.createSession(mode);
      setCurrentSession(session);
      setSessions([session, ...sessions]);
      startRecording(session);
    } catch (error) {
      console.error("Failed to create session:", error);
      alert("Failed to create session");
    }
  };

  const startRecording = async (session) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { deviceId: selectedMicrophone ? { exact: selectedMicrophone } : undefined },
      });

      streamRef.current = stream;

      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      audioContextRef.current = audioContext;

      const sampleRate = audioContext.sampleRate;
      audioFormatRef.current = { sampleRate, channels: 1, bitDepth: 16 };

      const source = audioContext.createMediaStreamSource(stream);
      const bufferSize = 4096;
      const processor = audioContext.createScriptProcessor(bufferSize, 1, 1);
      processorRef.current = processor;

      pcmBufferRef.current = [];
      let chunkBuffer = [];

      processor.onaudioprocess = (event) => {
        const inputData = event.inputBuffer.getChannelData(0);
        const pcm = new Int16Array(inputData.length);

        for (let i = 0; i < inputData.length; i++) {
          pcm[i] = Math.max(-1, Math.min(1, inputData[i])) < 0
            ? inputData[i] * 0x8000
            : inputData[i] * 0x7FFF;
        }

        pcmBufferRef.current.push(pcm);
        chunkBuffer.push(pcm);
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      console.log(`%c[AUDIO] Recording started with Web Audio API (${sampleRate}Hz), session: ${session.id}`, "color: green; font-weight: bold;");
      isRecordingRecording(true);

      if (transcriptMode === "stream" && mode === "online") {
        console.log(`%c[RECORD] Starting live transcript streaming`, "color: green; font-weight: bold;");
        streamTranscript(session.id, true);

        chunkIntervalRef.current = setInterval(async () => {
          if (chunkBuffer.length > 0) {
            const pcmChunk = new Int16Array(chunkBuffer.reduce((a, b) => a + b.length, 0));
            let offset = 0;
            for (const chunk of chunkBuffer) {
              pcmChunk.set(chunk, offset);
              offset += chunk.length;
            }
            chunkBuffer = [];

            try {
              const chunkBlob = new Blob([pcmChunk.buffer], { type: "application/octet-stream" });
              await sendAudioChunk(session.id, chunkBlob, false);
            } catch (error) {
              console.error("[RECORD] Failed to send chunk:", error);
            }
          }
        }, 5000);
      }
    } catch (error) {
      console.error("Failed to start recording:", error);
      alert("Failed to access microphone");
    }
  };

  const sendAudioChunk = async (sessionId, chunkBlob, isFinal) => {
    const formData = new FormData();
    formData.append("file", chunkBlob, "audio.pcm");

    const params = new URLSearchParams({
      is_final: isFinal,
      sample_rate: audioFormatRef.current.sampleRate,
      channels: audioFormatRef.current.channels,
      bit_depth: audioFormatRef.current.bitDepth,
    });

    const url = `http://localhost:8000/api/v1/sessions/${sessionId}/audio?${params}`;
    const response = await fetch(url, { method: "POST", body: formData });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.status}`);
    }

    const secs = (chunkBlob.size / 2 / audioFormatRef.current.sampleRate).toFixed(1);
    console.log(`%c[RECORD] Sent ${chunkBlob.size} bytes (~${secs}s audio)`, "color: blue;");
  };

  const stopRecording = async () => {
    console.log("Stop recording requested");

    if (chunkIntervalRef.current) {
      clearInterval(chunkIntervalRef.current);
      chunkIntervalRef.current = null;
    }

    if (processorRef.current) {
      processorRef.current.disconnect();
    }

    if (audioContextRef.current) {
      await audioContextRef.current.close();
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => {
        track.stop();
        console.log("Audio track stopped");
      });
    }

    isRecordingRecording(false);

    if (pcmBufferRef.current.length > 0) {
      const totalPCM = new Int16Array(pcmBufferRef.current.reduce((a, b) => a + b.length, 0));
      let offset = 0;
      for (const chunk of pcmBufferRef.current) {
        totalPCM.set(chunk, offset);
        offset += chunk.length;
      }

      const audioBlob = new Blob([totalPCM.buffer], { type: "audio/pcm" });
      console.log(`%c[RECORD] Recording stopped. Total PCM: ${audioBlob.size} bytes`, "color: green; font-weight: bold;");
      await sendFinalAudio(audioBlob);
    } else {
      console.error("No audio data recorded");
      alert("No audio was recorded. Please try again.");
    }

    pcmBufferRef.current = [];
  };

  const sendFinalAudio = async (pcmBlob) => {
    const currentSession = await sessionAPI.getSessions().then(sessions =>
      sessions.find(s => s.status === "active")
    );

    if (!currentSession) {
      alert("Session not found");
      return;
    }

    try {
      if (mode === "online") {
        await sendAudioChunk(currentSession.id, pcmBlob, true);
        await sessionAPI.closeSession(currentSession.id);
        console.log("Session closed successfully");
      } else {
        await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => {
            try {
              const audioData = reader.result;
              localStorage.setItem(`audio_${currentSession.id}`, JSON.stringify({
                data: Array.from(new Uint8Array(audioData)),
                format: "pcm",
                sampleRate: audioFormatRef.current.sampleRate,
                channels: audioFormatRef.current.channels,
                bitDepth: audioFormatRef.current.bitDepth,
                timestamp: new Date().toISOString(),
                client_id: currentSession.client_id,
                session_mode: currentSession.mode
              }));
              console.log("Audio stored locally");
              resolve();
            } catch (e) {
              reject(e);
            }
          };
          reader.onerror = () => reject(reader.error);
          reader.readAsArrayBuffer(pcmBlob);
        });
      }
    } catch (error) {
      console.error("Failed to send audio:", error);
      alert("Failed to process audio: " + error.message);
    } finally {
      setCurrentSession(null);
      loadSessions();
    }
  };

  const handleAudioData = async (audioBlob, mimeType, session) => {
    if (!session) {
      console.error("No session provided");
      return;
    }

    try {
      if (mode === "online") {
        console.log(`Uploading final audio to session ${session.id}...`);
        const ext = mimeType.includes("webm") ? "webm" : mimeType.includes("mp4") ? "m4a" : "wav";
        // In stream mode, mark this as final chunk
        const url = transcriptMode === "stream"
          ? `http://localhost:8000/api/v1/sessions/${session.id}/audio?is_final=true`
          : `http://localhost:8000/api/v1/sessions/${session.id}/audio`;

        const formData = new FormData();
        formData.append("file", audioBlob, `audio.${ext}`);

        await fetch(url, {
          method: "POST",
          body: formData,
        });
        console.log("Audio uploaded successfully");
      } else {
        // Offline mode: store in localStorage
        console.log(`Storing audio locally for session ${session.id}...`);
        await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => {
            try {
              const audioData = reader.result;
              localStorage.setItem(`audio_${session.id}`, JSON.stringify({
                data: Array.from(new Uint8Array(audioData)),
                mimeType: mimeType,
                timestamp: new Date().toISOString(),
                client_id: session.client_id,
                session_mode: session.mode
              }));
              console.log("Audio stored locally");
              resolve();
            } catch (e) {
              reject(e);
            }
          };
          reader.onerror = () => reject(reader.error);
          reader.readAsArrayBuffer(audioBlob);
        });
      }

      // Close session after recording
      console.log(`Closing session ${session.id}...`);
      await sessionAPI.closeSession(session.id);
      console.log("Session closed successfully");
    } catch (error) {
      console.error("Failed to handle audio:", error);
      alert("Failed to process audio: " + error.message);
    } finally {
      // Always clear the current session and reload, regardless of success or error
      console.log("Clearing current session and reloading sessions list");
      setCurrentSession(null);
      isRecordingRecording(false);
      loadSessions();
    }
  };

  const viewTranscript = async (sessionId) => {
    console.log(`Fetching transcript for session ${sessionId}...`);
    try {
      const response = await fetch(`http://localhost:8000/api/v1/sessions/${sessionId}/transcript`);
      if (response.ok) {
        const transcript = await response.json();
        setSelectedTranscript(transcript);
        setLiveTranscript(transcript.text || "");
        console.log("Transcript loaded");
      } else if (response.status === 404) {
        alert("Transcript not available yet. Try again later.");
      }
    } catch (error) {
      console.error("Failed to load transcript:", error);
      alert("Failed to load transcript");
    }
  };

  const streamTranscript = async (sessionId, isLive = false) => {
    console.log(`%c[SSE] Connecting to transcript stream (isLive: ${isLive})`, "color: purple; font-weight: bold;");
    if (isLive) {
      setSelectedTranscript({ session_id: sessionId, text: "", language: "unknown", segments: [], status: "in_progress" });
    }

    try {
      const eventSource = new EventSource(
        `http://localhost:8000/api/v1/sessions/${sessionId}/transcript/stream`
      );
      sseRef.current = eventSource;
      console.log(`%c[SSE] Connected to stream for session ${sessionId}`, "color: purple;");

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.error) {
            console.error("Transcript error:", data.error);
            setSelectedTranscript(prev => ({ ...prev, error: data.error }));
          } else {
            const text = data.text || "";
            console.log(`%c[SSE] Update (${data.status}): ${text.length} chars`, "color: purple;");
            setLiveTranscript(text);
            setSelectedTranscript(prev => ({
              ...prev,
              text: text,
              language: data.language || prev?.language,
              segments: data.segments || prev?.segments,
              status: data.status || prev?.status,
            }));
          }
        } catch (e) {
          console.error("Error parsing transcript event:", e);
        }
      };

      eventSource.onerror = () => {
        console.log(`%c[SSE] Stream closed`, "color: purple;");
        eventSource.close();
        sseRef.current = null;
      };
    } catch (error) {
      console.error("Failed to stream transcript:", error);
      if (!isLive) alert("Failed to stream transcript");
    }
  };

  const closeTranscriptView = () => {
    setSelectedTranscript(null);
    setLiveTranscript("");
    if (sseRef.current) {
      sseRef.current.close();
      sseRef.current = null;
    }
  };

  return (
    <div className="app">
      <header className="header">
        <h1>AI Voice Extractor</h1>
      </header>

      <main className="main">
        <section className="control-panel">
          <h2>New Recording</h2>

          <div className="form-group">
            <label htmlFor="microphone">Select Microphone:</label>
            <select
              id="microphone"
              value={selectedMicrophone}
              onChange={(e) => setSelectedMicrophone(e.target.value)}
              disabled={isRecording}
            >
              {microphones.map((mic) => (
                <option key={mic.deviceId} value={mic.deviceId}>
                  {mic.label || `Microphone ${mic.deviceId.substring(0, 8)}`}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="mode">Mode:</label>
            <select
              id="mode"
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              disabled={isRecording}
            >
              <option value="online">Online</option>
              <option value="offline">Offline</option>
            </select>
          </div>

          {!currentSession ? (
            <button className="btn btn-primary" onClick={startSession} disabled={!selectedMicrophone}>
              Start Session
            </button>
          ) : (
            <div>
              <p>Session ID: {currentSession.id}</p>
              {isRecording && (
                <button className="btn btn-danger" onClick={stopRecording}>
                  Stop Recording
                </button>
              )}
            </div>
          )}
        </section>

        <section className="sessions-list">
          <h2>Sessions</h2>
          {sessions.length === 0 ? (
            <p className="empty-message">No sessions yet</p>
          ) : (
            <table className="sessions-table">
              <thead>
                <tr>
                  <th>Session ID</th>
                  <th>Mode</th>
                  <th>Status</th>
                  <th>Started</th>
                  <th>Ended</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((session) => (
                  <tr key={session.id}>
                    <td className="session-id">{session.id}</td>
                    <td>{session.mode}</td>
                    <td>
                      <span className={`status ${session.status}`}>{session.status}</span>
                    </td>
                    <td>{new Date(session.created_at).toLocaleString()}</td>
                    <td>{session.closed_at ? new Date(session.closed_at).toLocaleString() : "—"}</td>
                    <td>
                      {session.status === "closed" && (
                        <button
                          className="btn btn-small btn-info"
                          onClick={() => viewTranscript(session.id)}
                        >
                          View Transcript
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        {pendingUploads.length > 0 && (
          <section className="pending-uploads">
            <h2>Pending Offline Uploads ({pendingUploads.length})</h2>
            <p className="pending-message">
              You have recordings that need to be synced to the server.
            </p>
            <ul className="pending-list">
              {pendingUploads.map((upload) => (
                <li key={upload.key} className="pending-item">
                  <span className="session-id">{upload.sessionId}</span>
                </li>
              ))}
            </ul>
            <button
              className="btn btn-primary"
              onClick={uploadPendingRecordings}
              disabled={isSyncing}
            >
              {isSyncing ? "Syncing..." : "Sync to Server"}
            </button>
          </section>
        )}

        {selectedTranscript && (
          <div className="transcript-modal-overlay" onClick={closeTranscriptView}>
            <div className="transcript-modal" onClick={(e) => e.stopPropagation()}>
              <div className="transcript-header">
                <h2>Transcript</h2>
                <button className="btn-close" onClick={closeTranscriptView}>×</button>
              </div>
              <div className="transcript-body">
                <div className="transcript-meta">
                  <p><strong>Session:</strong> {selectedTranscript.session_id}</p>
                  <p><strong>Language:</strong> {selectedTranscript.language}</p>
                  {selectedTranscript.status && (
                    <p><strong>Status:</strong> {selectedTranscript.status}</p>
                  )}
                </div>
                <div className="transcript-text">
                  {liveTranscript || "No transcript available yet"}
                </div>
                {selectedTranscript.segments && selectedTranscript.segments.length > 0 && (
                  <div className="transcript-segments">
                    <h3>Segments</h3>
                    <ul>
                      {selectedTranscript.segments.map((segment, idx) => (
                        <li key={idx}>
                          <span className="segment-time">
                            {segment.start.toFixed(1)}s - {segment.end.toFixed(1)}s:
                          </span>
                          {" "}
                          <span className="segment-text">{segment.text}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
