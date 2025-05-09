"use client";

import React, { useEffect, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import { useRouter } from "next/router";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import styles from "../public/styles/Results.module.css";
import { ColDef, ICellRendererParams } from "ag-grid-community";
import { Modal, Typography, IconButton, Chip } from "@mui/material";
import {
  Close as CloseIcon,
  ThumbUp as ThumbUpIcon,
  ThumbDown as ThumbDownIcon,
} from "@mui/icons-material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import HelpIcon from "@mui/icons-material/Help";

import { rateResponse } from "@/utils/api";
import MagnifyingGlassLoader from "../components/Loader";
import Link from "next/link";

interface Rating {
  id: string;
  project: Project;
  result: Result;
  positive_rating: boolean;
  created_datetime: Date;
  updated_datetime: Date | null;
}

interface Criterion {
  id: string;
  category: string;
  created_datetime: Date;
  evidence: string;
  gate: string;
  question: string;
  updated_datetime: Date | null;
}

interface Chunk {
  id: string;
  idx: string;
  page_num: number;
  text: string;
  created_datetime: Date;
  updated_datetime: Date | null;
}

interface Project {
  id: string;
  created_datetime: Date;
  updated_datetime: Date | null;
  name: string;
  results_summary: string | null;
}

interface Result {
  answer: string;
  created_datetime: Date;
  updated_datetime: Date | null;
  criterion: Criterion;
  chunks: Chunk[];
  project: Project;
  ratings: Rating[];
  full_text: string;
  id: string;
}

interface Source {
  chunk_id: string;
  fileName: string;
}

interface TransformedResult {
  Criterion: Criterion;
  Chunks: Chunk[];
  Project: Project;
  Ratings: Rating[];
  Evidence: string;
  Category: string;
  Gate: string;
  Status: string;
  Justification: string;
  Sources: Source[];
  id: string;
  sourceCount: number;
}

const ResultsTable: React.FC = () => {
  const [results, setResults] = useState<TransformedResult[]>([]);
  const [open, setOpen] = useState(false);
  const [selectedRow, setSelectedRow] = useState<TransformedResult | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [thumbsUpColour, setThumbsUpColour] = useState({ color: "none" });
  const [thumbsDownColour, setThumbsDownColour] = useState({ color: "none" });
  const [expandEvidence, setExpandEvidence] = useState(false);
  const [expandJustification, setExpandJustification] = useState(false);

  const [page, setPage] = useState(1);
  const [totalRows, setTotalRows] = useState(0);
  const pageSize = 50;
  const router = useRouter();

  const handleOpen = () => setOpen(true);
  const handleClose = () => setOpen(false);

  const handleThumbsUp = async (resultId: string) => {
    try {
      const response = await rateResponse({
        result_id: resultId,
        good_response: true,
      });
      console.log("Thumbs up response:", response);
      setThumbsUpColour({ color: "green" });
      setThumbsDownColour({ color: "none" });
    } catch (error) {
      console.error("Error giving thumbs up:", error);
    }
  };

  const handleThumbsDown = async (resultId: string) => {
    try {
      const response = await rateResponse({
        result_id: resultId,
        good_response: false,
      });
      console.log("Thumbs down response:", response);
      setThumbsDownColour({ color: "red" });
      setThumbsUpColour({ color: "none" });
    } catch (error) {
      console.error("Error giving thumbs down:", error);
    }
  };

  const getStatusChipColor = (status: string) => {
    switch (status) {
      case "Positive":
        return "green";
      case "Neutral":
        return "orange";
      case "Negative":
        return "red";
      default:
        return "default";
    }
  };

  const ModalContent = () => {
    if (!selectedRow) return null;

    return (
      <div className={styles.modalContainer}>
        <div className={styles.modalHeader}>
          <IconButton
            aria-label="close"
            onClick={handleClose}
            className={styles.closeButton}
          >
            <CloseIcon />
          </IconButton>
          <Typography variant="subtitle1">
            <b>{selectedRow.Criterion.question}</b>
          </Typography>
          <div className={styles.chipsContainer}>
            <div
              style={{
                backgroundColor: getStatusChipColor(selectedRow.Status),
              }}
              className={styles.statusChip}
            >
              {selectedRow.Status}
            </div>
            <div className={styles.greyChip}>{selectedRow.Category}</div>
            <div className={styles.greyChip}>{selectedRow.Gate}</div>
          </div>
        </div>

        <div className={styles.modalContent}>
          <Typography
            variant="subtitle2"
            className={styles.sectionTitle}
            onClick={() => setExpandJustification(!expandJustification)}
            style={{ cursor: "pointer" }}
          >
            AI Justification {expandJustification ? "▼" : "▶"}
          </Typography>
          {expandJustification && (
            <div>
              <div
                style={{
                  backgroundColor: "#fff3cd",
                  border: "1px solid #ffeeba",
                  padding: "10px",
                  borderRadius: "4px",
                  marginBottom: "16px",
                }}
              >
                <Typography
                  variant="subtitle2"
                  style={{ fontWeight: "bold", color: "#856404" }}
                >
                  Important
                </Typography>
                <Typography
                  variant="body2"
                  style={{ color: "#856404", marginTop: "4px" }}
                >
                  This is an experimental service using AI to generate
                  responses. Please verify critical information by consulting
                  official GOV.UK guidance.
                </Typography>
              </div>
              <Typography variant="body2" className={styles.sectionText}>
                {selectedRow.Justification}
              </Typography>
              <Typography variant="body1" className={styles.sectionText}>
                <Link
                  href={`/custom-query?query=${encodeURIComponent(
                    selectedRow.Criterion.question
                  )}`}
                  passHref
                  legacyBehavior
                >
                  <a className="App-link">Explore further</a>
                </Link>
              </Typography>
            </div>
          )}
          <Typography
            variant="subtitle2"
            className={styles.sectionTitle}
            onClick={() => setExpandEvidence(!expandEvidence)}
            style={{ cursor: "pointer" }}
          >
            Evidence Considered {expandEvidence ? "▼" : "▶"}
          </Typography>
          {expandEvidence && (
            <Typography variant="body2" className={styles.sectionText}>
              {formatEvidence(selectedRow.Evidence)}
            </Typography>
          )}

          <Typography variant="subtitle2" className={styles.sectionTitle}>
            Sources:
          </Typography>
          <div className={styles.sourcesContainer}>
            {isLoadingDetails ? (
              <div style={{ textAlign: "center", padding: "10px" }}>
                <MagnifyingGlassLoader />
              </div>
            ) : (
              selectedRow.Sources.map((source: Source) => (
                <Chip
                  key={source.chunk_id}
                  label={source.fileName}
                  onClick={() => handleCitationClick(source.chunk_id)}
                  style={{ cursor: "pointer", marginBottom: "4px" }}
                />
              ))
            )}
          </div>
        </div>

        <div className={styles.modalFooter}>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              marginRight: "20px",
            }}
          >
            <IconButton
              onClick={() => handleRating(true)}
              aria-label="thumbs up"
            >
              <ThumbUpIcon style={thumbsUpColour} />
            </IconButton>
            <Typography variant="caption" style={{ marginTop: "4px" }}>
              Helpful
            </Typography>
          </div>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
            }}
          >
            <IconButton
              onClick={() => handleRating(false)}
              aria-label="thumbs down"
            >
              <ThumbDownIcon style={thumbsDownColour} />
            </IconButton>
            <Typography variant="caption" style={{ marginTop: "4px" }}>
              Not Helpful
            </Typography>
          </div>
        </div>
      </div>
    );
  };

  useEffect(() => {
    if (!router.isReady) return;

    const fetchData = async () => {
      try {
        const queryAnswer = router.query.answer as string | undefined;
        const response = await fetch(
          `/api/paginated_results?page=${page}&page_size=${pageSize}${
            queryAnswer ? `&status_filter=${queryAnswer}` : ""
          }`
        );

        if (!response.ok) {
          throw new Error("Failed to fetch results");
        }

        const data = await response.json();
        const transformedResults = data.items.map((result: any) => ({
          Criterion: result.criterion,
          Evidence: "", // Will be loaded on demand
          Category: result.criterion.category,
          Gate: result.criterion.gate,
          Status: result.status,
          Justification: "", // Will be loaded on demand
          Sources: [], // Will be loaded on demand
          id: result.id,
          Chunks: [], // Will be loaded on demand
          sourceCount: result.source_count,
        }));

        setResults(transformedResults);
        setTotalRows(data.total);
      } catch (error) {
        console.error("Error fetching data:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [router.isReady, router.query, page]);

  const loadResultDetails = async (resultId: string) => {
    try {
      const response = await fetch(`/api/result_details/${resultId}`);
      if (!response.ok) {
        throw new Error("Failed to fetch result details");
      }
      const details = await response.json();
      return {
        ...details,
        Sources: details.sources,
        Criterion: details.criterion,
        Status: details.status,
        Justification: details.justification,
        Ratings: details.ratings,
      };
    } catch (error) {
      console.error("Error loading result details:", error);
      return null;
    }
  };

  const onRowClicked = async (row: any) => {
    setThumbsUpColour({ color: "" });
    setThumbsDownColour({ color: "" });
    setSelectedRow(row.data);
    setIsLoadingDetails(true);
    setOpen(true);

    const details = await loadResultDetails(row.data.id);
    if (details) {
      setSelectedRow((prev) => ({
        ...prev!,
        Evidence: details.Criterion.evidence,
        Justification: details.Justification,
        Sources: details.Sources,
        Ratings: details.Ratings,
      }));

      if (details.Ratings && details.Ratings.length > 0) {
        const latestRating = details.Ratings[details.Ratings.length - 1];
        setThumbsUpColour({
          color: latestRating.positive_rating ? "lightgreen" : "none",
        });
        setThumbsDownColour({
          color: latestRating.positive_rating ? "none" : "red",
        });
      }
    }
    setIsLoadingDetails(false);
  };

  const formatEvidence = (evidence: string) => {
    return evidence.split("_").map((item, index) => (
      <React.Fragment key={index}>
        {index > 0 && "• "}
        {item}
        {index > 0 && <br />}
      </React.Fragment>
    ));
  };

  const handleRating = async (goodResponse: boolean) => {
    if (!selectedRow) return;

    try {
      await rateResponse({
        result_id: selectedRow.id,
        good_response: goodResponse,
      });
      console.log(
        `Rated response ${selectedRow.id} as ${goodResponse ? "up" : "down"}`
      );
      if (goodResponse) {
        setThumbsDownColour({ color: "" });
        setThumbsUpColour({ color: "lightgreen" });
      } else {
        setThumbsUpColour({ color: "" });
        setThumbsDownColour({ color: "red" });
      }
    } catch (error) {
      console.error("Error rating response:", error);
    }
  };

  const handleCitationClick = (chunk_id: string) => {
    router.push({ pathname: "/file-viewer", query: { citation: chunk_id } });
  };

  const columnDefs: ColDef[] = [
    {
      headerName: "Criterion",
      field: "Criterion",
      wrapText: true,
      autoHeight: true,
      flex: 5,
      cellRenderer: (params: ICellRendererParams) => params.value.question,
      cellStyle: { textAlign: "left" },
      headerClass: "center-header",
    },
    {
      headerName: "Category",
      field: "Category",
      wrapText: true,
      autoHeight: true,
      flex: 1,
      cellStyle: { textAlign: "center" },
      headerClass: "center-header",
    },
    {
      headerName: "Status",
      field: "Status",
      wrapText: true,
      autoHeight: true,
      flex: 1,
      cellRenderer: (params: ICellRendererParams) => {
        switch (params.value) {
          case "Positive":
            return <CheckCircleIcon style={{ color: "green" }} />;
          case "Neutral":
            return <HelpIcon style={{ color: "orange" }} />;
          case "Negative":
            return <ErrorIcon style={{ color: "red" }} />;
          default:
            return params.value;
        }
      },
      cellStyle: { textAlign: "center" },
      headerClass: "center-header",
    },
    {
      headerName: "Sources",
      field: "sourceCount",
      wrapText: true,
      autoHeight: true,
      flex: 1,
      cellRenderer: (params: any) => {
        return `${params.value} sources`;
      },
      cellStyle: { textAlign: "center" },
      headerClass: "center-header",
    },
  ];

  return (
    <div className={styles.tableContainer}>
      {isLoading ? (
        <MagnifyingGlassLoader />
      ) : (
        <div className={`ag-theme-alpine ${styles.gridContainer}`}>
          <AgGridReact
            rowData={results}
            columnDefs={columnDefs}
            defaultColDef={{
              wrapText: true,
              autoHeight: true,
              filter: true,
            }}
            onRowClicked={onRowClicked}
            pagination={true}
            paginationPageSize={pageSize}
            onPaginationChanged={(params) => {
              const currentPage = params.api.paginationGetCurrentPage();
              setPage(currentPage + 1);
            }}
          />
        </div>
      )}
      <Modal
        open={open}
        onClose={handleClose}
        aria-labelledby="modal-modal-title"
        aria-describedby="modal-modal-description"
      >
        <ModalContent />
      </Modal>
    </div>
  );
};

export default ResultsTable;
