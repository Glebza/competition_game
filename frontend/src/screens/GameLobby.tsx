import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Paper,
  Typography,
  Box,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  IconButton,
  Snackbar,
  Alert,
  CircularProgress,
} from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import QrCodeIcon from '@mui/icons-material/QrCode';
import PersonIcon from '@mui/icons-material/Person';
import CrownIcon from '@mui/icons-material/EmojiEvents';
import { getSession, getSessionPlayers, startSession } from '../api/sessions';
import { useWebSocket } from '../hooks/useWebSocket';

interface Player {
  id: string;
  nickname: string;
  is_organizer: boolean;
  joined_at: string;
}

interface SessionInfo {
  id: string;
  code: string;
  competition_name: string;
  status: string;
  organizer_name: string;
  player_count: number;
}

const GameLobby: React.FC = () => {
  const { sessionCode } = useParams<{ sessionCode: string }>();
  const navigate = useNavigate();
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [players, setPlayers] = useState<Player[]>([]);
  const [loading, setLoading] = useState(true);
  const [copySuccess, setCopySuccess] = useState(false);
  const [isOrganizer, setIsOrganizer] = useState(false);
  
  // WebSocket connection
  const { connected, sendMessage } = useWebSocket(sessionCode || '', {
    onPlayerJoined: (data) => {
      // Add new player to the list
      setPlayers(prev => [...prev, data.player]);
    },
    onGameStarted: () => {
      // Navigate to game screen
      navigate(`/game/${sessionCode}`);
    },
  });

  useEffect(() => {
    if (sessionCode) {
      fetchSessionInfo();
      fetchPlayers();
    }
  }, [sessionCode]);

  const fetchSessionInfo = async () => {
    try {
      const data = await getSession(sessionCode!);
      setSession(data);
      // Check if current user is organizer (simplified for now)
      setIsOrganizer(true); // You'd check based on actual user ID
    } catch (error) {
      console.error('Failed to fetch session:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchPlayers = async () => {
    try {
      const data = await getSessionPlayers(sessionCode!);
      setPlayers(data);
    } catch (error) {
      console.error('Failed to fetch players:', error);
    }
  };

  const handleCopyLink = () => {
    const link = `${window.location.origin}/join/${sessionCode}`;
    navigator.clipboard.writeText(link);
    setCopySuccess(true);
  };

  const handleCopyCode = () => {
    navigator.clipboard.writeText(sessionCode || '');
    setCopySuccess(true);
  };

  const handleStartGame = async () => {
    try {
      await startSession(sessionCode!);
      // WebSocket will handle the navigation
    } catch (error) {
      console.error('Failed to start game:', error);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="md" sx={{ mt: 4 }}>
      <Paper sx={{ p: 4 }}>
        <Typography variant="h4" align="center" gutterBottom>
          {session?.competition_name} - Game Lobby
        </Typography>

        <Box sx={{ textAlign: 'center', my: 4 }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            Session Code
          </Typography>
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 1 }}>
            <Typography variant="h2" sx={{ fontFamily: 'monospace', letterSpacing: 2 }}>
              {sessionCode}
            </Typography>
            <IconButton onClick={handleCopyCode} size="small">
              <ContentCopyIcon />
            </IconButton>
          </Box>
        </Box>

        <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', mb: 2 }}>
            <Typography variant="h5">
              Waiting for players...
            </Typography>
          </Box>
          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="h6">
              👥 {players.length}/∞ Players
            </Typography>
          </Box>
        </Paper>

        <Typography variant="h6" gutterBottom>
          Players:
        </Typography>
        <List>
          {players.map((player) => (
            <ListItem key={player.id}>
              <ListItemIcon>
                {player.is_organizer ? (
                  <CrownIcon color="primary" />
                ) : (
                  <PersonIcon />
                )}
              </ListItemIcon>
              <ListItemText
                primary={player.nickname}
                secondary={player.is_organizer ? 'Organizer' : null}
              />
              {connected && (
                <Chip label="✓" size="small" color="success" />
              )}
            </ListItem>
          ))}
        </List>

        <Box sx={{ mt: 4, display: 'flex', gap: 2, justifyContent: 'center' }}>
          <Button
            variant="outlined"
            startIcon={<ContentCopyIcon />}
            onClick={handleCopyLink}
          >
            Copy Link
          </Button>
          <Button
            variant="outlined"
            startIcon={<QrCodeIcon />}
          >
            QR Code
          </Button>
        </Box>

        {isOrganizer && (
          <Box sx={{ mt: 4, textAlign: 'center' }}>
            <Button
              variant="contained"
              size="large"
              onClick={handleStartGame}
              disabled={players.length < 2}
              sx={{ minWidth: 200 }}
            >
              Start Game
            </Button>
            {players.length < 2 && (
              <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                Minimum 2 players required
              </Typography>
            )}
          </Box>
        )}
      </Paper>

      <Snackbar
        open={copySuccess}
        autoHideDuration={2000}
        onClose={() => setCopySuccess(false)}
      >
        <Alert severity="success">Copied to clipboard!</Alert>
      </Snackbar>
    </Container>
  );
};

export default GameLobby;
