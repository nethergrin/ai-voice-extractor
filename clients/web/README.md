# AI Voice Extractor - Web Client

React web client for the AI Voice Extractor system.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Update `.env` with your backend API URL (default is `http://localhost:8000/api/v1`):
```
REACT_APP_API_URL=http://localhost:8000/api/v1
```

3. Start the development server:
```bash
npm start
```

The app will open at `http://localhost:3000`

## Features

- Create new recording sessions
- Choose between online (stream) or offline (store locally) modes
- Select microphone device
- View session history with timestamps
- Automatic audio upload for online mode
- Local storage of audio for offline mode

## Build

```bash
npm run build
```

This creates a production build in the `build` directory.
