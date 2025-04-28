"use client";

import React, { useEffect, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import {
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  Grid,
  Paper,
} from "@mui/material";
import { DateTimePicker } from "@mui/x-date-pickers/DateTimePicker";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import MagnifyingGlassLoader from "../components/Loader";
import styles from "../public/styles/AuditLogs.module.css";
import { useRouter } from "next/router";

interface AuditLog {
  id: string;
  timestamp: string;
  user_id: string;
  action_type: string;
  details: any;
  ip_address: string;
  user_agent: string;
}

const AuditLogsPage: React.FC = () => {
  const router = useRouter();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [startDate, setStartDate] = useState<Date | null>(null);
  const [endDate, setEndDate] = useState<Date | null>(null);
  const [actionType, setActionType] = useState<string>("");
  const [page, setPage] = useState(1);
  const [totalRows, setTotalRows] = useState(0);
  const pageSize = 50;

  const columnDefs = [
    {
      headerName: "Timestamp",
      field: "timestamp",
      sort: "desc",
      flex: 1,
      valueFormatter: (params: any) => {
        return new Date(params.value).toLocaleString();
      },
    },
    {
      headerName: "Action Type",
      field: "action_type",
      flex: 1,
    },
    {
      headerName: "User ID",
      field: "user_id",
      flex: 1,
    },
    {
      headerName: "IP Address",
      field: "ip_address",
      flex: 1,
    },
    {
      headerName: "Details",
      field: "details",
      flex: 2,
      cellRenderer: (params: any) => {
        if (!params.value) return "";
        try {
          return (
            <div style={{ whiteSpace: "pre-wrap" }}>
              {JSON.stringify(params.value, null, 2)}
            </div>
          );
        } catch (e) {
          return String(params.value);
        }
      },
    },
  ];

  const fetchLogs = async () => {
    try {
      setIsLoading(true);
      const queryParams = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });

      if (startDate) {
        queryParams.append("start_date", startDate.toISOString());
      }
      if (endDate) {
        queryParams.append("end_date", endDate.toISOString());
      }
      if (actionType) {
        queryParams.append("action_type", actionType);
      }

      const response = await fetch(`/api/admin/audit-logs?${queryParams}`);
      if (!response.ok) {
        throw new Error("Failed to fetch audit logs");
      }

      const data = await response.json();
      setLogs(data.items);
      setTotalRows(data.total);
    } catch (error) {
      console.error("Error fetching audit logs:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!router.isReady) return;
    fetchLogs();
  }, [router.isReady, page]);

  const handleFilter = () => {
    setPage(1);
    fetchLogs();
  };

  const handleClearFilters = () => {
    setStartDate(null);
    setEndDate(null);
    setActionType("");
    setPage(1);
    fetchLogs();
  };

  return (
    <div className={styles.container}>
      <Paper className={styles.filterSection}>
        <LocalizationProvider dateAdapter={AdapterDateFns}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={3}>
              <DateTimePicker
                label="Start Date"
                value={startDate}
                onChange={(newValue) => setStartDate(newValue)}
                slotProps={{ textField: { fullWidth: true } }}
              />
            </Grid>
            <Grid item xs={12} sm={3}>
              <DateTimePicker
                label="End Date"
                value={endDate}
                onChange={(newValue) => setEndDate(newValue)}
                slotProps={{ textField: { fullWidth: true } }}
              />
            </Grid>
            <Grid item xs={12} sm={2}>
              <FormControl fullWidth>
                <InputLabel>Action Type</InputLabel>
                <Select
                  value={actionType}
                  label="Action Type"
                  onChange={(e) => setActionType(e.target.value)}
                >
                  <MenuItem value="">All</MenuItem>
                  <MenuItem value="llm_query">LLM Query</MenuItem>
                  <MenuItem value="file_upload">File Upload</MenuItem>
                  <MenuItem value="file_delete">File Delete</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Button
                variant="contained"
                color="primary"
                onClick={handleFilter}
                style={{ marginRight: "8px" }}
              >
                Apply Filters
              </Button>
              <Button
                variant="outlined"
                color="secondary"
                onClick={handleClearFilters}
              >
                Clear Filters
              </Button>
            </Grid>
          </Grid>
        </LocalizationProvider>
      </Paper>

      <div className={styles.gridContainer}>
        {isLoading ? (
          <MagnifyingGlassLoader />
        ) : (
          <div className="ag-theme-alpine" style={{ height: "100%" }}>
            <AgGridReact
              rowData={logs}
              columnDefs={columnDefs}
              pagination={true}
              paginationPageSize={pageSize}
              onPaginationChanged={(params) => {
                const currentPage = params.api.paginationGetCurrentPage();
                setPage(currentPage + 1);
              }}
              defaultColDef={{
                sortable: true,
                filter: true,
                resizable: true,
              }}
              rowHeight={100}
              getRowHeight={(params) => {
                // Dynamically set row height based on content
                const detailsHeight = params.data.details
                  ? JSON.stringify(params.data.details, null, 2).split("\n")
                      .length * 20
                  : 0;
                return Math.max(100, detailsHeight);
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default AuditLogsPage;
