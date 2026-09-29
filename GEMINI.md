# Project Overview

This is a full-stack application that allows users to upload PDF documents and generate intelligent, structured notes from them. The backend is a Python/Flask application that uses the Google Gemini API for natural language processing, and the frontend is a React application built with Vite.

## Backend

The backend is a Flask application that provides a RESTful API for file uploading, note generation, and system reset.

*   **`Api.py`**: This is the main entry point of the backend application. It defines the Flask application and the API endpoints.
*   **`processing.py`**: This file contains the core logic for processing PDFs and generating notes. It uses `PyPDF2` and `paddleocr` to extract text from PDFs, `fastembed` and `qdrant-client` to create and store vector embeddings, and the `google-generativeai` library to interact with the Gemini API.
*   **`document_cache.py`**: This file provides a caching mechanism to avoid reprocessing the same PDF files.
*   **`requirements.txt`**: This file lists all the Python dependencies for the backend.

## Frontend

The frontend is a React application built with Vite and written in TypeScript. It uses `shadcn/ui` for UI components, `tailwindcss` for styling, `react-router-dom` for routing, and `@tanstack/react-query` for data fetching.

*   **`smart-notes-hub/`**: This directory contains the frontend code.
*   **`smart-notes-hub/src/App.tsx`**: This is the main component of the frontend application. It sets up the routing and the overall layout of the application.
*   **`smart-notes-hub/src/pages/`**: This directory contains the different pages of the application, such as the upload page, the notes page, and the chat page.
*   **`smart-notes-hub/package.json`**: This file lists all the npm dependencies for the frontend.

# Building and Running

## Docker (Recommended)

1.  Create a `.env` file with your Gemini API keys:
    ```env
    GEMINI_API_KEY_QUERY=
    GEMINI_API_KEY_GENERATE=
    ```
2.  Run the application using Docker Compose:
    ```bash
    docker compose up
    ```

## Local Development

### Backend

1.  Create a `.env` file with your Gemini API keys (see above).
2.  Install the Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the backend server:
    ```bash
    python Api.py
    ```

### Frontend

1.  Navigate to the `smart-notes-hub` directory:
    ```bash
    cd smart-notes-hub
    ```
2.  Install the npm dependencies:
    ```bash
    npm install
    ```
3.  Run the frontend development server:
    ```bash
    npm run dev
    ```

# Development Conventions

*   The backend follows the standard Flask application structure.
*   The frontend uses functional components with hooks.
*   Styling is done using `tailwindcss`.
*   UI components are from `shadcn/ui`.
*   The frontend uses `prettier` for code formatting and `eslint` for linting.
*   The `UploadPage.tsx` currently has a simulated upload process. This should be replaced with an actual API call to the `/upload` endpoint.
*   The "Reset All" button on the `UploadPage` should call the `/reset` endpoint.
