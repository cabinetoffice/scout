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
  Tooltip,
  Select,
  FormControl,
  InputLabel,
  SelectChangeEvent
} from "@mui/material";
import { 
  submitQuery, 
  fetchChatHistory, 
  fetchChatSessions, 
  createChatSession, 
  updateChatSession, 
  deleteChatSession,
  fetchLLMModels
} from "@/utils/api";
import ChatIcon from '@mui/icons-material/Chat';
import AddIcon from '@mui/icons-material/Add';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import SettingsIcon from '@mui/icons-material/Settings';
import { ModelSelector } from '@/components/ModelSelector';

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

// Interface for LLM models
interface LLMModel {
  id: string;
  name: string;
  model_id: string;
  description: string | null;
  is_default: boolean;
}

const CustomQuery = () => {
  const [messages, setMessages] = useState<{ text: string; isUser: boolean; timestamp: string }[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [loadingModels, setLoadingModels] = useState(true);
  
  // Session management
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(true);
  
  // Model selection
  const [models, setModels] = useState<LLMModel[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<string>("");
  
  // System prompt settings
  const [systemPrompt, setSystemPrompt] = useState<string>("");
  const [settingsDialogOpen, setSettingsDialogOpen] = useState(false);
  
  // Dialog states
  const [editSessionDialogOpen, setEditSessionDialogOpen] = useState(false);
  const [deleteSessionDialogOpen, setDeleteSessionDialogOpen] = useState(false);
  const [sessionTitle, setSessionTitle] = useState("");
  const [editingSession, setEditingSession] = useState<ChatSession | null>(null);
  
  // Menu state for session actions
  const [menuAnchorEl, setMenuAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedSessionForMenu, setSelectedSessionForMenu] = useState<ChatSession | null>(null);
  
  const [isNewChat, setIsNewChat] = useState(false);

  // Load chat sessions on component mount
  useEffect(() => {
    const loadChatSessions = async () => {
      try {
        setLoadingSessions(true);
        const sessionsData = await fetchChatSessions();
        setSessions(sessionsData || []);

        // If no sessions exist, create a dummy session
        if (!sessionsData || sessionsData.length === 0) {
          const dummySession = {
            id: '00000000-0000-0000-0000-000000000000',
            title: "New Chat",
            created_datetime: new Date().toISOString(),
            updated_datetime: null,
            message_count: 0,
          };

          setSessions([dummySession]);
          setActiveSessionId(dummySession.id);
          console.log("Dummy session created on page load:", dummySession.id);
        }
      } catch (error) {
        console.error('Failed to load chat sessions:', error);
      } finally {
        setLoadingSessions(false);
      }
    };

    loadChatSessions();
  }, []);
  
  // Load available LLM models
  useEffect(() => {
    const loadModels = async () => {
      try {
        setLoadingModels(true);
        const modelsData = await fetchLLMModels();
        setModels(modelsData);
        
        // Set default model
        const defaultModel = modelsData.find((model: LLMModel) => model.is_default);
        if (defaultModel) {
          setSelectedModelId(defaultModel.model_id);
        } else if (modelsData.length > 0) {
          setSelectedModelId(modelsData[0].model_id);
        }
      } catch (error) {
        console.error('Failed to load LLM models:', error);
      } finally {
        setLoadingModels(false);
      }
    };

    loadModels();
  }, []);

  // Set the active session when sessions are loaded
  useEffect(() => {
    // Only set first session as active on initial load if there's no active session
    if (sessions.length > 0 && !activeSessionId && !loadingHistory && !loadingSessions) {
      setActiveSessionId(sessions[0].id);
    }
  }, [sessions, activeSessionId, loadingHistory, loadingSessions]);

  // Load chat history based on active session
  useEffect(() => {
    setMessages([]); // Always clear messages when changing sessions
    setLoadingHistory(true);
    
    if (!activeSessionId) {
      setLoadingHistory(false);
      return;
    }

    const loadChatHistory = async () => {
      try {
        const history = await fetchChatHistory(activeSessionId);
        
        if (history) {
          const formattedMessages = history.map((msg: ChatMessage) => [
            { text: msg.query, isUser: true, timestamp: msg.timestamp },
            { text: msg.response, isUser: false, timestamp: msg.timestamp }
          ]).flat();
          
          setMessages(formattedMessages);
        }
      } catch (error) {
        console.error('Failed to load chat history:', error);
      } finally {
        setLoadingHistory(false);
      }
    };

    if (!isNewChat) {
      loadChatHistory()
    }
    else
    {
      setLoading(false);
      setLoadingSessions(false);
      setLoadingHistory(false);
      setIsNewChat(false);

      const dummySession = {
        id: '00000000-0000-0000-0000-000000000000',
        title: "New Chat",
        created_datetime: new Date().toISOString(),
        updated_datetime: null,
        message_count: 0,
      };

      setSessions([dummySession, ...sessions]);
      console.log("Dummy session created:", dummySession.id);
      setActiveSessionId(dummySession.id);
    }
;
  }, [activeSessionId]);

  // Handle creating a new session
  const handleCreateSession = async () => {
    try {
      // Create a new session without providing a session ID upfront
      // The session ID will be assigned by the backend when a query is made
      const newSession = await createChatSession("New Session");
      setSessions([newSession, ...sessions]);
      setActiveSessionId(newSession.id);
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
      // First submit the query and get a response
      const data = await submitQuery(
        message, 
        activeSessionId ?? undefined, 
        selectedModelId,
        systemPrompt || undefined  // Pass system prompt if it's not empty
      );
      
      // Get the session ID from the response
      const responseSessionId = data.chat_session_id ? 
        data.chat_session_id : 
        (data.body && JSON.parse(data.body).chat_session_id) || null;
      
      // If we don't have an active session but got a session ID from the response, create one
      if (!activeSessionId && responseSessionId) {
        const sessionName = message.length > 30 ? 
          message.substring(0, 30) + "..." : 
          message;
          
        // Create a chat session with the ID from the query response
        const newSession = await createChatSession(sessionName, responseSessionId);
        setActiveSessionId(newSession.id);
        setSessions(prev => [newSession, ...prev]);
      }
      // If we have a new session ID that's different from our active one
      else if (responseSessionId && responseSessionId !== activeSessionId) {
        setActiveSessionId(responseSessionId);
        // Refresh sessions to ensure the new one is included
        const updatedSessions = await fetchChatSessions();
        setSessions(updatedSessions);
      }

      const botMessage = { 
        text: data.response || (data.body ? JSON.parse(data.body).response : "No response"), 
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
  
  // Handle model selection change
  const handleModelChange = (event: SelectChangeEvent) => {
    setSelectedModelId(event.target.value);
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
        onClick={() => { // Changed from async, no direct API call here anymore
          // Check if a "New Chat" session with 0 messages already exists
          // This can be useful if the user clicks "New Chat" multiple times
          // without sending a message in an already visually prepared "New Chat".
          const existingEmptyNewChatSession = sessions.find(
            (session) => session.title === "New Chat" && session.message_count === 0
          );

          if (existingEmptyNewChatSession) {
            // If such a session exists (perhaps from a previous click where no message was sent),
            // set it as the active session.
            setActiveSessionId(existingEmptyNewChatSession.id);
          } else {
            // If no such empty "New Chat" session exists,
            // set activeSessionId to null. This signals to handleSendMessage
            // that the next message will initiate a brand new session,
            // whose ID will come from the submitQuery response.
            setActiveSessionId(null);
          }
          setIsNewChat(true);
          setMessages([]); // Clear messages from any previous session
          setInput("");   // Clear any typed input
          // The actual ChatSession object will be created in handleSendMessage
          // after the first message is sent and a session ID is received from the backend.
        }}
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

        {/* Model Selector */}
        <ModelSelector 
          models={models}
          selectedModelId={selectedModelId}
          handleModelChange={handleModelChange}
          loading={loading}
          loadingModels={loadingModels}
        />

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
          <IconButton 
            onClick={() => setSettingsDialogOpen(true)}
            disabled={loading}
            sx={{ mr: 1 }}
            title="System Prompt Settings"
          >
            <SettingsIcon />
          </IconButton>
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

      {/* System Prompt Settings Dialog */}
      <Dialog 
        open={settingsDialogOpen} 
        onClose={() => setSettingsDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>System Prompt Settings</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
            Configure a custom system prompt that will be sent with your queries to provide context and instructions to the AI model.
          </Typography>
          <TextField
            autoFocus
            margin="dense"
            label="System Prompt"
            fullWidth
            multiline
            rows={6}
            variant="outlined"
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            placeholder="Enter your custom system prompt here..."
            helperText="This prompt will be included with all your queries in this session. Leave empty to use the default system behavior."
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSettingsDialogOpen(false)}>Cancel</Button>
          <Button 
            onClick={() => {
              setSettingsDialogOpen(false);
            }}
            variant="contained"
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CustomQuery;
