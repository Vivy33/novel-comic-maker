import apiClient, { ApiResponse } from './api';

export interface CoverGenerationRequest {
  projectId: string;
  coverType: 'project' | 'chapter';
  novelFilename?: string;
  coverPrompt: string;
  coverSize: string;
  referenceImage?: File;
}

export interface CoverGenerationResponse {
  success: boolean;
  cover_id: string;
  title: string;
  description: string;
  image_url: string;
  local_path?: string;
  cover_type: string;
  related_novel?: string;
  status: string;
}

export interface CoverListResponse {
  success: boolean;
  covers: Array<{
    cover_id: string;
    title: string;
    description: string;
    image_url: string;
    local_path?: string;
    cover_type: string;
    related_novel?: string;
    status: string;
    created_at: string;
  }>;
  total_count: number;
}

class CoverService {
  private baseUrl = '/api/comics';

  /**
   * 生成漫画封面
   */
  async generateCover(request: CoverGenerationRequest): Promise<CoverGenerationResponse> {
    const formData = new FormData();

    // 添加必需字段
    formData.append('cover_type', request.coverType);
    formData.append('cover_prompt', request.coverPrompt);
    formData.append('cover_size', request.coverSize);

    // 添加可选字段
    if (request.novelFilename) {
      formData.append('novel_filename', request.novelFilename);
    }

    if (request.referenceImage) {
      formData.append('reference_image', request.referenceImage);
    }

    // 使用底层的axios客户端直接发送FormData
    const response = await apiClient.httpClient.post<CoverGenerationResponse>(
      `${this.baseUrl}/${request.projectId}/generate-cover`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  }

  /**
   * 获取项目封面列表
   */
  async getProjectCovers(projectId: string): Promise<CoverListResponse> {
    const response = await apiClient.get<CoverListResponse>(
      `${this.baseUrl}/${projectId}/covers`
    );
    return response;
  }

  /**
   * 获取单个封面详情
   */
  async getCoverDetail(projectId: string, coverId: string): Promise<any> {
    const response = await apiClient.get(
      `${this.baseUrl}/${projectId}/covers/${coverId}`
    );
    return response;
  }

  /**
   * 删除封面
   */
  async deleteCover(projectId: string, coverId: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.delete<{ success: boolean; message: string }>(
      `${this.baseUrl}/${projectId}/covers/${coverId}`
    );
    return response;
  }

  /**
   * 下载封面图片
   */
  async downloadCover(imageUrl: string, filename?: string): Promise<Blob> {
    try {
      const response = await fetch(imageUrl);
      if (!response.ok) {
        throw new Error(`下载失败: ${response.statusText}`);
      }
      return await response.blob();
    } catch (error) {
      throw new Error(`封面下载失败: ${error}`);
    }
  }

  /**
   * 更新封面信息
   */
  async updateCoverInfo(
    projectId: string,
    coverId: string,
    updateData: {
      title?: string;
      description?: string;
    }
  ): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.put<{ success: boolean; message: string }>(
      `${this.baseUrl}/${projectId}/covers/${coverId}`,
      updateData
    );
    return response;
  }

  /**
   * 设置项目主封面
   */
  async setProjectMainCover(projectId: string, coverId: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.post<{ success: boolean; message: string }>(
      `${this.baseUrl}/${projectId}/covers/${coverId}/set-main`
    );
    return response;
  }

  /**
   * 获取项目主封面
   */
  async getProjectMainCover(projectId: string): Promise<any> {
    const response = await apiClient.get(
      `${this.baseUrl}/${projectId}/covers/main`
    );
    return response;
  }
}

export const coverService = new CoverService();
export default coverService;