import apiClient, { ApiResponse, Project } from './api';

export interface CreateProjectRequest {
  name: string;
  description?: string;
  metadata?: Record<string, any>;
}

export interface UpdateProjectRequest {
  name?: string;
  description?: string;
  metadata?: Record<string, any>;
}

class ProjectService {
  private baseUrl = '/api/projects';

  /**
   * 获取所有项目
   */
  async getProjects(): Promise<Project[]> {
    const response = await apiClient.get<Project[]>(this.baseUrl);
    return response.data;
  }

  /**
   * 获取项目详情
   */
  async getProject(id: string): Promise<Project> {
    const response = await apiClient.get<Project>(`${this.baseUrl}/${id}`);
    return response.data;
  }

  /**
   * 创建新项目
   */
  async createProject(data: CreateProjectRequest): Promise<Project> {
    const response = await apiClient.post<Project>(this.baseUrl, data);
    return response.data;
  }

  /**
   * 更新项目
   */
  async updateProject(id: string, data: UpdateProjectRequest): Promise<Project> {
    const response = await apiClient.put<Project>(`${this.baseUrl}/${id}`, data);
    return response.data;
  }

  /**
   * 删除项目
   */
  async deleteProject(id: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${id}`);
  }

  /**
   * 获取项目状态
   */
  async getProjectStatus(id: string): Promise<{ status: string; progress?: number }> {
    const response = await apiClient.get<{ status: string; progress?: number }>(`${this.baseUrl}/${id}/status`);
    return response.data;
  }

  /**
   * 上传项目文件
   */
  async uploadProjectFile(
    projectId: string,
    file: File,
    fileType: 'novel' | 'reference' | 'character',
    onProgress?: (progress: number) => void
  ): Promise<{ file_url: string; file_id: string }> {
    const response = await apiClient.uploadFile<{ file_url: string; file_id: string }>(
      `${this.baseUrl}/${projectId}/files/${fileType}`,
      file,
      onProgress
    );
    return response.data;
  }

  /**
   * 获取项目文件列表
   */
  async getProjectFiles(projectId: string): Promise<Array<{
    id: string;
    file_name: string;
    file_type: string;
    file_url: string;
    upload_time: string;
  }>> {
    const response = await apiClient.get<Array<{
      id: string;
      file_name: string;
      file_type: string;
      file_url: string;
      upload_time: string;
    }>>(`${this.baseUrl}/${projectId}/files`);
    return response.data;
  }

  /**
   * 删除项目文件
   */
  async deleteProjectFile(projectId: string, fileId: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${projectId}/files/${fileId}`);
  }

  /**
   * 获取项目时间线
   */
  async getProjectTimeline(id: string): Promise<any> {
    const response = await apiClient.get(`${this.baseUrl}/${id}/timeline`);
    return response.data;
  }
}

export const projectService = new ProjectService();
export default projectService;