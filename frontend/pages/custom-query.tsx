"use client";

import { useCallback, useEffect, useState } from "react";
import { Box, TextField, Button, Paper, Typography, CircularProgress } from "@mui/material";
import { submitQuery, fetchChatHistory } from "@/utils/api";

const CustomQuery = () => {
  const [messages, setMessages] = useState<{ text: string; isUser: boolean }[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);

  // Load chat history
  useEffect(() => {
    const loadChatHistory = async () => {
      try {
        const history = await fetchChatHistory();
        const formattedHistory = history.flatMap((entry: any) => [
          { text: entry.query, isUser: true },
          { text: entry.response, isUser: false }
        ]);
        setMessages(formattedHistory);
      } catch (error) {
        console.error('Failed to load chat history:', error);
      } finally {
        setLoadingHistory(false);
      }
    };

    loadChatHistory();
  }, []);

  const handleSendMessage = async (message: string) => {
    const userMessage = { text: message, isUser: true };
    setMessages((prevMessages) => [...prevMessages, userMessage]);
    setLoading(true);

    const data = await submitQuery(message);
    const botMessage = { text: JSON.parse(data.body).response, isUser: false };
    setMessages((prevMessages) => [...prevMessages, botMessage]);
    setLoading(false);
  };

  const sendMessage = () => {
    if (input.trim() === "") return;
    handleSendMessage(input);
    setInput("");
  };

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const query = urlParams.get("query");
    if (query) {
      handleSendMessage(query);
    }
  }, []);

  return (
    <Box sx={{ p: 2 }}>
      <Paper
        sx={{
          height: "400px",
          overflowY: "scroll",
          border: "1px solid #ccc",
          p: 2,
          mb: 2,
        }}
        ref={(el) => {
          if (el) {
            el.scrollTop = el.scrollHeight;
          }
        }}
      >
        {loadingHistory ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
            <CircularProgress size={24} />
          </Box>
        ) : (
          messages.map((msg, index) => (
            <Box
              key={index}
              sx={{
                textAlign: msg.isUser ? "right" : "left",
                mb: 1,
              }}
            >
              <Typography
                sx={{
                  backgroundColor: msg.isUser ? "#DCF8C6" : "#FFF",
                  display: "inline-block",
                  p: 1,
                  borderRadius: 1,
                }}
              >
                {msg.text}
              </Typography>
            </Box>
          ))
        )}
        {loading && (
          <Box sx={{ textAlign: "right", mb: 1 }}>
            <Typography
              sx={{
                backgroundColor: "#FFF",
                display: "inline-block",
                p: 1,
                borderRadius: 1,
              }}
            >
              <span className="dot-flashing"></span>
            </Typography>
          </Box>
        )}
      </Paper>
      <Box sx={{ display: "flex", alignItems: "center" }}>
        <TextField
          fullWidth
          variant="outlined"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          sx={{ mr: 1 }}
        />
        <Button variant="contained" onClick={sendMessage} disabled={loading}>
          Send
        </Button>
      </Box>
    </Box>
  );
};

export default CustomQuery;
