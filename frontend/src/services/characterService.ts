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
    const response = await apiClient.get<{characters: Character[]}>(`${this.baseUrl}/${projectId}`);
    console.log('getProjectCharacters - 原始响应:', response);
    console.log('getProjectCharacters - response.data:', response.data);
    console.log('getProjectCharacters - response.data?.characters:', response.data?.characters);
    const result = response.data?.characters || [];
    console.log('getProjectCharacters - 最终结果:', result);
    return result;
  }

  /**
   * 获取角色详情
   */
  async getCharacter(id: string): Promise<Character> {
    const response = await apiClient.get<{data: Character}>(`${this.baseUrl}/${id}`);
    return response.data?.data;
  }

  /**
   * 创建新角色
   */
  async createCharacter(data: CreateCharacterRequest): Promise<Character> {
    console.log('createCharacter - 请求数据:', data);
    const response = await apiClient.post<{data: Character}>(`${this.baseUrl}/${data.project_id}`, data);
    console.log('createCharacter - 响应:', response);
    console.log('createCharacter - response.data:', response.data);
    const result = response.data?.data;
    console.log('createCharacter - 最终结果:', result);
    return result;
  }

  /**
   * 更新角色
   */
  async updateCharacter(id: string, data: UpdateCharacterRequest): Promise<Character> {
    const response = await apiClient.put<{data: Character}>(`${this.baseUrl}/${id}`, data);
    return response.data?.data;
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
    return response.data;
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
    return response.data;
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
    return response.data;
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
    return response.data;
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
    return response.data;
  }

  /**
   * 生成角色卡
   */
  async generateCharacterCard(characterId: string, cardData: {
    prompt?: string;
    negative_prompt?: string;
  }): Promise<any> {
    const response = await apiClient.post<any>(`${this.baseUrl}/${characterId}/generate-card`, cardData);
    return response.data;
  }

  /**
   * 获取角色卡
   */
  async getCharacterCard(characterId: string): Promise<any> {
    const response = await apiClient.get<any>(`${this.baseUrl}/${characterId}/card`);
    return response.data;
  }

  /**
   * 根据项目ID和角色名称获取角色卡
   */
  async getCharacterCardByName(projectId: string, characterName: string): Promise<any> {
    const response = await apiClient.get<any>(`${this.baseUrl}/${projectId}/${characterName}/card`);
    return response.data;
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
    return response.data;
  }

  /**
   * 更新角色卡信息
   */
  async updateCharacterCard(projectId: string, characterName: string, cardData: any): Promise<any> {
    const response = await apiClient.put<any>(`${this.baseUrl}/${projectId}/${characterName}/card`, cardData);
    return response.data;
  }
}

export const characterService = new CharacterService();
export default characterService;