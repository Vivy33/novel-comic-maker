import apiClient, { ApiResponse, TextToImageRequest, ImageToImageRequest } from './api';

export interface ImageGenerationResult {
  image_url: string;
  generation_id: string;
  model_used: string;
  parameters: {
    prompt: string;
    size: string;
    quality: string;
    style?: string;
  };
  generation_time: number;
  cost?: number;
}

export interface BatchImageGenerationRequest {
  prompts: string[];
  model?: string;
  size?: string;
  quality?: string;
  style?: string;
  count_per_prompt?: number;
  sequential_generation?: boolean;
  max_images?: number;
}

export interface BatchImageGenerationResult {
  generation_id: string;
  images: Array<{
    image_url: string;
    prompt_index: number;
    image_index: number;
  }>;
  total_generated: number;
  generation_time: number;
  total_cost?: number;
}

export interface ImageEditRequest {
  prompt: string;
  base64_image: string;
  base64_mask?: string;
  model?: string;
  size?: string;
  strength?: number;
}

export interface ImageEditResult {
  edited_image_url: string;
  edit_id: string;
  model_used: string;
  edit_time: number;
  cost?: number;
}

class ImageService {
  private baseUrl = '/api/images';

  /**
   * 文生图
   */
  async generateImage(request: TextToImageRequest): Promise<ImageGenerationResult> {
    const response = await apiClient.post<ImageGenerationResult>(`${this.baseUrl}/text-to-image`, request);
    return response.data;
  }

  /**
   * 批量文生图
   */
  async generateImagesBatch(request: BatchImageGenerationRequest): Promise<BatchImageGenerationResult> {
    const response = await apiClient.post<BatchImageGenerationResult>(`${this.baseUrl}/generate-batch`, request);
    return response.data;
  }

  /**
   * 图生图
   */
  async imageToImage(request: ImageToImageRequest): Promise<ImageGenerationResult> {
    const response = await apiClient.post<ImageGenerationResult>(`${this.baseUrl}/image-to-image`, request);
    return response.data;
  }

  /**
   * 编辑图像
   */
  async editImage(request: ImageEditRequest): Promise<ImageEditResult> {
    const response = await apiClient.post<ImageEditResult>(`${this.baseUrl}/edit`, request);
    return response.data;
  }

  /**
   * 上传图像
   */
  async uploadImage(
    file: File,
    imageType: 'reference' | 'character' | 'edit' | 'sketch',
    onProgress?: (progress: number) => void
  ): Promise<{ image_url: string; image_id: string }> {
    const response = await apiClient.uploadFile<{ image_url: string; image_id: string }>(
      `${this.baseUrl}/upload/${imageType}`,
      file,
      onProgress
    );
    return response.data;
  }

  /**
   * 下载图像
   */
  async downloadImage(imageUrl: string, filename?: string): Promise<Blob> {
    try {
      const response = await fetch(imageUrl);
      if (!response.ok) {
        throw new Error(`下载失败: ${response.statusText}`);
      }

      const blob = await response.blob();

      // 如果提供了文件名，触发浏览器下载
      if (filename) {
        const downloadUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(downloadUrl);
      }

      return blob;
    } catch (error) {
      throw new Error(`图像下载失败: ${error}`);
    }
  }
}

export const imageService = new ImageService();
export default imageService;