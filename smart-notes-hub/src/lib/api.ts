const API_BASE_URL = "http://localhost:5000";

export const uploadFiles = async (files: File[]) => {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append("files", file);
  });

  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("File upload failed");
  }

  return response.json();
};

export const generateNotes = async (
  basePrompt: string,
  topics: string[],
  batchSize: number
) => {
  const response = await fetch(`${API_BASE_URL}/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      base_prompt: basePrompt,
      topics: topics,
      batch_size: batchSize,
    }),
  });

  if (!response.ok) {
    throw new Error("Note generation failed");
  }

  return response.text();
};

export const chat = async (prompt: string, base_prompt?: string) => {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ prompt, base_prompt }),
  });

  if (!response.ok) {
    throw new Error("Chat failed");
  }

  return response.text();
};

export const resetSystem = async () => {
  const response = await fetch(`${API_BASE_URL}/reset`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error("System reset failed");
  }

  return response.json();
};
