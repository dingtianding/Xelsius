"use client";

import { useRef, useState } from "react";

interface FileUploadProps {
  onUpload: (file: File) => void;
  isUploading: boolean;
}

export default function FileUpload({ onUpload, isUploading }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  function handleFile(file: File) {
    const validTypes = [
      "text/csv",
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "application/vnd.ms-excel",
    ];
    const validExt = [".csv", ".xlsx", ".xls"];
    const hasValidType = validTypes.includes(file.type);
    const hasValidExt = validExt.some((ext) => file.name.toLowerCase().endsWith(ext));

    if (!hasValidType && !hasValidExt) {
      alert("Please upload a CSV or Excel file (.csv, .xlsx, .xls)");
      return;
    }
    onUpload(file);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragOver(true);
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={`border border-dashed rounded-lg px-3 py-4 text-center cursor-pointer transition-colors ${
        isDragOver
          ? "border-emerald-500 bg-emerald-900/30"
          : "border-emerald-800/40 hover:border-emerald-600 hover:bg-emerald-900/20"
      } ${isUploading ? "opacity-50 pointer-events-none" : ""}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".csv,.xlsx,.xls"
        onChange={handleChange}
        className="hidden"
      />
      <p className="text-sm text-zinc-300">
        {isUploading ? "Uploading..." : "Drop CSV or Excel file here"}
      </p>
      <p className="text-xs text-zinc-500 mt-1">
        or click to browse
      </p>
    </div>
  );
}
