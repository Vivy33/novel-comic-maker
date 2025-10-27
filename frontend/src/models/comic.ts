// 漫画相关的前端模型定义

export interface ChapterInfo {
  chapter_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  status: string; // pending, generating, completed, error
  total_panels: number;
  confirmed_panels: number;
  unconfirmed_panels: number;
  chapter_number: number;
  cover_image_path: string | null;
  cover_thumbnail_url: string | null;
  completion_percentage: number;
  has_unconfirmed_panels: boolean;
}

export interface CoverInfo {
  cover_id: string;
  cover_type: string; // project, chapter
  title: string | null;
  description: string | null;
  image_path: string;
  thumbnail_url: string;
  is_primary: boolean;
  created_at: string;
  file_size: number;
}

export interface ProjectCoversResponse {
  project_id: string;
  primary_cover: CoverInfo | null;
  chapter_covers: CoverInfo[];
  total_covers: number;
}

export interface ComicPanel {
  panel_id: number;
  description: string;
  scene_description: string;
  characters: string[];
  scene: string;
  emotion: string;
  image_path: string | null;
  confirmed: boolean;
  generated_at: string | null;
  updated_at: string | null;
}

export interface ChapterDetail {
  chapter_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  status: string;
  total_panels: number;
  confirmed_panels: number;
  unconfirmed_panels: number;
  panels: ComicPanel[];
}