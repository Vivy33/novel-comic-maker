import apiClient, { ApiResponse } from './api';

export interface ImageEditRequest {
  prompt: string;
  base64_image: string;
  base64_mask?: string;
  model_preference?: string;
  size?: string;
}

export interface ImageUploadResponse {
  success: boolean;
  base64_data: string;
  image_info: {
    format: string;
    width: number;
    height: number;
    size_bytes: number;
  };
  process_result?: any;
}

export interface ImageEditResponse {
  success: boolean;
  result_url: string;
  local_path: string;
  edit_params: {
    prompt: string;
    model_preference: string;
    size: string;
  };
}

export interface ImageToImageResponse {
  success: boolean;
  result_url: string;
  local_path: string;
  original_filename: string;
  generation_params: {
    prompt: string;
    model_preference: string;
    size: string;
    strength?: number;
  };
}

export interface ImageModelsResponse {
  available_models: string[];
  total_count: number;
}

export interface TempFileListResponse {
  success: boolean;
  files: Array<{
    filename: string;
    size: number;
    modified_time: string;
    download_url: string;
  }>;
  total_count: number;
}

export interface ImageDownloadResponse {
  success: boolean;
  image_url: string;
  local_path: string;
  relative_path: string;
  file_size: number;
  download_time: string;
}

class ImageEditService {
  private baseUrl = '/api/image-edit';

  /**
   * 上传图像并转换为base64格式
   */
  async uploadImageBase64(file: File): Promise<ImageUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<ImageUploadResponse>(`${this.baseUrl}/upload-base64`, formData);
    return response.data;
  }

  /**
   * 使用base64图像进行编辑
   */
  async editImageWithBase64(request: ImageEditRequest): Promise<ImageEditResponse> {
    const formData = new FormData();
    formData.append('prompt', request.prompt);
    formData.append('base64_image', request.base64_image);
    if (request.base64_mask) {
      formData.append('base64_mask', request.base64_mask);
    }
    formData.append('model_preference', request.model_preference || 'qwen');
    formData.append('size', request.size || '1024x1024');

    const response = await apiClient.post<ImageEditResponse>(`${this.baseUrl}/edit-with-base64`, formData);
    return response.data;
  }

  /**
   * 上传图像文件进行编辑
   */
  async editUploadedImage(
    prompt: string,
    file: File,
    maskFile?: File,
    modelPreference: string = 'qwen',
    size: string = '1024x1024'
  ): Promise<ImageEditResponse> {
    const formData = new FormData();
    formData.append('prompt', prompt);
    formData.append('file', file);
    if (maskFile) {
      formData.append('mask_file', maskFile);
    }
    formData.append('model_preference', modelPreference);
    formData.append('size', size);

    const response = await apiClient.post<ImageEditResponse>(`${this.baseUrl}/edit-upload`, formData);
    return response.data;
  }

  /**
   * 下载生成的图像
   */
  async downloadGeneratedImage(filename: string): Promise<Blob> {
    try {
      const response = await fetch(`${this.baseUrl}/download/${filename}`);
      if (!response.ok) {
        throw new Error(`下载失败: ${response.statusText}`);
      }

      const blob = await response.blob();
      return blob;
    } catch (error) {
      throw new Error(`图像下载失败: ${error}`);
    }
  }

  /**
   * 获取可用的图像编辑模型
   */
  async getAvailableModels(): Promise<ImageModelsResponse> {
    const response = await apiClient.get<ImageModelsResponse>(`${this.baseUrl}/models`);
    return response.data;
  }

  /**
   * 图生图功能 - 上传参考图生成新图像
   */
  async imageToImageGeneration(
    prompt: string,
    file: File,
    modelPreference: string = 'doubao-seedream-4-0-250828',
    size: string = '1024x1024',
    strength: number = 0.8
  ): Promise<ImageToImageResponse> {
    const formData = new FormData();
    formData.append('prompt', prompt);
    formData.append('file', file);
    formData.append('model_preference', modelPreference);
    formData.append('size', size);
    formData.append('strength', strength.toString());

    const response = await apiClient.post<ImageToImageResponse>(`${this.baseUrl}/image-to-image`, formData);
    return response.data;
  }

  /**
   * 列出临时文件
   */
  async listTempFiles(): Promise<TempFileListResponse> {
    const response = await apiClient.get<TempFileListResponse>(`${this.baseUrl}/temp-files`);
    return response.data;
  }

  /**
   * 删除临时文件
   */
  async deleteTempFile(filename: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.delete<{ success: boolean; message: string }>(`${this.baseUrl}/temp-files/${filename}`);
    return response.data;
  }

  /**
   * 编码本地图像为base64格式
   */
  async encodeLocalImage(filePath: string): Promise<any> {
    const response = await apiClient.post(`${this.baseUrl}/encode-local`, {
      file_path: filePath
    });
    return response.data;
  }

  /**
   * 下载图像到本地
   */
  async downloadImageToLocal(
    imageUrl: string,
    filename?: string
  ): Promise<ImageDownloadResponse> {
    const formData = new FormData();
    formData.append('image_url', imageUrl);
    if (filename) {
      formData.append('filename', filename);
    }

    const response = await apiClient.post<ImageDownloadResponse>(`${this.baseUrl}/download-to-local`, formData);
    return response.data;
  }

  /**
   * 健康检查
   */
  async healthCheck(): Promise<any> {
    const response = await apiClient.get(`${this.baseUrl}/health`);
    return response.data;
  }
}

export const imageEditService = new ImageEditService();
export default imageEditService;