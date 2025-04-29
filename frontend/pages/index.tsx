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

  if (!projectDetails) {
    return <div className="summary-card">Loading...</div>;
  }

  return (
    <div>
      <div>
        <div
          className="summary-card"
          style={{
            display: "flex",
            alignItems: "center",
            marginBottom: "20px",
            marginTop: "40px",
          }}
        >
          <div style={{ flex: 1 }}>
            <h2>
              Welcome to <strong>Scout!</strong>
            </h2>
            <p></p>
            {gateUrl && (
              <>
                This AI tool helps you navigate your document set before your
                review. Please check the details below are correct before
                continuing
                <ul>
                  <strong>Review Type:</strong> {gateUrl} <br />
                  <br />
                  <strong>Project Name:</strong> {projectDetails.name}
                </ul>
                This tool has preprocessed your documents and analysed them
                against the questions in the&nbsp;
                {/* <a href="#" target="_blank" rel="noopener noreferrer"> */}
                {gateUrl} workbook
                {/* </a> */}.
              </>
            )}
          </div>
        </div>
      </div>

      <div
        className="summary-card"
        style={{ display: "flex", alignItems: "top", marginBottom: "20px" }}
      >
        <div style={{ flex: 1 }}>
          <h2>Review Summary</h2>
          <p>{summaryText}</p>
        </div>
        <div className="chart-container" style={{ flex: 1 }}>
          <PieChart data={chartData} labels={chartLabels} />
        </div>
      </div>
      {chartLabels.map((label, index) => (
        <div
          className="summary-card"
          key={label}
          style={{ marginBottom: "20px" }}
        >
          <h2>{label}</h2>
          <p>{`Count: ${chartData[index]}`}</p>
          <a href={`/results?answer=${label}`}>View {label} results</a>
        </div>
      ))}
    </div>
  );
};

export default Summary;
