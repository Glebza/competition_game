import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  CircularProgress,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { createSession } from '../api/competitions';

interface CreateSessionDialogProps {
  open: boolean;
  onClose: () => void;
  competition: any;
}

const CreateSessionDialog: React.FC<CreateSessionDialogProps> = ({
  open,
  onClose,
  competition,
}) => {
  const navigate = useNavigate();
  const [organizerName, setOrganizerName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleCreate = async () => {
    if (!organizerName.trim()) {
      setError('Please enter your name');
      return;
    }

    try {
      setLoading(true);
      setError('');
      const response = await createSession(competition.id, organizerName);
      navigate(`/lobby/${response.code}`);
    } catch (err) {
      setError('Failed to create session. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Start New Game - {competition?.name}</DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 2 }}>
          <TextField
            fullWidth
            label="Your Name"
            value={organizerName}
            onChange={(e) => setOrganizerName(e.target.value)}
            error={!!error}
            helperText={error}
            disabled={loading}
            autoFocus
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleCreate();
              }
            }}
          />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            You'll be the organizer of this game session. You can share the game code with others to join.
          </Typography>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleCreate}
          disabled={loading || !organizerName.trim()}
        >
          {loading ? <CircularProgress size={24} /> : 'Create Game'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default CreateSessionDialog;
