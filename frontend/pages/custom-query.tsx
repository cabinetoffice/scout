"use client";

import { useCallback, useEffect, useState } from "react";
import { 
  Box, 
  TextField, 
  Button, 
  Paper, 
  Typography, 
  CircularProgress,
  Drawer,
  List,
  ListItem,
  ListItemText,
  ListItemButton,
  ListItemIcon,
  IconButton,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Menu,
  MenuItem,
  Tooltip
} from "@mui/material";
import { 
  submitQuery, 
  fetchChatHistory, 
  fetchChatSessions, 
  createChatSession, 
  updateChatSession, 
  deleteChatSession 
} from "@/utils/api";
import ChatIcon from '@mui/icons-material/Chat';
import AddIcon from '@mui/icons-material/Add';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';

// Interface for chat sessions
interface ChatSession {
  id: string;
  title: string;
  created_datetime: string;
  updated_datetime: string | null;
  message_count: number;
}

// Interface for chat messages
interface ChatMessage {
  id: string;
  query: string;
  response: string;
  timestamp: string;
  session_id: string | null;
}

const CustomQuery = () => {
  const [messages, setMessages] = useState<{ text: string; isUser: boolean; timestamp: string }[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [loadingSessions, setLoadingSessions] = useState(true);
  
  // Session management
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(true);
  
  // Dialog states
  const [newSessionDialogOpen, setNewSessionDialogOpen] = useState(false);
  const [editSessionDialogOpen, setEditSessionDialogOpen] = useState(false);
  const [deleteSessionDialogOpen, setDeleteSessionDialogOpen] = useState(false);
  const [sessionTitle, setSessionTitle] = useState("");
  const [editingSession, setEditingSession] = useState<ChatSession | null>(null);
  
  // Menu state for session actions
  const [menuAnchorEl, setMenuAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedSessionForMenu, setSelectedSessionForMenu] = useState<ChatSession | null>(null);

  // Load chat sessions on component mount
  useEffect(() => {
    const loadChatSessions = async () => {
      try {
        setLoadingSessions(true);
        const sessionsData = await fetchChatSessions();
        setSessions(sessionsData || []);
      } catch (error) {
        console.error('Failed to load chat sessions:', error);
      } finally {
        setLoadingSessions(false);
      }
    };

    loadChatSessions();
  }, []);

  // Set the active session when sessions are loaded
  useEffect(() => {
    if (!activeSessionId && sessions.length > 0) {
      setActiveSessionId(sessions[0].id);
    }
  }, [sessions, activeSessionId]);

  // Load chat history based on active session
  useEffect(() => {
    const loadChatHistory = async () => {
      try {
        setLoadingHistory(true);
        const history = await fetchChatHistory(activeSessionId || undefined);
        
        if (history) {
          const formattedMessages = history.map((msg: ChatMessage) => [
            { text: msg.query, isUser: true, timestamp: msg.timestamp },
            { text: msg.response, isUser: false, timestamp: msg.timestamp }
          ]).flat();
          
          setMessages(formattedMessages);
        } else {
          setMessages([]);
        }
      } catch (error) {
        console.error('Failed to load chat history:', error);
      } finally {
        setLoadingHistory(false);
      }
    };

    loadChatHistory();
  }, [activeSessionId]);

  // Handle creating a new session
  const handleCreateSession = async () => {
    if (!sessionTitle.trim()) return;
    
    try {
      const newSession = await createChatSession(sessionTitle);
      setSessions([newSession, ...sessions]);
      setActiveSessionId(newSession.id);
      setNewSessionDialogOpen(false);
      setSessionTitle("");
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  };

  // Handle updating a session
  const handleUpdateSession = async () => {
    if (!editingSession || !sessionTitle.trim()) return;
    
    try {
      const updatedSession = await updateChatSession(editingSession.id, sessionTitle);
      setSessions(sessions.map(session => 
        session.id === updatedSession.id ? updatedSession : session
      ));
      setEditSessionDialogOpen(false);
      setSessionTitle("");
      setEditingSession(null);
    } catch (error) {
      console.error('Failed to update session:', error);
    }
  };

  // Handle deleting a session
  const handleDeleteSession = async () => {
    if (!editingSession) return;
    
    try {
      await deleteChatSession(editingSession.id);
      setSessions(sessions.filter(session => session.id !== editingSession.id));
      
      if (activeSessionId === editingSession.id) {
        setActiveSessionId(sessions.length > 1 ? 
          sessions.find(s => s.id !== editingSession.id)?.id || null : null);
      }
      
      setDeleteSessionDialogOpen(false);
      setEditingSession(null);
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  // Handle sending a message
  const handleSendMessage = async (message: string) => {
    const timestamp = new Date().toISOString();
    const userMessage = { text: message, isUser: true, timestamp };
    setMessages((prevMessages) => [...prevMessages, userMessage]);
    setLoading(true);

    try {
      // Create a new session if none is active
      if (!activeSessionId) {
        const sessionName = message.length > 30 ? 
          message.substring(0, 30) + "..." : 
          message;
          
        const newSession = await createChatSession(sessionName);
        setActiveSessionId(newSession.id);
        setSessions(prev => [newSession, ...prev]);
      }

      const data = await submitQuery(message);
      const botMessage = { 
        text: JSON.parse(data.body).response, 
        isUser: false, 
        timestamp: new Date().toISOString() 
      };
      setMessages((prevMessages) => [...prevMessages, botMessage]);

      // Refresh sessions to get updated message counts
      const updatedSessions = await fetchChatSessions();
      setSessions(updatedSessions);
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = () => {
    if (input.trim() === "") return;
    handleSendMessage(input);
    setInput("");
  };

  // Handle opening the session menu
  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, session: ChatSession) => {
    setMenuAnchorEl(event.currentTarget);
    setSelectedSessionForMenu(session);
  };

  // Handle closing the session menu
  const handleMenuClose = () => {
    setMenuAnchorEl(null);
    setSelectedSessionForMenu(null);
  };

  // Handle edit option from menu
  const handleEditFromMenu = () => {
    if (selectedSessionForMenu) {
      setEditingSession(selectedSessionForMenu);
      setSessionTitle(selectedSessionForMenu.title);
      setEditSessionDialogOpen(true);
    }
    handleMenuClose();
  };

  // Handle delete option from menu
  const handleDeleteFromMenu = () => {
    if (selectedSessionForMenu) {
      setEditingSession(selectedSessionForMenu);
      setDeleteSessionDialogOpen(true);
    }
    handleMenuClose();
  };

  // Load query from URL if present
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const query = urlParams.get("query");
    if (query) {
      handleSendMessage(query);
    }
  }, []);

  const drawerWidth = 240;

  return (
    <Box sx={{ display: "flex", height: "calc(100vh - 150px)" }}>
      {/* Sessions Drawer */}
      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          [`& .MuiDrawer-paper`]: { 
            width: drawerWidth, 
            boxSizing: 'border-box',
            position: 'relative',
            height: '100%',
            border: '1px solid rgba(0, 0, 0, 0.12)'
          },
        }}
        open={drawerOpen}
      >
        <Box sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between', 
          p: 2,
          borderBottom: '1px solid rgba(0, 0, 0, 0.12)'
        }}>
          <Typography variant="h6">Chat Sessions</Typography>
          <IconButton 
            onClick={() => setNewSessionDialogOpen(true)}
            color="primary"
          >
            <AddIcon />
          </IconButton>
        </Box>
        
        {loadingSessions ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
            <CircularProgress size={24} />
          </Box>
        ) : (
          <List sx={{ overflow: 'auto', flexGrow: 1 }}>
            {sessions.length === 0 ? (
              <ListItem>
                <ListItemText 
                  primary="No sessions yet"
                  secondary="Start a chat or create a new session"
                />
              </ListItem>
            ) : (
              sessions.map((session) => (
                <ListItem 
                  key={session.id} 
                  disablePadding
                  secondaryAction={
                    <IconButton 
                      edge="end" 
                      onClick={(e) => handleMenuOpen(e, session)}
                    >
                      <MoreVertIcon />
                    </IconButton>
                  }
                >
                  <ListItemButton
                    selected={activeSessionId === session.id}
                    onClick={() => setActiveSessionId(session.id)}
                  >
                    <ListItemIcon>
                      <ChatIcon />
                    </ListItemIcon>
                    <ListItemText 
                      primary={session.title} 
                      secondary={`${session.message_count} message${session.message_count === 1 ? '' : 's'}`}
                      primaryTypographyProps={{
                        noWrap: true,
                        title: session.title
                      }}
                    />
                  </ListItemButton>
                </ListItem>
              ))
            )}
          </List>
        )}
      </Drawer>

      {/* Main Chat Area */}
      <Box sx={{ flexGrow: 1, p: 2, display: 'flex', flexDirection: 'column', height: '100%' }}>
        {/* Chat Messages */}
        <Paper
          sx={{
            flexGrow: 1,
            overflowY: "scroll",
            border: "1px solid #ccc",
            p: 2,
            mb: 2,
            display: 'flex',
            flexDirection: 'column',
          }}
          ref={(el) => {
            if (el) {
              el.scrollTop = el.scrollHeight;
            }
          }}
        >
          {loadingHistory ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
              <CircularProgress />
            </Box>
          ) : messages.length === 0 ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
              <Typography color="textSecondary">
                No messages yet. Start a new conversation!
              </Typography>
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
                    p: 2,
                    borderRadius: 2,
                    maxWidth: '80%',
                    boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
                    wordBreak: 'break-word'
                  }}
                >
                  {msg.text}
                </Typography>
                <Typography variant="caption" sx={{ display: 'block', mt: 0.5, color: 'text.secondary' }}>
                  {new Date(msg.timestamp).toLocaleTimeString()} • {new Date(msg.timestamp).toLocaleDateString()}
                </Typography>
              </Box>
            ))
          )}
          {loading && (
            <Box sx={{ textAlign: "left", mb: 1 }}>
              <Typography
                sx={{
                  backgroundColor: "#FFF",
                  display: "inline-block",
                  p: 2,
                  borderRadius: 2,
                }}
              >
                <span className="dot-flashing"></span>
              </Typography>
            </Box>
          )}
        </Paper>

        {/* Input Area */}
        <Box sx={{ display: "flex", alignItems: "center" }}>
          <TextField
            fullWidth
            variant="outlined"
            placeholder="Type your message here..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
            multiline
            maxRows={4}
            sx={{ mr: 1 }}
          />
          <Button 
            variant="contained" 
            onClick={sendMessage} 
            disabled={loading || input.trim() === ""}
          >
            Send
          </Button>
        </Box>
      </Box>

      {/* Session Menu */}
      <Menu
        anchorEl={menuAnchorEl}
        open={Boolean(menuAnchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleEditFromMenu}>
          <ListItemIcon>
            <EditIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Rename</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleDeleteFromMenu}>
          <ListItemIcon>
            <DeleteIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Delete</ListItemText>
        </MenuItem>
      </Menu>

      {/* New Session Dialog */}
      <Dialog open={newSessionDialogOpen} onClose={() => setNewSessionDialogOpen(false)}>
        <DialogTitle>New Chat Session</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Session Name"
            fullWidth
            variant="outlined"
            value={sessionTitle}
            onChange={(e) => setSessionTitle(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setNewSessionDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreateSession} disabled={!sessionTitle.trim()}>Create</Button>
        </DialogActions>
      </Dialog>

      {/* Edit Session Dialog */}
      <Dialog open={editSessionDialogOpen} onClose={() => setEditSessionDialogOpen(false)}>
        <DialogTitle>Rename Session</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Session Name"
            fullWidth
            variant="outlined"
            value={sessionTitle}
            onChange={(e) => setSessionTitle(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditSessionDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleUpdateSession} disabled={!sessionTitle.trim()}>Save</Button>
        </DialogActions>
      </Dialog>

      {/* Delete Session Dialog */}
      <Dialog open={deleteSessionDialogOpen} onClose={() => setDeleteSessionDialogOpen(false)}>
        <DialogTitle>Delete Session</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete this session? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteSessionDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleDeleteSession} color="error">Delete</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CustomQuery;
