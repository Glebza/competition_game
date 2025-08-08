import React from 'react';
import {
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Grid,
  Chip,
  IconButton,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';

interface CompetitionDetailProps {
  competition: any;
  onClose: () => void;
  onStartGame: () => void;
}

const CompetitionDetail: React.FC<CompetitionDetailProps> = ({
  competition,
  onClose,
  onStartGame,
}) => {
  return (
    <>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          {competition.name}
          <IconButton onClick={onClose}>
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ mb: 3 }}>
          <img
            src={competition.image_url || '/placeholder.jpg'}
            alt={competition.name}
            style={{ width: '100%', maxHeight: '300px', objectFit: 'cover' }}
          />
        </Box>
        
        <Typography variant="body1" paragraph>
          {competition.description || 'No description available'}
        </Typography>

        <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
          <Chip label={`${competition.item_count} items`} />
          <Chip label={`${competition.session_count} sessions played`} />
        </Box>

        <Typography variant="h6" gutterBottom>
          Items Preview:
        </Typography>
        <Grid container spacing={1}>
          {/* This would show actual items when we fetch full details */}
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Grid item xs={2} key={i}>
              <Box
                sx={{
                  width: '100%',
                  paddingBottom: '100%',
                  bgcolor: 'grey.300',
                  borderRadius: 1,
                }}
              />
            </Grid>
          ))}
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
        <Button variant="contained" onClick={onStartGame}>
          Start New Game
        </Button>
      </DialogActions>
    </>
  );
};

export default CompetitionDetail;
