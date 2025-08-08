import { api } from './competitions';

export const submitVote = async (sessionCode: string, voteData: {
  item_id: string;
  round_number: number;
  pair_index: number;
}) => {
  const response = await api.post(`/sessions/${sessionCode}/vote`, voteData);
  return response.data;
};
