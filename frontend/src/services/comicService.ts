import apiClient, { ApiResponse, Comic, ComicPage, TextAnalysis, ScriptGeneration } from './api';
import { ChapterInfo, CoverInfo, ProjectCoversResponse, ChapterDetail, ComicPanel } from '../models/comic';

export interface CreateComicRequest {
  project_id: string;
  title: string;
  summary?: string;
  style?: string;
  target_audience?: string;
}

export interface GenerateComicRequest {
  project_id: string;
  text_content: string;
  manga_type?: string;
  target_audience?: string;
  art_style?: string;
  reference_images?: string[];
  chapter_config?: {
    pages_per_chapter: number;
    max_pages: number;
  };
}

export interface GeneratePagesRequest {
  comic_id: string;
  scene_descriptions: string[];
  user_prompt?: string;
  reference_images?: string[];
  generation_config?: {
    image_count: number;
    size: string;
    quality: string;
  };
}

class ComicService {
  private baseUrl = '/api/comics';

  /**
   * 获取项目的所有漫画
   */
  async getProjectComics(projectId: string): Promise<Comic[]> {
    const response = await apiClient.get<Comic[]>(`${this.baseUrl}/project/${projectId}`);
    return response;
  }

  /**
   * 获取漫画详情
   */
  async getComic(id: string): Promise<Comic> {
    const response = await apiClient.get<Comic>(`${this.baseUrl}/${id}`);
    return response;
  }

  /**
   * 创建新漫画
   */
  async createComic(data: CreateComicRequest): Promise<Comic> {
    const response = await apiClient.post<Comic>(this.baseUrl, data);
    return response;
  }

  /**
   * AI生成漫画
   */
  async generateComic(data: GenerateComicRequest): Promise<Comic> {
    const response = await apiClient.post<Comic>(`${this.baseUrl}/generate`, data);
    return response;
  }

  /**
   * 获取漫画生成状态
   */
  async getComicGenerationStatus(comicId: string): Promise<{
    status: 'creating' | 'generating' | 'completed' | 'error';
    progress: number;
    current_step?: string;
    estimated_time_remaining?: number;
    error_message?: string;
  }> {
    const response = await apiClient.get<{
      status: 'creating' | 'generating' | 'completed' | 'error';
      progress: number;
      current_step?: string;
      estimated_time_remaining?: number;
      error_message?: string;
    }>(`${this.baseUrl}/${comicId}/generation-status`);
    return response;
  }

  /**
   * 获取漫画页面
   */
  async getComicPages(comicId: string): Promise<ComicPage[]> {
    const response = await apiClient.get<ComicPage[]>(`${this.baseUrl}/${comicId}/pages`);
    return response;
  }

  /**
   * 生成漫画页面
   */
  async generateComicPages(data: GeneratePagesRequest): Promise<{
    pages: Array<{
      page_number: number;
      image_url: string;
      scene: string;
      panel_description: string;
    }>;
    cover_image_url?: string;
  }> {
    const response = await apiClient.post<{
      pages: Array<{
        page_number: number;
        image_url: string;
        scene: string;
        panel_description: string;
      }>;
      cover_image_url?: string;
    }>(`${this.baseUrl}/generate-pages`, data);
    return response;
  }

  /**
   * 分析文本
   */
  async analyzeText(text: string, options?: {
    model_preference?: string;
    context_id?: string;
  }): Promise<TextAnalysis> {
    const response = await apiClient.post<TextAnalysis>('/api/ai/analyze-text', {
      text,
      ...options,
    });
    return response;
  }

  /**
   * 生成脚本
   */
  async generateScript(
    textAnalysis: TextAnalysis,
    styleRequirements?: string,
    options?: {
      model_preference?: string;
      context_id?: string;
    }
  ): Promise<ScriptGeneration> {
    const response = await apiClient.post<ScriptGeneration>('/api/ai/generate-script', {
      text_analysis: textAnalysis,
      style_requirements: styleRequirements,
      ...options,
    });
    return response;
  }

  /**
   * 重新生成页面
   */
  async regeneratePage(
    comicId: string,
    pageNumber: number,
    modifications?: {
      prompt_changes?: string;
      style_changes?: string;
      reference_images?: string[];
    }
  ): Promise<ComicPage> {
    const response = await apiClient.post<ComicPage>(`${this.baseUrl}/${comicId}/pages/${pageNumber}/regenerate`, modifications);
    return response;
  }

  /**
   * 删除页面
   */
  async deletePage(comicId: string, pageNumber: number): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${comicId}/pages/${pageNumber}`);
  }

  /**
   * 导出漫画
   */
  async exportComic(
    comicId: string,
    format: 'pdf' | 'images' | 'zip',
    options?: {
      include_text?: boolean;
      resolution?: string;
      quality?: string;
    }
  ): Promise<{ download_url: string; file_size: number }> {
    const response = await apiClient.post<{ download_url: string; file_size: number }>(`${this.baseUrl}/${comicId}/export`, {
      format,
      options,
    });
    return response;
  }

  /**
   * 上传参考图片
   */
  async uploadReferenceImage(projectId: string, file: File): Promise<{
    success: boolean;
    filename: string;
    file_url: string;
    file_size: number;
  }> {
    const formData = new FormData();
    formData.append('image', file);

    const response = await apiClient.httpClient.post<{
      success: boolean;
      filename: string;
      file_url: string;
      file_size: number;
    }>(`${this.baseUrl}/upload/reference-image`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      params: {
        project_id: projectId,
      },
    });
    return response.data;
  }

  /**
   * 获取项目章节列表
   */
  async getChapters(projectId: string): Promise<ChapterInfo[]> {
    const response = await apiClient.get<ChapterInfo[]>(`${this.baseUrl}/${projectId}/chapters`);
    return response;
  }

  /**
   * 获取项目封面（分层级展示）
   */
  async getProjectCovers(projectId: string): Promise<ProjectCoversResponse> {
    const response = await apiClient.get<ProjectCoversResponse>(`${this.baseUrl}/${projectId}/covers`);
    return response;
  }

  /**
   * 设置主封面
   */
  async setPrimaryCover(projectId: string, coverId: string): Promise<any> {
    const response = await apiClient.put(`${this.baseUrl}/${projectId}/covers/${coverId}/set-primary`);
    return response;
  }

  /**
   * 删除封面
   */
  async deleteCover(projectId: string, coverId: string): Promise<any> {
    const response = await apiClient.delete(`${this.baseUrl}/${projectId}/covers/${coverId}`);
    return response;
  }

  /**
   * 获取章节详情
   */
  async getChapterDetail(projectId: string, chapterId: string): Promise<ChapterDetail> {
    const response = await apiClient.get<ChapterDetail>(`${this.baseUrl}/${projectId}/chapters/${chapterId}`);
    return response;
  }

  /**
   * 批量确认图片
   */
  async batchConfirmPanels(projectId: string, chapterId: string, panelIds: number[]): Promise<any> {
    const response = await apiClient.put(`${this.baseUrl}/${projectId}/chapters/${chapterId}/panels/batch-confirm`, {
      panel_ids: panelIds
    });
    return response;
  }

  /**
   * 删除分镜图
   */
  async deletePanel(projectId: string, chapterId: string, panelId: number): Promise<any> {
    console.log('🚀 comicService.deletePanel 调用:', {
      projectId,
      chapterId,
      panelId,
      url: `${this.baseUrl}/${projectId}/chapters/${chapterId}/panels/${panelId}`
    });

    try {
      const response = await apiClient.delete(`${this.baseUrl}/${projectId}/chapters/${chapterId}/panels/${panelId}`);
      console.log('✅ comicService.deletePanel 成功:', response);
      return response;
    } catch (error) {
      console.error('❌ comicService.deletePanel 失败:', error);
      throw error;
    }
  }

  /**
   * 批量删除分镜图
   */
  async batchDeletePanels(projectId: string, chapterId: string, panelIds: number[]): Promise<any> {
    // 由于后端没有批量删除API，这里我们逐个删除
    for (const panelId of panelIds) {
      await this.deletePanel(projectId, chapterId, panelId);
    }
    return { success: true, deleted_count: panelIds.length };
  }

  /**
   * 导出章节
   */
  async exportChapter(projectId: string, chapterId: string): Promise<any> {
    const response = await apiClient.post(`${this.baseUrl}/${projectId}/chapters/${chapterId}/export`, {});
    return response;
  }

  /**
   * 重新生成章节
   */
  async regenerateChapter(projectId: string, chapterId: string): Promise<any> {
    const response = await apiClient.post(`${this.baseUrl}/${projectId}/chapters/${chapterId}/regenerate`, {});
    return response;
  }

  /**
   * 获取漫画模板
   */
  async getComicTemplates(): Promise<Array<{
    id: string;
    name: string;
    description: string;
    preview_url: string;
    manga_type: string;
    art_style: string;
  }>> {
    const response = await apiClient.get<Array<{
      id: string;
      name: string;
      description: string;
      preview_url: string;
      manga_type: string;
      art_style: string;
    }>>(`${this.baseUrl}/templates`);
    return response;
  }
}

export const comicService = new ComicService();
export default comicService;
