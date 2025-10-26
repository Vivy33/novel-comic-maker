import apiClient, { ApiResponse, Comic, ComicPage, TextAnalysis, ScriptGeneration, Chapter, ChapterDetail, ChapterImage, ComicExportOptions } from './api';
import axios from 'axios';

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
    const response = await axios.get<Comic[]>(`${this.baseUrl}/project/${projectId}`);
    return response.data;
  }

  /**
   * 获取漫画详情
   */
  async getComic(id: string): Promise<Comic> {
    const response = await apiClient.get<Comic>(`${this.baseUrl}/${id}`);
    return response.data;
  }

  /**
   * 创建新漫画
   */
  async createComic(data: CreateComicRequest): Promise<Comic> {
    const response = await apiClient.post<Comic>(this.baseUrl, data);
    return response.data;
  }

  /**
   * AI生成漫画
   */
  async generateComic(data: GenerateComicRequest): Promise<Comic> {
    const response = await apiClient.post<Comic>(`${this.baseUrl}/generate`, data);
    return response.data;
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
    return response.data;
  }

  /**
   * 获取漫画页面
   */
  async getComicPages(comicId: string): Promise<ComicPage[]> {
    const response = await apiClient.get<ComicPage[]>(`${this.baseUrl}/${comicId}/pages`);
    return response.data;
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
    return response.data;
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
    return response.data;
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
    return response.data;
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
    return response.data;
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
    return response.data;
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
    return response.data;
  }

  // ==================== 章节管理API ====================

  /**
   * 获取项目的所有章节
   */
  async getProjectChapters(projectId: string): Promise<Chapter[]> {
    const response = await axios.get<Chapter[]>(`${this.baseUrl}/${projectId}/chapters`);
    return response.data;
  }

  /**
   * 获取章节详情
   */
  async getChapterDetail(projectId: string, chapterId: string): Promise<ChapterDetail> {
    const response = await axios.get<ChapterDetail>(`${this.baseUrl}/${projectId}/chapters/${chapterId}`);
    return response.data;
  }

  /**
   * 重新生成章节
   */
  async regenerateChapter(projectId: string, chapterId: string, options?: {
    regenerate_images_only?: boolean;
    panel_ids?: number[];
    style_changes?: string;
  }): Promise<{ task_id: string }> {
    const response = await axios.post<{ task_id: string }>(`${this.baseUrl}/${projectId}/chapters/${chapterId}/regenerate`, options);
    return response.data;
  }

  /**
   * 删除章节
   */
  async deleteChapter(projectId: string, chapterId: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${projectId}/chapters/${chapterId}`);
  }

  /**
   * 删除章节中的特定画面
   */
  async deleteChapterPanel(projectId: string, chapterId: string, panelId: number): Promise<void> {
    await axios.delete(`${this.baseUrl}/${projectId}/chapters/${chapterId}/panels/${panelId}`);
  }

  /**
   * 确认/取消确认画面
   */
  async updatePanelConfirmation(projectId: string, chapterId: string, panelId: number, confirmed: boolean): Promise<void> {
    await axios.put(`${this.baseUrl}/${projectId}/chapters/${chapterId}/panels/${panelId}/confirm`, { confirmed });
  }

  /**
   * 批量确认画面
   */
  async batchConfirmPanels(projectId: string, chapterId: string, panelIds: number[], confirmed: boolean): Promise<void> {
    await axios.put(`${this.baseUrl}/${projectId}/chapters/${chapterId}/panels/batch-confirm`, {
      panel_ids: panelIds,
      confirmed
    });
  }

  /**
   * 导出章节
   */
  async exportChapter(projectId: string, chapterId: string, options: ComicExportOptions): Promise<{
    download_url: string;
    file_size: number;
  }> {
    const response = await axios.post<{
      download_url: string;
      file_size: number;
    }>(`${this.baseUrl}/${projectId}/chapters/${chapterId}/export`, options);
    return response.data;
  }

  /**
   * 导出整个项目的漫画
   */
  async exportProjectComics(projectId: string, options: ComicExportOptions): Promise<{
    download_url: string;
    file_size: number;
  }> {
    const response = await apiClient.post<{
      download_url: string;
      file_size: number;
    }>(`${this.baseUrl}/${projectId}/export`, options);
    return response.data;
  }

  /**
   * 获取重新生成任务状态
   */
  async getRegenerateStatus(taskId: string): Promise<{
    status: 'pending' | 'running' | 'completed' | 'failed';
    progress: number;
    current_step?: string;
    estimated_time_remaining?: number;
    error_message?: string;
    result?: any;
  }> {
    const response = await apiClient.get<{
      status: 'pending' | 'running' | 'completed' | 'failed';
      progress: number;
      current_step?: string;
      estimated_time_remaining?: number;
      error_message?: string;
      result?: any;
    }>(`${this.baseUrl}/regenerate/${taskId}/status`);
    return response.data;
  }
}

export const comicService = new ComicService();
export default comicService;