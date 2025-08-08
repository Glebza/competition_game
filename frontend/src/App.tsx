import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import CompetitionLibrary from './screens/CompetitionLibrary';
import GameLobby from './screens/GameLobby';
import TournamentGame from './screens/TournamentGame';

const theme = createTheme({
  palette: {
    primary: {
      main: '#3498db',
    },
    secondary: {
      main: '#2c3e50',
    },
    background: {
      default: '#f5f5f5',
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Routes>
          <Route path="/" element={<CompetitionLibrary />} />
          <Route path="/lobby/:sessionCode" element={<GameLobby />} />
          <Route path="/game/:sessionCode" element={<TournamentGame />} />
        </Routes>
      </Router>
    </ThemeProvider>
  );
}

export default App;
