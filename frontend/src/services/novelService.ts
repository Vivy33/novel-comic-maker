import { apiClient, ApiResponse } from './api';
import type { NovelFile, NovelContent } from './api';

class NovelService {
  /**
   * 获取项目的小说文件列表
   */
  async getNovels(projectId: string): Promise<ApiResponse<NovelFile[]>> {
    return apiClient.get(`/api/projects/${projectId}/novels`);
  }

  /**
   * 上传小说文件
   */
  async uploadNovel(
    projectId: string,
    file: File,
    isPrimary: boolean = false,
    onProgress?: (progress: number) => void
  ): Promise<ApiResponse<NovelFile>> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('is_primary', isPrimary.toString());

    try {
      const response = await apiClient.httpClient.post(
        `/api/projects/${projectId}/novels/upload`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          onUploadProgress: (progressEvent) => {
            if (onProgress && progressEvent.total) {
              const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
              onProgress(progress);
            }
          },
        }
      );
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  /**
   * 创建新的小说文件
   */
  async createNovel(
    projectId: string,
    title: string,
    content: string,
    isPrimary: boolean = false
  ): Promise<ApiResponse<NovelFile>> {
    return apiClient.post(`/api/projects/${projectId}/novels/create`, {
      title,
      content,
      is_primary: isPrimary
    });
  }

  /**
   * 获取小说文件内容
   */
  async getNovelContent(projectId: string, filename: string): Promise<ApiResponse<NovelContent>> {
    return apiClient.get(`/api/projects/${projectId}/novels/${encodeURIComponent(filename)}/content`);
  }

  /**
   * 更新小说文件内容
   */
  async updateNovelContent(
    projectId: string,
    filename: string,
    content: string
  ): Promise<ApiResponse<NovelContent>> {
    return apiClient.put(`/api/projects/${projectId}/novels/${encodeURIComponent(filename)}/content`, {
      content
    });
  }

  /**
   * 删除小说文件
   */
  async deleteNovel(projectId: string, filename: string): Promise<ApiResponse<null>> {
    return apiClient.delete(`/api/projects/${projectId}/novels/${encodeURIComponent(filename)}`);
  }

  /**
   * 设置主要小说文件
   */
  async setPrimaryNovel(projectId: string, filename: string): Promise<ApiResponse<NovelFile>> {
    return apiClient.put(`/api/projects/${projectId}/novels/${encodeURIComponent(filename)}/set-primary`);
  }

  /**
   * 格式化文件大小
   */
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  /**
   * 格式化时间戳
   */
  formatDate(timestamp: number): string {
    return new Date(timestamp * 1000).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}

export default new NovelService();