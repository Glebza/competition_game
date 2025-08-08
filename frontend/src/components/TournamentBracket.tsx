import React from 'react';
import { Box, Typography } from '@mui/material';

interface TournamentBracketProps {
  bracket: any;
}

const TournamentBracket: React.FC<TournamentBracketProps> = ({ bracket }) => {
  // This is a simplified version - you might want to use a library like react-tournament-bracket
  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="body1" color="text.secondary">
        Tournament bracket visualization would go here
      </Typography>
      <Typography variant="caption" display="block" sx={{ mt: 1 }}>
        Rounds: {bracket.total_rounds}
      </Typography>
    </Box>
  );
};

export default TournamentBracket;
