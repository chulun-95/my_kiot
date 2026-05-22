import { http, HttpResponse } from 'msw';

export const handlers = [
  http.post('*/auth/refresh', () => HttpResponse.json({ access_token: 'mock-access-token' })),
];
