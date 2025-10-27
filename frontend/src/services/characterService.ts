import apiClient, { Character } from './api';

export interface CreateCharacterRequest {
  name: string;
  description?: string;
  traits: string[];
  reference_images?: string[];
  project_id: string;
}

export interface UpdateCharacterRequest {
  name?: string;
  description?: string;
  traits?: string[];
  reference_images?: string[];
}

export interface GenerateCharacterRequest {
  text_description: string;
  style?: string;
  project_id: string;
  include_back?: boolean;
  include_side?: boolean;
}

class CharacterService {
  private baseUrl = '/api/characters';

  /**
   * 获取项目的所有角色
   */
  async getProjectCharacters(projectId: string): Promise<Character[]> {
    const response = await apiClient.get<any>(`${this.baseUrl}/${projectId}`);

    // 处理后端返回的数据结构
    if (response && response.data && Array.isArray(response.data.characters)) {
      return response.data.characters;
    }

    // 如果直接返回数组（向后兼容）
    if (Array.isArray(response)) {
      return response;
    }

    // 如果是对象且包含data属性且data是数组
    if (response && Array.isArray(response.data)) {
      return response.data;
    }

    // 其他情况返回空数组
    console.warn('API返回的角色数据格式不正确:', response);
    return [];
  }

  /**
   * 获取角色详情
   */
  async getCharacter(id: string): Promise<Character> {
    const response = await apiClient.get<Character>(`${this.baseUrl}/${id}`);
    return response;
  }

  /**
   * 创建新角色
   */
  async createCharacter(data: CreateCharacterRequest): Promise<Character> {
    const response = await apiClient.post<Character>(`${this.baseUrl}/${data.project_id}`, data);
    return response;
  }

  /**
   * 更新角色
   */
  async updateCharacter(id: string, data: UpdateCharacterRequest): Promise<Character> {
    const response = await apiClient.put<Character>(`${this.baseUrl}/${id}`, data);
    return response;
  }

  /**
   * 删除角色
   */
  async deleteCharacter(character: { id: string; project_id: string; name: string }): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${character.project_id}/${character.name}`);
  }

  /**
   * AI生成角色
   */
  async generateCharacter(data: GenerateCharacterRequest): Promise<Character> {
    const response = await apiClient.post<Character>(`${this.baseUrl}/generate`, data);
    return response;
  }

  /**
   * 上传角色参考图
   */
  async uploadCharacterImage(
    characterId: string,
    file: File,
    imageType: 'front' | 'back' | 'side' | 'reference',
    onProgress?: (progress: number) => void
  ): Promise<{ image_url: string }> {
    const response = await apiClient.uploadFile<{ image_url: string }>(
      `${this.baseUrl}/${characterId}/images/${imageType}`,
      file,
      onProgress
    );
    return response;
  }

  /**
   * 检查角色一致性
   */
  async checkCharacterConsistency(characterId: string, imageUrl: string): Promise<{
    consistency_score: number;
    issues: string[];
    suggestions: string[];
  }> {
    const response = await apiClient.post<{
      consistency_score: number;
      issues: string[];
      suggestions: string[];
    }>(`${this.baseUrl}/${characterId}/check-consistency`, { image_url: imageUrl });
    return response;
  }

  /**
   * 获取角色生成模板
   */
  async getCharacterTemplates(): Promise<Array<{
    id: string;
    name: string;
    description: string;
    preview_url: string;
    tags: string[];
  }>> {
    const response = await apiClient.get<Array<{
      id: string;
      name: string;
      description: string;
      preview_url: string;
      tags: string[];
    }>>(`${this.baseUrl}/templates`);
    return response;
  }

  /**
   * 基于模板生成角色
   */
  async generateFromTemplate(
    templateId: string,
    customizations: Record<string, any>
  ): Promise<Character> {
    const response = await apiClient.post<Character>(`${this.baseUrl}/generate-from-template`, {
      template_id: templateId,
      customizations,
    });
    return response;
  }

  /**
   * 生成角色卡
   */
  async generateCharacterCard(characterId: string, cardData: {
    prompt?: string;
    negative_prompt?: string;
  }): Promise<any> {
    const response = await apiClient.post<any>(`${this.baseUrl}/${characterId}/generate-card`, cardData);
    return response;
  }

  /**
   * 获取角色卡
   */
  async getCharacterCard(characterId: string): Promise<any> {
    const response = await apiClient.get<any>(`${this.baseUrl}/${characterId}/card`);
    return response;
  }

  /**
   * 根据项目ID和角色名称获取角色卡
   */
  async getCharacterCardByName(projectId: string, characterName: string): Promise<any> {
    const response = await apiClient.get<any>(`${this.baseUrl}/${projectId}/${characterName}/card`);
    return response;
  }

  /**
   * 删除角色卡
   */
  async deleteCharacterCard(projectId: string, characterName: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${projectId}/${characterName}/card`);
  }

  /**
   * 上传角色参考图片
   */
  async uploadCharacterReferenceImage(
    projectId: string,
    characterName: string,
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<{ path: string }> {
    const response = await apiClient.uploadFile<{ path: string }>(
      `${this.baseUrl}/${projectId}/${characterName}/reference-image`,
      file,
      onProgress
    );
    return response;
  }

  /**
   * 更新角色卡信息
   */
  async updateCharacterCard(projectId: string, characterName: string, cardData: any): Promise<any> {
    const response = await apiClient.put<any>(`${this.baseUrl}/${projectId}/${characterName}/card`, cardData);
    return response;
  }
}

export const characterService = new CharacterService();
export default characterService;