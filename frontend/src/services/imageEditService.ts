import apiClient from './api';

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

    const response = await apiClient.httpClient.post<ImageUploadResponse>(`${this.baseUrl}/upload-base64`, formData);
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

    const response = await apiClient.httpClient.post<ImageEditResponse>(`${this.baseUrl}/edit-with-base64`, formData);
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

    const response = await apiClient.httpClient.post<ImageEditResponse>(`${this.baseUrl}/edit-upload`, formData);
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
    return await apiClient.get<ImageModelsResponse>(`${this.baseUrl}/models`);
  }

  /**
   * 图生图功能 - 上传参考图生成新图像 (已废弃，请使用editUploadedImage)
   * @deprecated 请使用 editUploadedImage 方法
   */
  async imageToImageGeneration(
    prompt: string,
    file: File,
    modelPreference: string = 'doubao-seedream-4-0-250828',
    size: string = '1024x1024'
  ): Promise<ImageToImageResponse> {
    // 重定向到图像编辑功能
    console.warn('imageToImageGeneration 已废弃，请使用 editUploadedImage');
    const editResponse = await this.editUploadedImage(prompt, file, undefined, modelPreference, size);
    return {
      success: editResponse.success,
      result_url: editResponse.result_url,
      local_path: editResponse.local_path,
      original_filename: file.name,
      generation_params: editResponse.edit_params,
    };
  }

  /**
   * 调试端点 - 测试FormData参数
   */
  async debugFormData(
    prompt: string,
    file: File | null = null,
    modelPreference: string = 'doubao-seedream-4-0-250828',
    size: string = '1024x1024'
  ): Promise<any> {
    const formData = new FormData();
    formData.append('prompt', prompt);
    if (file) {
      formData.append('file', file);
    }
    formData.append('model_preference', modelPreference);
    formData.append('size', size);
    formData.append('stream', 'true');

    const response = await apiClient.httpClient.post<any>(`${this.baseUrl}/debug-form-data`, formData);
    return response.data;
  }

  /**
   * 列出临时文件
   */
  async listTempFiles(): Promise<TempFileListResponse> {
    return await apiClient.get<TempFileListResponse>(`${this.baseUrl}/temp-files`);
  }

  /**
   * 删除临时文件
   */
  async deleteTempFile(filename: string): Promise<{ success: boolean; message: string }> {
    return await apiClient.delete<{ success: boolean; message: string }>(`${this.baseUrl}/temp-files/${filename}`);
  }

  /**
   * 编码本地图像为base64格式
   */
  async encodeLocalImage(filePath: string): Promise<any> {
    return await apiClient.post(`${this.baseUrl}/encode-local`, {
      file_path: filePath
    });
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

    const response = await apiClient.httpClient.post<ImageDownloadResponse>(`${this.baseUrl}/download-to-local`, formData);
    return response.data;
  }

  /**
   * 健康检查
   */
  async healthCheck(): Promise<any> {
    return await apiClient.get(`${this.baseUrl}/health`);
  }
}

export const imageEditService = new ImageEditService();
export default imageEditService;