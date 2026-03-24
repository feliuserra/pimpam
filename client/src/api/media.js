import api from "./client";

export const upload = (file, media_type) => {
  const form = new FormData();
  form.append("file", file);
  form.append("media_type", media_type);
  return api.post("/media/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};
