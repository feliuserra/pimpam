import { useState } from "react";
import Lightbox from "./Lightbox";
import styles from "./ImageGallery.module.css";

export default function ImageGallery({ images }) {
  const [lightboxIndex, setLightboxIndex] = useState(null);

  if (!images || images.length === 0) return null;

  const count = images.length;
  const layoutClass =
    count === 1 ? styles.single : count === 2 ? styles.double : styles.grid;

  return (
    <>
      <div className={`${styles.gallery} ${layoutClass}`}>
        {images.slice(0, 4).map((img, i) => (
          <button
            key={img.url}
            className={styles.imageBtn}
            onClick={() => setLightboxIndex(i)}
            aria-label={`View image ${i + 1}`}
          >
            <img src={img.url} alt="" className={styles.image} loading="lazy" />
            {i === 3 && count > 4 && (
              <span className={styles.more}>+{count - 4}</span>
            )}
          </button>
        ))}
      </div>

      {lightboxIndex !== null && (
        <Lightbox
          images={images}
          index={lightboxIndex}
          onClose={() => setLightboxIndex(null)}
          onIndexChange={setLightboxIndex}
        />
      )}
    </>
  );
}
