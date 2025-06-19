import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { apiConfigManager } from './apiConfig';

class APIClient {
  private static instance: APIClient;
  private client: AxiosInstance;

  private constructor() {
    this.client = this.createClient();
  }

  static getInstance(): APIClient {
    if (!APIClient.instance) {
      APIClient.instance = new APIClient();
    }
    return APIClient.instance;
  }

  private createClient(): AxiosInstance {
    const config = apiConfigManager.getActiveConfig();
    const baseURL = config?.baseUrl || process.env.NEXT_PUBLIC_DEFAULT_API_URL;

    return axios.create({
      baseURL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  public updateClient() {
    this.client = this.createClient();
  }

  public async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return this.client.get(url, config);
  }

  public async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return this.client.post(url, data, config);
  }

  public async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return this.client.put(url, data, config);
  }

  public async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return this.client.delete(url, config);
  }
}

export const apiClient = APIClient.getInstance(); 