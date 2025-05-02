import React, { useEffect, useState, useCallback } from "react";
import { fetchItems, fetchReadItemsByAttribute, fetchFile } from "@/utils/api";
import { useRouter } from "next/router";
import { Tabs, Tab, Box } from "@mui/material";

interface File {
  name: string | null;
  id: string;
  clean_name: string | null;
  url: string | null;
  s3_key: string | null;
  summary: string | null;
}

const FileViewer: React.FC = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [selectedFile, setSelectedFile] = useState<{
    dataUrl: string;
    fileType: string;
  } | null>(null);
  const [summaryData, setSummaryData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pageNumber, setPageNumber] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<"summary" | "viewer">("summary");
  const router = useRouter();
  const { citation } = router.query;
  const [citationUuid, setCitationUuid] = useState<string>("");

  useEffect(() => {
    if (citation && typeof citation === "string") {
      setCitationUuid(citation);
    }
  }, [citation]);

  const handleFileClick = useCallback(async (file: File, pageNum?: number) => {
    setIsLoading(true);
    setSelectedFile(null);
    setSummaryData(null);
    setError(null);
    setPageNumber(pageNum || 1);

    try {
      const { url, fileType } = await fetchFile(file.id);
      setSelectedFile({ dataUrl: url, fileType });
      setSummaryData(file.summary);
    } catch (error) {
      console.error("Error fetching file data:", error);
      setError("Failed to fetch file. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const fetchFiles = async () => {
      try {
        const response = await fetchReadItemsByAttribute({
          model: "file",
          filters: {},
        });
        setFiles(response);

        if (citationUuid) {
          const citation = await fetchItems("chunk", citationUuid);
          if (citation && citation.id) {
            handleFileClick(
              { id: citation.file.id } as File,
              citation.page_num
            );
          }
        }
      } catch (error) {
        console.error("Error fetching files", error);
        setError("Failed to fetch files. Please try again.");
      }
    };

    fetchFiles();
  }, [citationUuid, handleFileClick]);

  const handleDownload = useCallback(() => {
    if (selectedFile) {
      const link = document.createElement("a");
      link.href = selectedFile.dataUrl;
      link.download = "file"; // You might want to set a proper filename here
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  }, [selectedFile]);

  useEffect(() => {
    return () => {
      if (selectedFile) {
        URL.revokeObjectURL(selectedFile.dataUrl);
      }
    };
  }, [selectedFile]);

  const handleTabChange = (
    event: React.SyntheticEvent,
    newValue: "summary" | "viewer"
  ) => {
    setActiveTab(newValue);
  };

  return (
    <div
      className="file-viewer flex h-[calc(100vh-100px)]"
      style={{ width: "100%" }}
    >
      <div className="file-list flex-shrink-0 w-72 overflow-y-auto border-r border-gray-300 p-5">
        <h2 className="text-lg font-semibold mb-4">Document Set</h2>
        <ul className="list-none p-0">
          {files.map((file) => (
            <li key={file.id} className="mb-2">
              <button
                onClick={() => handleFileClick(file)}
                className="w-full text-left p-2 bg-gray-100 hover:bg-gray-200 rounded"
              >
                {file.clean_name || file.name}
              </button>
            </li>
          ))}
        </ul>
      </div>
      <div className="w-full width-full flex flex-col" style={{ width: "75%" }}>
        <div className="document-viewer flex-1 overflow-y-auto p-5">
          <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
            <Tabs
              value={activeTab}
              onChange={handleTabChange}
              aria-label="File Viewer Tabs"
            >
              <Tab label="Summary" value="summary" />
              <Tab label="Viewer" value="viewer" />
            </Tabs>
          </Box>
        </div>
        {isLoading ? (
          <div>Loading...</div>
        ) : error ? (
          <div className="text-red-500">{error}</div>
        ) : activeTab === "summary" ? (
          <div className="summary">
            {summaryData ? (
              <pre className="bg-gray-100 p-4 rounded text-wrap-auto text-align-justify">
                {JSON.stringify(summaryData, null, 2)}
              </pre>
            ) : (
              <div>No summary available</div>
            )}
          </div>
        ) : selectedFile ? (
          selectedFile.fileType.toLowerCase() === "application/pdf" ? (
            <iframe
              src={`${selectedFile.dataUrl}#view=FitH&navpanes=0${
                pageNumber ? `&page=${pageNumber}` : ""
              }`}
              width="100%"
              height="100%"
              className="border-none"
              title="PDF Viewer"
            />
          ) : (
            <div>
              <p>This file type cannot be viewed in the browser.</p>
              <button
                onClick={handleDownload}
                className="mt-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
              >
                Download File
              </button>
            </div>
          )
        ) : (
          <div className="text-gray-500">Select a file to view</div>
        )}
      </div>
    </div>
  );
};

export default FileViewer;
