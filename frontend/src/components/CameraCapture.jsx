import React, { useRef, useCallback, useState } from 'react';
import Webcam from 'react-webcam';
import { FiCamera, FiRefreshCcw, FiX, FiTarget } from 'react-icons/fi';
import { motion } from 'framer-motion';

export default function CameraCapture({ onCapture, onCancel }) {
  const webcamRef = useRef(null);
  const [facingMode, setFacingMode] = useState("environment");

  const capture = useCallback(() => {
    const imageSrc = webcamRef.current.getScreenshot();
    if (imageSrc) {
      fetch(imageSrc)
        .then(res => res.blob())
        .then(blob => {
          const file = new File([blob], "camera_capture.jpg", { type: "image/jpeg" });
          onCapture(file);
        });
    }
  }, [webcamRef, onCapture]);

  const toggleCamera = () => {
    setFacingMode(prev => prev === "user" ? "environment" : "user");
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="relative rounded-2xl overflow-hidden bg-black/90 border border-white/10 shadow-2xl glass-glow"
    >
      <Webcam
        audio={false}
        ref={webcamRef}
        screenshotFormat="image/jpeg"
        videoConstraints={{
          facingMode: facingMode,
          width: { ideal: 1080 },
          height: { ideal: 1080 }
        }}
        className="w-full h-auto max-h-[60vh] object-cover"
      />

      {/* Controls Overlay */}
      <div className="absolute bottom-6 left-0 right-0 gap-6 flex justify-center items-center z-10">
        <button
          onClick={onCancel}
          className="w-12 h-12 rounded-full bg-black/40 backdrop-blur-md border border-white/20 text-white flex justify-center items-center hover:bg-black/60 transition-all"
        >
          <FiX size={20} />
        </button>

        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={capture}
          className="w-20 h-20 rounded-full bg-white/20 backdrop-blur-md border-4 border-orange-500 text-white flex justify-center items-center group relative shadow-[0_0_30px_rgba(249,115,22,0.6)]"
        >
          <div className="w-14 h-14 rounded-full bg-orange-500 group-hover:bg-orange-400 transition-colors flex items-center justify-center text-white shadow-inner">
            <FiCamera size={28} />
          </div>
        </motion.button>

        <button
          onClick={toggleCamera}
          className="w-12 h-12 rounded-full bg-black/40 backdrop-blur-md border border-white/20 text-white flex justify-center items-center hover:bg-black/60 transition-all"
        >
          <FiRefreshCcw size={20} />
        </button>
      </div>

      {/* Viewfinder brackets */}
      <div className="absolute top-10 left-10 w-16 h-16 border-t-4 border-l-4 border-orange-500/70 rounded-tl-xl pointer-events-none"></div>
      <div className="absolute top-10 right-10 w-16 h-16 border-t-4 border-r-4 border-orange-500/70 rounded-tr-xl pointer-events-none"></div>
      <div className="absolute bottom-28 left-10 w-16 h-16 border-b-4 border-l-4 border-orange-500/70 rounded-bl-xl pointer-events-none"></div>
      <div className="absolute bottom-28 right-10 w-16 h-16 border-b-4 border-r-4 border-orange-500/70 rounded-br-xl pointer-events-none"></div>
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-30 mt-[-50px]">
        <FiTarget size={64} className="text-orange-500" />
      </div>

      <div className="absolute top-4 left-0 right-0 text-center pointer-events-none">
        <span className="bg-black/60 backdrop-blur px-4 py-1.5 rounded-full text-xs font-semibold text-orange-400 tracking-widest uppercase border border-white/10">
          Align Footprint in Center
        </span>
      </div>
    </motion.div>
  );
}
