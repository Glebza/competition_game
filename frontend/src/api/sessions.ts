import { api } from './competitions';

export const getSession = async (sessionCode: string) => {
  const response = await api.get(`/sessions/${sessionCode}`);
  return response.data;
};

export const getSessionPlayers = async (sessionCode: string) => {
  const response = await api.get(`/sessions/${sessionCode}/players`);
  return response.data;
};

export const joinSession = async (sessionCode: string, playerName: string) => {
  const response = await api.post(`/sessions/${sessionCode}/join`, {
    player_name: playerName,
  });
  return response.data;
};

export const startSession = async (sessionCode: string) => {
  const response = await api.post(`/sessions/${sessionCode}/start`);
  return response.data;
};
