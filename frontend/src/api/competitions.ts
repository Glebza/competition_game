import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getCompetitions = async (page = 1, search = '') => {
  const response = await api.get('/competitions', {
    params: { page, search },
  });
  return response.data;
};

export const getCompetitionDetail = async (id: string) => {
  const response = await api.get(`/competitions/${id}`);
  return response.data;
};

export const createSession = async (competitionId: string, organizerName: string) => {
  const response = await api.post('/sessions', {
    competition_id: competitionId,
    organizer_name: organizerName,
  });
  return response.data;
};
