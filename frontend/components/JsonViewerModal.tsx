import React from "react";
import { Modal, Box, Typography, Tabs, Tab } from "@mui/material";
import { AuditLog } from "../types/audit";

interface JsonViewerModalProps {
  open: boolean;
  onClose: () => void;
  data: AuditLog | null;
}

const JsonViewerModal: React.FC<JsonViewerModalProps> = ({
  open,
  onClose,
  data,
}) => {
  const [activeTab, setActiveTab] = React.useState(0);

  if (!data) return null;

  const formatValue = (value: any): string => {
    if (typeof value === "object" && value !== null) {
      return JSON.stringify(value, null, 2);
    }
    return String(value);
  };

  const renderKeyValuePairs = (obj: Record<string, any>) => {
    return Object.entries(obj).map(([key, value]) => (
      <Box key={key} sx={{ mb: 2 }}>
        <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 0.5 }}>
          {key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, " ")}:
        </Typography>
        <Box
          sx={{
            backgroundColor: "#f5f5f5",
            p: 1,
            borderRadius: 1,
            fontFamily: "monospace",
            fontSize: "0.875rem",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          }}
        >
          {formatValue(value)}
        </Box>
      </Box>
    ));
  };

  return (
    <Modal open={open} onClose={onClose} aria-labelledby="audit-log-modal">
      <Box
        sx={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width: "80%",
          maxWidth: "1000px",
          maxHeight: "80vh",
          bgcolor: "background.paper",
          boxShadow: 24,
          p: 4,
          borderRadius: 1,
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <Typography variant="h6" component="h2" gutterBottom>
          Audit Log Details
        </Typography>

        <Tabs
          value={activeTab}
          onChange={(_, newValue) => setActiveTab(newValue)}
          sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}
        >
          <Tab label="Formatted View" />
          <Tab label="Raw JSON" />
        </Tabs>

        <Box sx={{ overflow: "auto", flex: 1 }}>
          {activeTab === 0 ? (
            <Box sx={{ p: 1 }}>{renderKeyValuePairs(data)}</Box>
          ) : (
            <pre
              style={{
                margin: 0,
                padding: "1rem",
                backgroundColor: "#f5f5f5",
                borderRadius: "4px",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                fontFamily: "monospace",
                fontSize: "0.875rem",
              }}
            >
              {JSON.stringify(data, null, 2)}
            </pre>
          )}
        </Box>
      </Box>
    </Modal>
  );
};

export default JsonViewerModal;
