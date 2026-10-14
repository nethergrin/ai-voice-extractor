export const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000/api/v1";
export const CLIENT_ID = "web-client-v1";

// Stream transcription chunk interval in milliseconds (default: 5 seconds)
export const STREAM_CHUNK_INTERVAL = parseInt(process.env.REACT_APP_STREAM_CHUNK_INTERVAL || "5000", 10);
