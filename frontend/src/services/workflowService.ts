import apiClient, { WorkflowStatus } from './api';
import axios from 'axios';

export interface StartWorkflowRequest {
  project_id: string;
  workflow_type: 'comic_generation' | 'text_compression' | 'character_design' | 'feedback_processing';
  parameters: Record<string, any>;
  priority?: 'low' | 'normal' | 'high';
  webhook_url?: string;
}

export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  workflow_type: string;
  default_parameters: Record<string, any>;
  steps: Array<{
    step_id: string;
    name: string;
    description: string;
    agent_type: string;
    parameters: Record<string, any>;
    dependencies: string[];
    estimated_time: number;
  }>;
  estimated_total_time: number;
  tags: string[];
}

export interface WorkflowStep {
  step_id: string;
  workflow_id: string;
  step_type: string;
  agent_type: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  progress: number;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  input_data?: any;
  output_data?: any;
  parameters: Record<string, any>;
  execution_time?: number;
  cost?: number;
}

export interface WorkflowExecution {
  workflow_id: string;
  template_id?: string;
  project_id: string;
  status: WorkflowStatus['status'];
  progress: number;
  current_step?: string;
  total_steps: number;
  completed_steps: number;
  started_at: string;
  estimated_completion_time?: string;
  total_cost?: number;
  steps: WorkflowStep[];
  result?: any;
  error_message?: string;
}

// 新增分段式漫画生成的类型定义
export interface TextSegmentationRequest {
  novel_content: string;
  project_name: string;
  target_length?: string;  // small(200字), medium(300字), large(500字)
  preserve_context?: boolean;
  language?: string;     // chinese/english
}

export interface TextSegmentationResponse {
  success: boolean;
  message: string;
  total_segments: number;
  segments: Array<{
    content: string;
    word_count: number;
    character_count: number;
    segment_index: number;
    // 新增漫画导向字段
    segment_type?: string;
    scene_setting?: string;
    characters_present?: string[];
    emotional_tone?: string;
    key_events?: string[];
    transition_clues?: string[];
    character_descriptions?: Record<string, string[]>;
    scene_elements?: string[];
    visual_keywords?: string[];
    character_importance?: Record<string, boolean>;
    comic_suitability?: number;
    panel_focus?: string;
  }>;
  first_segment?: any;
  project_name: string;
}

export interface SegmentGenerationRequest {
  project_name: string;
  segment_index: number;
  segment_text: string;
  style_reference_images?: string[];
  selected_characters?: string[];
  style_requirements?: string;
  generation_count?: number;
  previous_segment_image?: string;
}

export interface SegmentGenerationResponse {
  success: boolean;
  message: string;
  segment_index: number;
  generation_result: any;
  total_generated: number;
  project_name: string;
}

export interface SegmentConfirmationRequest {
  project_name: string;
  segment_index: number;
  selected_image_index: number;
}

export interface SegmentConfirmationResponse {
  success: boolean;
  message: string;
  segment_index: number;
  selected_image_index: number;
  has_next_segment: boolean;
  next_segment_index?: number;
  confirmed_image_path?: string;
  project_name: string;
}

class WorkflowService {
  private baseUrl = '/workflows';

  /**
   * 启动工作流（保持向后兼容）
   */
  async startWorkflow(request: StartWorkflowRequest): Promise<WorkflowStatus> {
    // 转换请求格式以匹配后端的 ComicGenerationRequest
    const comicRequest = {
      novel_text: request.parameters.text_content || request.parameters.novel_text || '',
      project_name: request.project_id,
      workflow_type: request.workflow_type,
      // 简化后的直接参数，不再包装在 options 中
      reference_images: request.parameters.reference_images || [],
      style_requirements: request.parameters.style_requirements || '',
      // 保留 options 作为向后兼容
      options: {
        ...request.parameters,
        user_preferences: request.parameters.user_preferences
      }
    };

    // 直接调用axios而不是使用apiClient，因为工作流API返回原始JSON
    // 不符合ApiResponse包装格式
    const response = await axios.post(`/workflows/start`, comicRequest);

    // 检查响应数据是否存在
    if (!response || !response.data) {
      throw new Error('API响应数据为空');
    }

    // 获取实际的后端响应数据，并明确指定类型
    const backendData: any = response.data;

    // 转换响应格式以匹配前端的 WorkflowStatus 接口
    const workflowStatus: WorkflowStatus = {
      id: backendData.workflow_id || backendData.task_id,
      project_id: backendData.project_id,
      workflow_type: backendData.workflow_type || 'comic_generation',
      status: backendData.status,
      progress: 0,
      current_step: undefined,
      started_at: undefined,
      completed_at: undefined,
      error_message: undefined,
      result: backendData
    };
    return workflowStatus;
  }

  /**
   * 获取工作流状态 - 使用漫画服务的状态查询
   */
  async getWorkflowStatus(workflowId: string): Promise<WorkflowExecution> {
    try {
      // 使用漫画服务的状态查询API
      const response = await apiClient.get<any>(`/api/comics/generate/${workflowId}/status`);

      // 检查响应数据是否存在
      // 后端可能返回错误信息，需要处理
      if (!response.data) {
        throw new Error('工作流状态响应数据为空');
      }

      // 将漫画服务响应转换为工作流执行格式
      const comicStatus = response.data;
      return {
        workflow_id: comicStatus.task_id || workflowId,
        template_id: undefined,
        project_id: comicStatus.project_id,
        status: this.mapComicStatusToWorkflowStatus(comicStatus.status),
        progress: comicStatus.progress || 0,
        current_step: comicStatus.current_step,
        total_steps: 10, // 估算值
        completed_steps: Math.floor((comicStatus.progress || 0) * 10 / 100),
        started_at: comicStatus.started_at,
        estimated_completion_time: undefined,
        total_cost: undefined,
        steps: [], // 简化实现
        result: comicStatus,
        error_message: comicStatus.error_message
      };
    } catch (error: any) {
      // 特殊处理"任务不存在"的情况 - 检查多种可能的错误格式
      const errorDetail = error.response?.data?.detail || '';
      const errorMessage = error.message || '';

      if (errorDetail.includes('任务不存在') ||
          errorMessage.includes('任务不存在') ||
          (errorDetail.includes('task') && errorDetail.includes('not exist')) ||
          errorDetail.includes('找不到任务')) {
        // 任务已完成并被清理，返回完成状态
        return {
          workflow_id: workflowId,
          template_id: undefined,
          project_id: '',
          status: 'completed' as const,
          progress: 100,
          current_step: 'completed',
          total_steps: 10,
          completed_steps: 10,
          started_at: new Date().toISOString(), // 使用当前时间
          estimated_completion_time: undefined,
          total_cost: undefined,
          steps: [],
          result: { status: 'completed', message: '任务已完成或已清理' },
          error_message: undefined
        };
      }
      // 其他错误正常抛出
      throw error;
    }
  }

  /**
   * 将漫画服务状态映射到工作流状态
   */
  private mapComicStatusToWorkflowStatus(comicStatus: string): 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' {
    switch (comicStatus) {
      case 'pending': return 'pending';
      case 'running': return 'running';
      case 'completed': return 'completed';
      case 'failed': return 'failed';
      case 'cancelled': return 'cancelled';
      default: return 'pending';
    }
  }

  /**
   * 取消工作流
   */
  async cancelWorkflow(workflowId: string, reason?: string): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${workflowId}/cancel`, { reason });
  }

  /**
   * 暂停工作流
   */
  async pauseWorkflow(workflowId: string): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${workflowId}/pause`);
  }

  /**
   * 恢复工作流
   */
  async resumeWorkflow(workflowId: string): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${workflowId}/resume`);
  }

  /**
   * 重试工作流
   */
  async retryWorkflow(workflowId: string, fromStep?: string): Promise<WorkflowStatus> {
    const response = await apiClient.post<WorkflowStatus>(`${this.baseUrl}/${workflowId}/retry`, {
      from_step: fromStep,
    });
    return response.data;
  }

  /**
   * 获取工作流模板
   */
  async getWorkflowTemplates(workflowType?: string): Promise<WorkflowTemplate[]> {
    const url = workflowType ? `${this.baseUrl}/templates?workflow_type=${workflowType}` : `${this.baseUrl}/templates`;
    const response = await apiClient.get<WorkflowTemplate[]>(url);
    return response.data;
  }

  /**
   * 基于模板启动工作流
   */
  async startWorkflowFromTemplate(
    templateId: string,
    projectId: string,
    customizations?: Record<string, any>
  ): Promise<WorkflowStatus> {
    const response = await apiClient.post<WorkflowStatus>(`${this.baseUrl}/start-from-template`, {
      template_id: templateId,
      project_id: projectId,
      customizations,
    });
    return response.data;
  }

  /**
   * 获取项目的工作流历史
   */
  async getProjectWorkflows(
    projectId: string,
    options?: {
      limit?: number;
      offset?: number;
      workflow_type?: string;
      status?: string;
      date_from?: string;
      date_to?: string;
    }
  ): Promise<{
    workflows: WorkflowExecution[];
    total: number;
    has_more: boolean;
  }> {
    const params = new URLSearchParams();
    if (options) {
      Object.entries(options).forEach(([key, value]) => {
        if (value !== undefined) {
          params.append(key, value.toString());
        }
      });
    }

    const response = await apiClient.get<{
      workflows: WorkflowExecution[];
      total: number;
      has_more: boolean;
    }>(`${this.baseUrl}/project/${projectId}?${params.toString()}`);
    return response.data;
  }

  /**
   * 获取工作流步骤详情
   */
  async getWorkflowStep(workflowId: string, stepId: string): Promise<WorkflowStep> {
    const response = await apiClient.get<WorkflowStep>(`${this.baseUrl}/${workflowId}/steps/${stepId}`);
    return response.data;
  }

  /**
   * 获取工作流执行日志
   */
  async getWorkflowLogs(
    workflowId: string,
    options?: {
      level?: 'debug' | 'info' | 'warning' | 'error';
      limit?: number;
      offset?: number;
    }
  ): Promise<{
    logs: Array<{
      timestamp: string;
      level: string;
      step_id?: string;
      message: string;
      details?: any;
    }>;
    total: number;
    has_more: boolean;
  }> {
    const params = new URLSearchParams();
    if (options) {
      Object.entries(options).forEach(([key, value]) => {
        if (value !== undefined) {
          params.append(key, value.toString());
        }
      });
    }

    const response = await apiClient.get<{
      logs: Array<{
        timestamp: string;
        level: string;
        step_id?: string;
        message: string;
        details?: any;
      }>;
      total: number;
      has_more: boolean;
    }>(`${this.baseUrl}/${workflowId}/logs?${params.toString()}`);
    return response.data;
  }

  /**
   * 导出工作流结果
   */
  async exportWorkflowResult(
    workflowId: string,
    format: 'json' | 'csv' | 'pdf',
    options?: {
      include_logs?: boolean;
      include_intermediate_results?: boolean;
    }
  ): Promise<{ download_url: string; file_size: number }> {
    const response = await apiClient.post<{ download_url: string; file_size: number }>(`${this.baseUrl}/${workflowId}/export`, {
      format,
      options,
    });
    return response.data;
  }

  /**
   * 获取工作流统计信息
   */
  async getWorkflowStats(options?: {
    project_id?: string;
    workflow_type?: string;
    date_from?: string;
    date_to?: string;
  }): Promise<any> {
    const params = new URLSearchParams();
    if (options) {
      Object.entries(options).forEach(([key, value]) => {
        if (value !== undefined) {
          params.append(key, value.toString());
        }
      });
    }

    const response = await apiClient.get(`${this.baseUrl}/stats?${params.toString()}`);
    return response.data;
  }

  /**
   * 创建自定义工作流模板
   */
  async createWorkflowTemplate(template: Omit<WorkflowTemplate, 'id'>): Promise<WorkflowTemplate> {
    const response = await apiClient.post<WorkflowTemplate>(`${this.baseUrl}/templates`, template);
    return response.data;
  }

  /**
   * 更新工作流模板
   */
  async updateWorkflowTemplate(
    templateId: string,
    updates: Partial<WorkflowTemplate>
  ): Promise<WorkflowTemplate> {
    const response = await apiClient.put<WorkflowTemplate>(`${this.baseUrl}/templates/${templateId}`, updates);
    return response.data;
  }

  /**
   * 删除工作流模板
   */
  async deleteWorkflowTemplate(templateId: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/templates/${templateId}`);
  }

  /**
   * 验证工作流配置
   */
  async validateWorkflowConfig(config: {
    steps: Array<{
      step_type: string;
      agent_type: string;
      parameters: Record<string, any>;
      dependencies: string[];
    }>;
  }): Promise<{
    valid: boolean;
    errors: string[];
    warnings: string[];
  }> {
    const response = await apiClient.post<{
      valid: boolean;
      errors: string[];
      warnings: string[];
    }>(`${this.baseUrl}/validate-config`, { config });
    return response.data;
  }

  // ==================== 分段式漫画生成API ====================

  /**
   * 文本分段并预览第一段
   */
  async segmentAndPreviewNovel(request: TextSegmentationRequest): Promise<TextSegmentationResponse> {
    const response = await axios.post<TextSegmentationResponse>(
      `/workflows/segment-and-preview`,
      request
    );

    if (!response.data) {
      throw new Error('文本分段响应数据为空');
    }

    return response.data;
  }

  /**
   * 为单个段落生成漫画组图
   */
  async generateSegmentComics(request: SegmentGenerationRequest): Promise<SegmentGenerationResponse> {
    const response = await axios.post<SegmentGenerationResponse>(
      `/workflows/generate-segment`,
      request
    );

    if (!response.data) {
      throw new Error('段落生成响应数据为空');
    }

    return response.data;
  }

  /**
   * 确认段落选择的图片，进入下一段
   */
  async confirmSegmentSelection(request: SegmentConfirmationRequest): Promise<SegmentConfirmationResponse> {
    const response = await axios.post<SegmentConfirmationResponse>(
      `/workflows/confirm-segment`,
      request
    );

    if (!response.data) {
      throw new Error('段落确认响应数据为空');
    }

    return response.data;
  }
}

export const workflowService = new WorkflowService();
export default workflowService;