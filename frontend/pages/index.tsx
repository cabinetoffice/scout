"use client";

import React, { useEffect, useState } from "react";
import PieChart from "../components/PieChart";
import { fetchSummaryData, fetchTopReferencedDocuments } from "../utils/api";
import { SummaryData } from "../types/SummaryData";
import { TopReferencedDocumentsResponse, ReferencedDocument } from "../types/ReferencedDocuments";

const Summary: React.FC = () => {
  const [chartData, setChartData] = useState<number[]>([]);
  const [chartLabels, setChartLabels] = useState<string[]>([]);
  const [summaryText, setSummaryText] = useState<string>("");
  const [gateUrl, setGateUrl] = useState<string | null>(null);
  const [projectDetails, setProjectDetails] = useState<any>({});
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [topDocuments, setTopDocuments] = useState<ReferencedDocument[]>([]);
  const [documentsLoading, setDocumentsLoading] = useState<boolean>(true);
  const [mainDataLoading, setMainDataLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setMainDataLoading(true);
        const data = await fetchSummaryData();

        // Set chart data from answer counts
        const labels = Object.keys(data.answer_count);
        const counts = Object.values(data.answer_count);
        setChartLabels(labels);
        setChartData(counts);

        // Set project details
        if (data.project) {
          setProjectDetails(data.project);
          setSummaryText(data.project.results_summary);
        }

        // Set gate URL
        setGateUrl(data.gate_url);
      } catch (error) {
        console.error("Error fetching summary data:", error);
      } finally {
        setMainDataLoading(false);
      }
    };

    fetchData();
  }, []);

  useEffect(() => {
    const fetchDocuments = async () => {
      try {
        setDocumentsLoading(true);
        const data = await fetchTopReferencedDocuments(5);
        setTopDocuments(data.documents);
      } catch (error) {
        console.error("Error fetching top referenced documents:", error);
      } finally {
        setDocumentsLoading(false);
      }
    };

    fetchDocuments();
  }, []);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  };

  return (
    <div
      className="summary-container"
      style={{ 
        display: "grid", 
        gridTemplateColumns: "1fr 1fr", 
        gridTemplateRows: "auto auto",
        gap: "20px", 
        padding: "20px",
        height: "calc(100vh - 160px)", // Adjust based on your header height
      }}
    >
      {/* Welcome Section - Top Left */}
      <div
        className="summary-card"
        style={{
          padding: "20px",
          border: "1px solid #ddd",
          borderRadius: "8px",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <h2>
          Welcome to <strong>Scout!</strong>
        </h2>
        {mainDataLoading ? (
          <p>Loading project details...</p>
        ) : gateUrl && (
          <>
            <p>
              This AI tool helps you navigate your document set before your
              review. Please check the details below are correct before
              continuing.
            </p>
            <ul>
              <li>
                <strong>Review Type:</strong> {gateUrl}
              </li>
              <li>
                <strong>Project Name:</strong> {projectDetails.name}
              </li>
            </ul>
            <p>
              This tool has preprocessed your documents and analysed them
              against the questions in the {gateUrl} workbook.
            </p>
          </>
        )}
      </div>

      {/* PieChart Section - Top Right */}
      <div
        className="summary-card"
        style={{
          padding: "20px",
          border: "1px solid #ddd",
          borderRadius: "8px",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <h3>Results Breakdown</h3>
        {mainDataLoading ? (
          <div style={{ 
            display: "flex", 
            alignItems: "center", 
            justifyContent: "center", 
            flex: 1 
          }}>
            Loading chart data...
          </div>
        ) : (
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <PieChart
              data={chartData}
              labels={chartLabels}
              onClickURL="/results"
            />
          </div>
        )}
      </div>

      {/* Review Summary - Bottom Left */}
      <div
        className="summary-card"
        style={{
          padding: "20px",
          border: "1px solid #ddd",
          borderRadius: "8px",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <h3>Review Summary</h3>
        <div style={{ flex: 1, overflow: "auto" }}>
          {mainDataLoading ? (
            <p>Loading summary...</p>
          ) : (
            <div className="formatted-summary">
              {summaryText.split("\n").map((line, index) => {
                // Check if line starts with a bullet point
                if (line.trim().startsWith("•")) {
                  return (
                    <div key={index} style={{ display: "flex", marginBottom: "16px" }}>
                      <span style={{ marginRight: "8px" }}>•</span>
                      <span>{line.substring(1).trim()}</span>
                    </div>
                  );
                }
                // Regular paragraph text
                return line.trim() ? <p key={index}>{line}</p> : null;
              })}
            </div>
          )}
        </div>
      </div>

      {/* Top Referenced Documents - Bottom Right */}
      <div
        className="summary-card"
        style={{
          padding: "20px",
          border: "1px solid #ddd",
          borderRadius: "8px",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <h3>Top Referenced Documents</h3>
        {documentsLoading ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flex: 1,
              background: "linear-gradient(90deg, #f0f0f0 25%, transparent 50%, #f0f0f0 75%)",
              backgroundSize: "200% 100%",
              animation: "loading 1.5s infinite",
              borderRadius: "4px",
            }}
          >
            <style jsx>{`
              @keyframes loading {
                0% {
                  background-position: 200% 0;
                }
                100% {
                  background-position: -200% 0;
                }
              }
            `}</style>
            <span style={{ color: "#666", fontSize: "14px" }}>Loading documents...</span>
          </div>
        ) : topDocuments.length > 0 ? (
          <div 
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(2, 1fr)",
              gap: "12px",
              flex: 1,
              overflowY: "auto"
            }}
          >
            {topDocuments.map((doc, index) => (
              <div
                key={doc.id}
                style={{
                  padding: "12px",
                  border: "1px solid #eee",
                  borderRadius: "6px",
                  display: "flex",
                  flexDirection: "column",
                  height: "fit-content",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                  <div style={{ fontWeight: "500", fontSize: "14px" }}>
                    {doc.clean_name}
                  </div>
                  <div
                    style={{
                      backgroundColor: "#e3f2fd",
                      color: "#1976d2",
                      padding: "2px 8px",
                      borderRadius: "12px",
                      fontSize: "12px",
                      fontWeight: "500",
                      minWidth: "fit-content",
                    }}
                  >
                    {doc.reference_count} refs
                  </div>
                </div>
                {doc.summary && (
                  <div style={{ fontSize: "12px", color: "#666", lineHeight: "1.3" }}>
                    {doc.summary.length > 80 
                      ? `${doc.summary.substring(0, 80)}...` 
                      : doc.summary}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div style={{ 
            flex: 1, 
            display: "flex", 
            alignItems: "center", 
            justifyContent: "center" 
          }}>
            <p style={{ color: "#666", fontStyle: "italic" }}>No referenced documents found.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Summary;