"use client";

import React, { useEffect, useState } from "react";
import PieChart from "../components/PieChart";
import { fetchSummaryData } from "../utils/api";
import { SummaryData } from "../types/SummaryData";

const Summary: React.FC = () => {
  const [chartData, setChartData] = useState<number[]>([]);
  const [chartLabels, setChartLabels] = useState<string[]>([]);
  const [summaryText, setSummaryText] = useState<string>("");
  const [gateUrl, setGateUrl] = useState<string | null>(null);
  const [projectDetails, setProjectDetails] = useState<any>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");

  useEffect(() => {
    const fetchData = async () => {
      try {
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
      }
    };

    fetchData();
  }, []);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  };

  if (!projectDetails) {
    return <div className="summary-card">Loading...</div>;
  }

  return (
    <div
      className="summary-container"
      style={{ display: "flex", padding: "20px", gap: "20px" }}
    >
      {/* Left Column */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          gap: "20px",
        }}
      >
        {/* Welcome Section */}
        <div
          className="summary-card"
          style={{
            padding: "20px",
            border: "1px solid #ddd",
            borderRadius: "8px",
          }}
        >
          <h2>
            Welcome to <strong>Scout!</strong>
          </h2>
          {gateUrl && (
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
                This tool has preprocessed your documents and analyzed them
                against the questions in the {gateUrl} workbook.
              </p>
            </>
          )}
        </div>

        {/* Review Summary */}
        <div
          className="summary-card"
          style={{
            padding: "20px",
            border: "1px solid #ddd",
            borderRadius: "8px",
          }}
        >
          <h3>Review Summary</h3>
          <p>{summaryText}</p>
        </div>
      </div>

      {/* Right Column */}
      <div
        className="chart-container"
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          gap: "20px",
        }}
      >
        <div
          style={{
            flex: 1,
            border: "1px solid #ddd",
            borderRadius: "8px",
            padding: "20px",
          }}
        >
          <PieChart
            data={chartData}
            labels={chartLabels}
            onClickURL="/results"
          />
        </div>
      </div>
    </div>
  );
};

export default Summary;
