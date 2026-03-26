import api from "./client";

export const upload = (file, media_type) => {
  const form = new FormData();
  form.append("file", file);
  return api.post(`/media/upload?media_type=${media_type}`, form, {
    headers: { "Content-Type": undefined },
  });
};
