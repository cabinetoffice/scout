"use client";

import React, { useEffect, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import { useRouter } from "next/router";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import { ColDef, ICellRendererParams } from "ag-grid-community";
import { Modal, Box, Typography, IconButton, Chip } from "@mui/material";
import {
  Close as CloseIcon,
  ThumbUp as ThumbUpIcon,
  ThumbDown as ThumbDownIcon,
} from "@mui/icons-material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import HelpIcon from "@mui/icons-material/Help";

import { fetchItems, fetchRelatedItems, rateResponse } from "@/utils/api";
import MagnifyingGlassLoader from "../components/Loader";

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
}

const style = {
  position: "absolute" as "absolute",
  top: "50%",
  left: "50%",
  transform: "translate(-50%, -50%)",
  width: 600,
  bgcolor: "background.paper",
  borderRadius: "10px",
  boxShadow: 24,
  p: 4,
};

const ResultsTable: React.FC = () => {
  const [allResults, setAllResults] = useState<TransformedResult[]>([]);
  const [results, setResults] = useState<TransformedResult[]>([]);
  const [open, setOpen] = useState(false);
  const [selectedRow, setSelectedRow] = useState<TransformedResult | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(true);
  const [thumbsUpColour, setThumbsUpColour] = useState({ color: "none" });
  const [thumbsDownColour, setThumbsDownColour] = useState({ color: "none" });
  const router = useRouter();

  useEffect(() => {
    if (!router.isReady) return;

    const fetchData = async () => {
      try {
        const data = await fetchItems("result");

        const queryAnswer = router.query.answer as string | undefined;

        const filteredData = queryAnswer
          ? data.filter((result: Result) => result.answer === queryAnswer)
          : data;

        const transformedResults: TransformedResult[] = await Promise.all(
          filteredData.map(async (result: Result) => {
            const sources: Source[] = await Promise.all(
              result.chunks.map(async (chunk: any) => {
                try {
                  const source = await fetchItems("chunk", chunk.id);
                  return {
                    chunk_id: source?.id || "Unknown ID",
                    fileName: source?.file?.name || "Unknown filename",
                  };
                } catch (error) {
                  return {
                    chunk_id: chunk.id || "Unknown ID",
                    fileName: "Error fetching file name",
                  };
                }
              })
            );

            return {
              Criterion: result.criterion,
              Evidence: result.criterion.evidence,
              Category: result.criterion.category,
              Gate: result.criterion.gate,
              Status: result.answer,
              Justification: result.full_text,
              Sources: sources,
              id: result.id,
              Chunks: result.chunks,
              Project: result.project,
              Ratings: result.ratings,
            };
          })
        );

        transformedResults.sort((a, b) => {
          if (a.Status === "Negative" && b.Status !== "Negative") return -1;
          if (a.Status !== "Negative" && b.Status === "Negative") return 1;
          return 0;
        });

        setAllResults(transformedResults);
        setResults(transformedResults);
      } catch (error) {
        console.error("Error fetching data:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [router.isReady, router.query]);

  const handleCitationClick = (chunk_id: string) => {
    router.push({ pathname: "/file-viewer", query: { citation: chunk_id } });
  };

  const sourcesFormatter = (params: any) => {
    return params.value.map((source: Source) => (
      <Chip
        key={source.chunk_id}
        label={source.fileName}
        onClick={() => handleCitationClick(source.chunk_id)}
        style={{ margin: "2px", cursor: "pointer" }}
      />
    ));
  };

  const statusRenderer = (params: ICellRendererParams) => {
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
  };

  const criterionRenderer = (params: ICellRendererParams) => {
    return params.value.question;
  };

  const columnDefs: ColDef[] = [
    {
      headerName: "Criterion",
      field: "Criterion",
      flex: 5,
      wrapText: true,
      autoHeight: true,
      cellRenderer: criterionRenderer,
    },
    {
      headerName: "Category",
      field: "Category",
      flex: 1,
      filter: "agMultiColumnFilter",
      filterParams: {
        filters: [
          {
            filter: "agTextColumnFilter",
            filterParams: {
              defaultOption: "startsWith",
            },
          },
          {
            filter: "agSetColumnFilter",
          },
        ],
      },
    },
    {
      headerName: "Status",
      field: "Status",
      flex: 1,
      cellRenderer: statusRenderer,
      filter: "agSetColumnFilter",
      filterParams: {
        values: (params: any) => {
          const uniqueValues = Array.from(
            new Set(allResults.map((res) => res.Status))
          );
          params.success(uniqueValues);
        },
        suppressMiniFilter: true,
      },
    },
    {
      headerName: "Sources",
      field: "Sources",
      flex: 3,
      cellRenderer: sourcesFormatter,
      filter: "agSetColumnFilter",
      filterParams: {
        values: (params: any) => {
          const uniqueValues = Array.from(
            allResults.reduce((set, res) => {
              res.Sources.forEach((src) => set.add(src.fileName));
              return set;
            }, new Set<string>())
          );
          params.success(uniqueValues);
        },
        suppressMiniFilter: true,
      },
    },
  ];

  return (
    <div style={{ width: "100%", height: "100vh" }}>
      {isLoading ? (
        <MagnifyingGlassLoader />
      ) : (
        <div
          className="ag-theme-alpine"
          style={{ height: "calc(100% - 64px)", width: "100%" }}
        >
          <AgGridReact
            rowData={results}
            columnDefs={columnDefs}
            defaultColDef={{
              wrapText: true,
              autoHeight: true,
              filter: true,
            }}
            onRowClicked={(e) => setSelectedRow(e.data)}
          />
        </div>
      )}
    </div>
  );
};

export default ResultsTable;
