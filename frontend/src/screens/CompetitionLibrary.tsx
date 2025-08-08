import React, { useState, useEffect } from 'react';
import {
  Container,
  Grid,
  Card,
  CardMedia,
  CardContent,
  Typography,
  TextField,
  Button,
  Box,
  AppBar,
  Toolbar,
  InputAdornment,
  IconButton,
  Dialog,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import AddIcon from '@mui/icons-material/Add';
import { getCompetitions } from '../api/competitions';
import CompetitionDetail from '../components/CompetitionDetail';
import CreateSessionDialog from '../components/CreateSessionDialog';

interface Competition {
  id: string;
  name: string;
  description: string;
  item_count: number;
  session_count: number;
  image_url?: string;
}

const CompetitionLibrary: React.FC = () => {
  const [competitions, setCompetitions] = useState<Competition[]>([]);
  const [search, setSearch] = useState('');
  const [selectedCompetition, setSelectedCompetition] = useState<Competition | null>(null);
  const [createSessionOpen, setCreateSessionOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCompetitions();
  }, []);

  const fetchCompetitions = async () => {
    try {
      setLoading(true);
      const response = await getCompetitions();
      setCompetitions(response.items);
    } catch (error) {
      console.error('Failed to fetch competitions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(event.target.value);
    // TODO: Implement search API call with debounce
  };

  const handleCompetitionClick = (competition: Competition) => {
    setSelectedCompetition(competition);
  };

  const handleStartGame = () => {
    if (selectedCompetition) {
      setCreateSessionOpen(true);
    }
  };

  return (
    <>
      <AppBar position="static" elevation={0}>
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            🏆 Tournament Game
          </Typography>
          <Button color="inherit" startIcon={<AddIcon />}>
            Create Competition
          </Button>
          <Button color="inherit">
            Join Game
          </Button>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Box sx={{ mb: 4 }}>
          <TextField
            fullWidth
            variant="outlined"
            placeholder="Search competitions..."
            value={search}
            onChange={handleSearch}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
          />
        </Box>

        <Grid container spacing={3}>
          {competitions.map((competition) => (
            <Grid item xs={12} sm={6} md={4} key={competition.id}>
              <Card 
                sx={{ 
                  cursor: 'pointer',
                  transition: 'transform 0.2s',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: 3,
                  }
                }}
                onClick={() => handleCompetitionClick(competition)}
              >
                <CardMedia
                  component="img"
                  height="200"
                  image={competition.image_url || '/placeholder.jpg'}
                  alt={competition.name}
                />
                <CardContent>
                  <Typography gutterBottom variant="h6" component="div">
                    {competition.name}
                  </Typography>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2 }}>
                    <Typography variant="body2" color="text.secondary">
                      {competition.item_count} items
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {competition.session_count} sessions
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

        {competitions.length === 0 && !loading && (
          <Box sx={{ textAlign: 'center', mt: 8 }}>
            <Typography variant="h6" color="text.secondary">
              No competitions found
            </Typography>
          </Box>
        )}
      </Container>

      {/* Competition Detail Dialog */}
      <Dialog
        open={!!selectedCompetition}
        onClose={() => setSelectedCompetition(null)}
        maxWidth="md"
        fullWidth
      >
        {selectedCompetition && (
          <CompetitionDetail
            competition={selectedCompetition}
            onClose={() => setSelectedCompetition(null)}
            onStartGame={handleStartGame}
          />
        )}
      </Dialog>

      {/* Create Session Dialog */}
      <CreateSessionDialog
        open={createSessionOpen}
        onClose={() => setCreateSessionOpen(false)}
        competition={selectedCompetition}
      />
    </>
  );
};

export default CompetitionLibrary;
