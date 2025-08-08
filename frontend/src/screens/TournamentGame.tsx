import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Container,
  Paper,
  Typography,
  Box,
  Card,
  CardMedia,
  CardContent,
  Button,
  LinearProgress,
  Chip,
  Grid,
} from '@mui/material';
import { useWebSocket } from '../hooks/useWebSocket';
import { submitVote } from '../api/voting';
import RoundComplete from '../components/RoundComplete';
import GameComplete from '../components/GameComplete';

interface Item {
  id: string;
  name: string;
  image_url: string;
}

interface CurrentPair {
  round_number: number;
  pair_index: number;
  total_pairs: number;
  item1: Item;
  item2: Item;
}

interface VoteCount {
  [itemId: string]: number;
}

const TournamentGame: React.FC = () => {
  const { sessionCode } = useParams<{ sessionCode: string }>();
  const [currentPair, setCurrentPair] = useState<CurrentPair | null>(null);
  const [voteCounts, setVoteCounts] = useState<VoteCount>({});
  const [totalRounds, setTotalRounds] = useState(5);
  const [hasVoted, setHasVoted] = useState(false);
  const [selectedItem, setSelectedItem] = useState<string | null>(null);
  const [showRoundComplete, setShowRoundComplete] = useState(false);
  const [showGameComplete, setShowGameComplete] = useState(false);
  const [gameResults, setGameResults] = useState<any>(null);

  const { connected, sendMessage } = useWebSocket(sessionCode || '', {
    onNextPair: (data) => {
      setCurrentPair(data);
      setVoteCounts({});
      setHasVoted(false);
      setSelectedItem(null);
      setShowRoundComplete(false);
    },
    onVoteUpdate: (data) => {
      setVoteCounts(data.vote_counts);
    },
    onRoundComplete: (data) => {
      setShowRoundComplete(true);
      // Auto-advance after 3 seconds
      setTimeout(() => {
        setShowRoundComplete(false);
      }, 3000);
    },
    onGameComplete: (data) => {
      setGameResults(data);
      setShowGameComplete(true);
    },
  });

  const handleVote = async (itemId: string) => {
    if (hasVoted || !currentPair) return;

    setSelectedItem(itemId);
    setHasVoted(true);

    try {
      await submitVote(sessionCode!, {
        item_id: itemId,
        round_number: currentPair.round_number,
        pair_index: currentPair.pair_index,
      });
    } catch (error) {
      console.error('Failed to submit vote:', error);
      setHasVoted(false);
      setSelectedItem(null);
    }
  };

  const getVotePercentage = (itemId: string) => {
    const total = Object.values(voteCounts).reduce((sum, count) => sum + count, 0);
    if (total === 0) return 0;
    return Math.round((voteCounts[itemId] || 0) / total * 100);
  };

  if (showGameComplete && gameResults) {
    return <GameComplete results={gameResults} sessionCode={sessionCode!} />;
  }

  if (showRoundComplete) {
    return <RoundComplete />;
  }

  if (!currentPair) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Typography variant="h5">Waiting for game to start...</Typography>
      </Box>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">
            Round {currentPair.round_number} of {totalRounds}
          </Typography>
          <Typography variant="h5" align="center" sx={{ flex: 1 }}>
            Which is better?
          </Typography>
          <Typography variant="h6">
            Pair {currentPair.pair_index + 1}/{currentPair.total_pairs}
          </Typography>
        </Box>
      </Paper>

      <Grid container spacing={4} justifyContent="center">
        <Grid item xs={12} md={5}>
          <Card 
            sx={{ 
              cursor: hasVoted ? 'default' : 'pointer',
              transition: 'all 0.3s',
              transform: selectedItem === currentPair.item1.id ? 'scale(1.05)' : 'scale(1)',
              opacity: hasVoted && selectedItem !== currentPair.item1.id ? 0.7 : 1,
              border: selectedItem === currentPair.item1.id ? '3px solid #3498db' : 'none',
            }}
            onClick={() => handleVote(currentPair.item1.id)}
          >
            <CardMedia
              component="img"
              height="400"
              image={currentPair.item1.image_url}
              alt={currentPair.item1.name}
            />
            <CardContent>
              <Typography variant="h5" align="center" gutterBottom>
                {currentPair.item1.name}
              </Typography>
              
              {Object.keys(voteCounts).length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2">
                      {voteCounts[currentPair.item1.id] || 0} votes
                    </Typography>
                    <Typography variant="body2">
                      {getVotePercentage(currentPair.item1.id)}%
                    </Typography>
                  </Box>
                  <LinearProgress 
                    variant="determinate" 
                    value={getVotePercentage(currentPair.item1.id)}
                    sx={{ height: 10, borderRadius: 5 }}
                  />
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={2} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Typography variant="h3" sx={{ fontWeight: 'bold' }}>
            VS
          </Typography>
        </Grid>

        <Grid item xs={12} md={5}>
          <Card 
            sx={{ 
              cursor: hasVoted ? 'default' : 'pointer',
              transition: 'all 0.3s',
              transform: selectedItem === currentPair.item2.id ? 'scale(1.05)' : 'scale(1)',
              opacity: hasVoted && selectedItem !== currentPair.item2.id ? 0.7 : 1,
              border: selectedItem === currentPair.item2.id ? '3px solid #3498db' : 'none',
            }}
            onClick={() => handleVote(currentPair.item2.id)}
          >
            <CardMedia
              component="img"
              height="400"
              image={currentPair.item2.image_url}
              alt={currentPair.item2.name}
            />
            <CardContent>
              <Typography variant="h5" align="center" gutterBottom>
                {currentPair.item2.name}
              </Typography>
              
              {Object.keys(voteCounts).length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2">
                      {voteCounts[currentPair.item2.id] || 0} votes
                    </Typography>
                    <Typography variant="body2">
                      {getVotePercentage(currentPair.item2.id)}%
                    </Typography>
                  </Box>
                  <LinearProgress 
                    variant="determinate" 
                    value={getVotePercentage(currentPair.item2.id)}
                    sx={{ height: 10, borderRadius: 5 }}
                  />
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Box sx={{ mt: 4, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          {hasVoted ? 'Waiting for other players...' : 'Click on your choice to vote'}
        </Typography>
      </Box>

      {/* Progress indicator */}
      <Box sx={{ mt: 4 }}>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Tournament Progress
        </Typography>
        <LinearProgress 
          variant="determinate" 
          value={(currentPair.pair_index + 1) / currentPair.total_pairs * 100}
          sx={{ height: 8, borderRadius: 4 }}
        />
      </Box>
    </Container>
  );
};

export default TournamentGame;
