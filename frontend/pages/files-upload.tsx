import React, { useEffect, useState, useCallback } from "react";
import { AgGridReact } from "ag-grid-react";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import { ColDef } from "ag-grid-community";
import { useDropzone } from "react-dropzone";
import {
  fetchFilesAsAdmin,
  uploadFilesToS3,
  deleteFileFromS3,
  getSignedFileUrl,
} from "@/utils/api";

interface S3File {
  key: string;
  lastModified?: string;
  size?: number;
}

const S3FileUploader: React.FC = () => {
  const [files, setFiles] = useState<S3File[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const fetchFiles = async () => {
    try {
      const res = await fetchFilesAsAdmin();
      setFiles(res);
    } catch (err) {
      console.error("Error fetching files:", err);
    }
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setSelectedFiles((prev) => [...prev, ...acceptedFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "image/*": [],
      "application/pdf": [],
    },
  });

  const handleUpload = async () => {
    if (!selectedFiles.length) return;

    const formData = new FormData();
    selectedFiles.forEach((file) => {
      formData.append("files", file);
    });

    setUploading(true);
    try {
      await uploadFilesToS3(formData);
      alert("Upload successful!");
      setSelectedFiles([]);
      setPreviewUrl(null);
      fetchFiles();
    } catch (err) {
      console.error("Upload failed:", err);
      alert("Failed to upload files.");
    } finally {
      setUploading(false);
    }
  };

  const handlePreview = async (key: string) => {
    try {
      const url = await getSignedFileUrl(key);
      setPreviewUrl(url);
    } catch (err) {
      console.error("Failed to get signed URL:", err);
      setPreviewUrl(null);
    }
  };

  const handleDelete = async (key: string) => {
    if (window.confirm(`Delete file "${key}" from Scout?`)) {
      try {
        await deleteFileFromS3(key);
        fetchFiles();
      } catch (err) {
        console.error("Failed to delete file:", err);
        alert("Failed to delete file.");
      }
    }
  };

  const columnDefs: ColDef[] = [
    { headerName: "Key", field: "key", flex: 4 },
    {
      headerName: "Last Modified",
      field: "lastModified",
      flex: 2,
      valueFormatter: (params) =>
        params.value ? new Date(params.value).toLocaleString() : "N/A",
    },
    {
      headerName: "Size (KB)",
      field: "size",
      flex: 1,
      valueFormatter: (params) =>
        params.value ? (params.value / 1024).toFixed(2) : "0.00",
    },
    {
      headerName: "Actions",
      field: "actions",
      cellRenderer: (params: any) => (
        <div>
          <button
            onClick={() => handlePreview(params.data.key)}
            style={actionBtn}
          >
            Preview
          </button>
          <button
            onClick={() => handleDelete(params.data.key)}
            style={{ ...actionBtn, color: "red" }}
          >
            Delete
          </button>
        </div>
      ),
      flex: 2,
    },
  ];

  return (
    <div style={{ padding: "20px" }}>
      <h2>Upload Project Files</h2>

      <div
        {...getRootProps()}
        style={{
          border: "2px dashed #ccc",
          padding: "20px",
          marginBottom: "15px",
          borderRadius: "6px",
          background: isDragActive ? "#f0f8ff" : "#fafafa",
          cursor: "pointer",
          textAlign: "center",
        }}
      >
        <input {...getInputProps()} />
        {isDragActive ? (
          <p>Drop files here...</p>
        ) : (
          <p>Drag & drop files here, or click to select</p>
        )}
      </div>

      {selectedFiles.length > 0 && (
        <div style={{ marginBottom: "20px" }}>
          <h4>Files Ready to Upload:</h4>
          <ul>
            {selectedFiles.map((file, i) => (
              <li key={i}>
                {file.name} ({(file.size / 1024).toFixed(1)} KB)
              </li>
            ))}
          </ul>
          <button onClick={handleUpload} disabled={uploading} style={uploadBtn}>
            {uploading ? "Uploading..." : "Upload"}
          </button>
        </div>
      )}

      {previewUrl && (
        <div style={{ marginBottom: "20px" }}>
          <h4>Preview</h4>
          {previewUrl.includes(".pdf") ? (
            <embed
              src={previewUrl}
              type="application/pdf"
              width="100%"
              height="400px"
            />
          ) : (
            <img
              src={previewUrl}
              alt="Preview"
              style={{ maxWidth: "100%", maxHeight: "400px" }}
            />
          )}
        </div>
      )}

      <h3>Files in Scout</h3>
      <div className="ag-theme-alpine" style={{ height: 400, width: "100%" }}>
        <AgGridReact
          rowData={files}
          columnDefs={columnDefs}
          defaultColDef={{ resizable: true, wrapText: true, autoHeight: true }}
        />
      </div>
    </div>
  );
};

export default S3FileUploader;

// Styles
const uploadBtn: React.CSSProperties = {
  marginTop: "10px",
  padding: "8px 16px",
  backgroundColor: "#4CAF50",
  color: "white",
  border: "none",
  borderRadius: "4px",
  cursor: "pointer",
};

const actionBtn: React.CSSProperties = {
  marginRight: "10px",
  padding: "4px 10px",
  backgroundColor: "#007bff",
  color: "white",
  border: "none",
  borderRadius: "4px",
  cursor: "pointer",
};
