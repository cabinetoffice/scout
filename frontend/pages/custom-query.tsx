"use client"; // This is a client component

import { useState } from "react";
import { Box, TextField, Button, Paper, Typography } from "@mui/material";
import { submitQuery } from "@/utils/api";

const CustomQuery = () => {
  const [messages, setMessages] = useState<{ text: string; isUser: boolean }[]>(
    []
  );
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (input.trim() === "") return;

    const userMessage = { text: input, isUser: true };
    setMessages([...messages, userMessage]);
    setInput("");
    setLoading(true);

    const data = await submitQuery(input);

    const botMessage = { text: data.response, isUser: false };
    setMessages((prevMessages) => [...prevMessages, botMessage]);
    setLoading(false);
  };

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
        {messages.map((msg, index) => (
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
        ))}
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
