"use client"; // This is a client component

import React, { useEffect, useState, useContext } from "react";
import PieChart from "../components/PieChart";
import { getGateUrl } from "../utils/getGateUrl";
import { fetchUser, fetchReadItemsByAttribute, fetchItems } from "../utils/api";

interface Result {
  answer: string;
  created_datetime: string;
  criterion: Criterion;
  full_text: string;
  id: string;
}

interface Criterion {
  id: string;
  question: string;
  evidence: string;
  category: string;
  gate: string;
}

const Summary: React.FC = () => {
  const [chartData, setChartData] = useState<number[]>([]);
  const [chartLabels, setChartLabels] = useState<string[]>([]);
  const [summaryText, setSummaryText] = useState<string>("");
  const [gateUrl, setGateUrl] = useState<string | null>(null);
  const [categories, setCategories] = useState<{ [key: string]: number }>({});
  const [projectDetails, setProjectDetails] = useState<any>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        console.log("Fetching results...");
        const results = await fetchReadItemsByAttribute({
          model: "result",
          filters: {},
        });
        console.log("Negative results fetched:", results);

        const answerCount: { [key: string]: number } = {};
        results.forEach((result: Result) => {
          answerCount[result.answer] = (answerCount[result.answer] || 0) + 1;
        });

        setChartLabels(Object.keys(answerCount));
        setChartData(Object.values(answerCount));

        console.log("Chart labels:", Object.keys(answerCount));
        console.log("Chart data:", Object.values(answerCount));

        // Fetching the project details
        console.log("Fetching project details...");
        const projectData = await fetchItems("project");

        console.log("Project details fetched:", projectData);

        if (projectData.length > 0) {
          setProjectDetails(projectData[0]);
          setSummaryText(projectData[0].results_summary);
        }
      } catch (error) {
        console.error("Error fetching data:", error);
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
        <br />
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
            <p>
              {gateUrl && (
                <>
                  This AI tool helps you navigate your document set before your
                  review. Please check the details below are correct before
                  continuing
                  <ul>
                    <strong>Review Type:</strong> {projectDetails.review_type}{" "}
                    <br />
                    <strong>Project Name:</strong> {projectDetails.name}
                  </ul>
                  This tool has preprocessed your documents and analysed them
                  against the questions in the
                  <a href={gateUrl} target="_blank" rel="noopener noreferrer">
                    {projectDetails.review_type} workbook
                  </a>
                  .
                </>
              )}
            </p>
            {projectDetails && (
              <div style={{ marginTop: "20px" }}>
                <h3>Project Overview</h3>
                <ul style={{ listStyleType: "none", padding: 0 }}>
                  <li>
                    <strong>Project Name:</strong> {projectDetails.name}
                  </li>
                  <li>
                    <strong>Review Type:</strong> {projectDetails.review_type}
                  </li>
                  <li>
                    <strong>Created Date:</strong>{" "}
                    {new Date(
                      projectDetails.created_datetime
                    ).toLocaleDateString()}
                  </li>
                  <li>
                    <strong>Description:</strong> {projectDetails.description}
                  </li>
                </ul>
              </div>
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
