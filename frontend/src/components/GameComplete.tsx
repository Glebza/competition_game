import React from 'react';
import {
  Container,
  Paper,
  Typography,
  Box,
  Button,
  Card,
  CardMedia,
  CardContent,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import TournamentBracket from './TournamentBracket';

interface GameCompleteProps {
  results: {
    winner: {
      id: string;
      name: string;
      image_url: string;
    };
    total_rounds: number;
    total_votes: number;
    duration_seconds: number;
    bracket: any;
  };
  sessionCode: string;
}

const GameComplete: React.FC<GameCompleteProps> = ({ results, sessionCode }) => {
  const navigate = useNavigate();

  const formatDuration = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h2" gutterBottom>
          🏆 Tournament Complete! 🏆
        </Typography>

        <Box sx={{ mt: 4, mb: 4 }}>
          <Typography variant="h4" gutterBottom>
            WINNER
          </Typography>
          <Card sx={{ maxWidth: 400, mx: 'auto', mt: 2 }}>
            <CardMedia
              component="img"
              height="300"
              image={results.winner.image_url}
              alt={results.winner.name}
            />
            <CardContent>
              <Typography variant="h4">
                {results.winner.name}
              </Typography>
            </CardContent>
          </Card>
        </Box>

        <Box sx={{ mt: 4, mb: 4 }}>
          <Typography variant="h5" gutterBottom>
            Tournament Statistics
          </Typography>
          <Box sx={{ display: 'flex', justifyContent: 'center', gap: 4, mt: 2 }}>
            <Box>
              <Typography variant="h6">{results.total_votes}</Typography>
              <Typography variant="body2" color="text.secondary">Total Votes</Typography>
            </Box>
            <Box>
              <Typography variant="h6">{results.total_rounds}</Typography>
              <Typography variant="body2" color="text.secondary">Rounds</Typography>
            </Box>
            <Box>
              <Typography variant="h6">{formatDuration(results.duration_seconds)}</Typography>
              <Typography variant="body2" color="text.secondary">Duration</Typography>
            </Box>
          </Box>
        </Box>

        <Box sx={{ mt: 4 }}>
          <Typography variant="h5" gutterBottom>
            Tournament Bracket
          </Typography>
          <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
            <TournamentBracket bracket={results.bracket} />
          </Paper>
        </Box>

        <Box sx={{ mt: 4, display: 'flex', justifyContent: 'center', gap: 2 }}>
          <Button variant="outlined" onClick={() => navigator.clipboard.writeText(window.location.href)}>
            Share Results
          </Button>
          <Button variant="outlined">
            Download Bracket
          </Button>
          <Button variant="contained" onClick={() => navigate('/')}>
            Play Another Game
          </Button>
        </Box>
      </Paper>
    </Container>
  );
};

export default GameComplete;
