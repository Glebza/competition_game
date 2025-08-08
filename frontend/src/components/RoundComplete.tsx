import React from 'react';
import {
  Box,
  Typography,
  Paper,
  Fade,
} from '@mui/material';

const RoundComplete: React.FC = () => {
  return (
    <Fade in={true}>
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
        }}
      >
        <Paper sx={{ p: 6, textAlign: 'center' }}>
          <Typography variant="h3" gutterBottom>
            Round Complete! 🎉
          </Typography>
          <Typography variant="h5" color="text.secondary">
            Advancing to next round...
          </Typography>
          <Box sx={{ mt: 4 }}>
            <Typography variant="h1">
              3
            </Typography>
          </Box>
        </Paper>
      </Box>
    </Fade>
  );
};

export default RoundComplete;
