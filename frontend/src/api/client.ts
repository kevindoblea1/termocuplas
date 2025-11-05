import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 8000,
});

export const endpoints = {
  state: '/state/',
  config: '/config/',
  events: '/events/',
};
