// 导出所有API服务和类型定义
export * from './api';
export { default as apiClient } from './api';

export { default as projectService } from './projectService';
export type { CreateProjectRequest, UpdateProjectRequest } from './projectService';
export { default as characterService } from './characterService';
export type { CreateCharacterRequest, UpdateCharacterRequest, GenerateCharacterRequest } from './characterService';
export { default as comicService } from './comicService';
export type { CreateComicRequest, GenerateComicRequest, GeneratePagesRequest } from './comicService';
export { default as imageService } from './imageService';
export type { ImageGenerationResult, BatchImageGenerationRequest, ImageEditRequest } from './imageService';
export { default as imageEditService } from './imageEditService';
export { default as workflowService } from './workflowService';
export type { StartWorkflowRequest, WorkflowTemplate, WorkflowExecution } from './workflowService';
export { default as novelService } from './novelService';
export { default as coverService } from './coverService';
export type { CoverGenerationRequest, CoverGenerationResponse, CoverListResponse } from './coverService';

// 重新导出常用类型
export type {
  Project,
  Character,
  Comic,
  ComicPage,
  NovelFile,
  NovelContent,
  TextAnalysis,
  ScriptGeneration,
  WorkflowStatus,
} from './api';

// 导出统一的API错误处理
export class ApiError extends Error {
  public status: number;
  public details?: any;

  constructor(message: string, status: number = 0, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

// API错误处理工具函数
export const handleApiError = (error: any): ApiError => {
  console.error('handleApiError - 完整错误对象:', error);
  if (error.response) {
    // 服务器返回的错误
    const message = error.response.data?.detail?.[0]?.msg ||
                   error.response.data?.detail ||
                   error.response.data?.message ||
                   error.message;
    console.error('handleApiError - 提取的消息:', message);
    return new ApiError(
      message,
      error.response.status,
      error.response.data
    );
  } else if (error.request) {
    // 网络错误
    return new ApiError('网络连接失败，请检查网络设置', 0);
  } else if (error instanceof ApiError) {
    // 已经是ApiError实例
    return error;
  } else {
    // 其他未知错误
    return new ApiError(error.message || '未知错误', 0);
  }
};

// 响应数据检查工具
export const checkApiResponse = <T>(response: any): T => {
  if (response && response.success) {
    return response.data;
  } else {
    throw new ApiError(response.message || 'API响应格式错误');
  }
};

// 加载状态管理工具
export const createLoadingManager = () => {
  const loadingStates: Record<string, boolean> = {};

  return {
    setLoading: (key: string, loading: boolean) => {
      loadingStates[key] = loading;
    },
    isLoading: (key: string): boolean => {
      return !!loadingStates[key];
    },
    getLoadingStates: () => ({ ...loadingStates }),
    clearAll: () => {
      Object.keys(loadingStates).forEach(key => {
        delete loadingStates[key];
      });
    },
  };
};

// 创建全局加载管理器
export const loadingManager = createLoadingManager();