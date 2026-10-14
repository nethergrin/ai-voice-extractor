import axios from "axios";
import { API_BASE_URL, CLIENT_ID } from "./config";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const sessionAPI = {
  createSession: async (mode) => {
    const response = await api.post("/sessions/", {
      client_id: CLIENT_ID,
      mode: mode,
    });
    return response.data;
  },

  getSessions: async () => {
    const response = await api.get("/sessions/");
    return response.data.sessions;
  },

  getSession: async (sessionId) => {
    const response = await api.get(`/sessions/${sessionId}`);
    return response.data;
  },

  closeSession: async (sessionId) => {
    const response = await api.post(`/sessions/${sessionId}/close`);
    return response.data;
  },
};

export const audioAPI = {
  uploadAudio: async (sessionId, audioBlob, filename = "audio.wav", sessionMetadata = {}) => {
    const formData = new FormData();
    formData.append("file", audioBlob, filename);

    // Include session metadata for auto-creation if session doesn't exist
    const params = new URLSearchParams({
      client_id: sessionMetadata.client_id || CLIENT_ID,
      mode: sessionMetadata.mode || "online",
    });

    const response = await axios.post(
      `${API_BASE_URL}/sessions/${sessionId}/audio?${params.toString()}`,
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );
    return response.data;
  },
};
