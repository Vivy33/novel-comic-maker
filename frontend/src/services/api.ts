import axios, { AxiosInstance, AxiosResponse } from 'axios';

// API响应基础接口
export interface ApiResponse<T = any> {
  data: T;
  message?: string;
  success: boolean;
}

// API错误接口
export interface ApiError {
  message: string;
  status: number;
  details?: any;
}

// 项目接口
export interface Project {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
  status: 'created' | 'in_progress' | 'completed' | 'error';
  metadata?: Record<string, any>;
  primary_cover?: {
    cover_id: string;
    thumbnail_url: string;
    title?: string;
  };
}

// 角色接口
export interface Character {
  id: string;
  project_id: string;
  name: string;
  description?: string;
  image_url?: string;
  traits: string[];
  created_at: string;
  updated_at: string;
}

// 漫画接口
export interface Comic {
  id: string;
  project_id: string;
  title: string;
  summary?: string;
  status: 'creating' | 'generating' | 'completed' | 'error';
  created_at: string;
  updated_at: string;
  pages?: ComicPage[];
  cover_image_url?: string;
}

// 漫画页面接口
export interface ComicPage {
  id: string;
  comic_id: string;
  page_number: number;
  scene: string;
  image_url: string;
  panel_description: string;
  created_at: string;
}

// 小说文件接口
export interface NovelFile {
  filename: string;
  title: string;
  size: number;
  created_at: number;
  modified_at: number;
  is_primary: boolean;
}

// 小说内容接口
export interface NovelContent {
  filename: string;
  title: string;
  content: string;
  size: number;
  created_at: number;
  modified_at: number;
  is_primary: boolean;
}

// 文本分析接口
export interface TextAnalysis {
  summary: string;
  key_points: string[];
  sentiment: 'positive' | 'negative' | 'neutral';
  entities: Array<{
    name: string;
    type: string;
    description: string;
  }>;
}

// 脚本生成接口
export interface ScriptGeneration {
  scenes: Array<{
    scene_number: number;
    setting: string;
    characters: string[];
    dialogue: string;
    action?: string;
    estimated_time?: string;
  }>;
  total_scenes: number;
  estimated_duration: string;
}

// 工作流状态接口
export interface WorkflowStatus {
  id: string;
  workflow_id?: string; // 添加workflow_id字段以兼容后端返回
  project_id: string;
  workflow_type: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  current_step?: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  result?: any;
}

// 文生图请求接口
export interface TextToImageRequest {
  prompt: string;
  model?: string;
  size?: string;
  quality?: string;
  style?: string;
}

// 图生图请求接口
export interface ImageToImageRequest {
  prompt: string;
  image_url: string;
  model?: string;
  size?: string;
}

class ApiClient {
  private client: AxiosInstance;
  private retryConfig = {
    retries: 3,
    retryDelay: 1000,
    retryCondition: (error: any) => {
      // 只重试网络错误和5xx错误
      return !error.response || (error.response.status >= 500 && error.response.status < 600);
    }
  };

  constructor() {
    this.client = axios.create({
      baseURL: '', // 使用相对路径，通过React代理转发到后端
      timeout: 60000, // 60秒超时
      // 不设置默认Content-Type，让axios根据请求类型自动设置
    });

    // 请求拦截器
    this.client.interceptors.request.use(
      (config) => {
        // 可以在这里添加认证token等
        console.log(`API请求: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // 响应拦截器
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        console.log(`API响应: ${response.config.method?.toUpperCase()} ${response.config.url} - ${response.status}`);
        return response;
      },
      (error) => {
        const apiError: ApiError = {
          message: error.response?.data?.message || error.message || '未知错误',
          status: error.response?.status || 0,
          details: error.response?.data,
        };
        console.error('API错误:', apiError);
        return Promise.reject(apiError);
      }
    );
  }

  // 通用请求方法
  private async request<T>(
    method: 'GET' | 'POST' | 'PUT' | 'DELETE',
    url: string,
    data?: any
  ): Promise<T> {
    try {
      const response = await this.client.request({
        method,
        url,
        data,
      });
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  // GET请求
  async get<T>(url: string): Promise<T> {
    return this.request<T>('GET', url);
  }

  // POST请求
  async post<T>(url: string, data?: any): Promise<T> {
    return this.request<T>('POST', url, data);
  }

  // PUT请求
  async put<T>(url: string, data?: any): Promise<T> {
    return this.request<T>('PUT', url, data);
  }

  // DELETE请求
  async delete<T>(url: string): Promise<T> {
    return this.request<T>('DELETE', url);
  }

  // 文件上传
  async uploadFile<T>(url: string, file: File, onProgress?: (progress: number) => void): Promise<T> {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await this.client.post(url, formData, {
        // 不要手动设置Content-Type，让浏览器自动设置multipart/form-data边界
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            onProgress(progress);
          }
        },
      });
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  // 获取底层axios客户端实例（用于高级用法）
  get httpClient() {
    return this.client;
  }
}

// 创建API客户端实例
export const apiClient = new ApiClient();

export default apiClient;