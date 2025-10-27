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
  paragraph_id?: string; // 段落ID，用于段落分组
  paragraph_index?: number; // 段落序号，用于排序
  notes?: string; // 分镜备注
}

// 段落信息
export interface ParagraphInfo {
  paragraph_id: string;
  paragraph_index: number;
  content: string; // 段落文本内容
  panels: ComicPanel[]; // 该段落的分镜图
  panel_count: number; // 分镜图数量
  confirmed_count: number; // 已确认的分镜图数量
}

// 章节详情（支持段落分组）
export interface ChapterDetail {
  chapter_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  status: string;
  total_panels: number;
  confirmed_panels: number;
  unconfirmed_panels: number;
  panels: ComicPanel[]; // 保持兼容性
  paragraphs?: ParagraphInfo[]; // 段落分组数据
}

// 用于向后兼容的章节详情（旧格式）
export interface ChapterDetailLegacy {
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

// 分镜图编辑操作类型
export interface PanelEditOperation {
  type: 'reorder' | 'delete' | 'update_notes' | 'reassign_paragraph';
  panel_ids: number[];
  data?: {
    new_order?: number[];
    notes?: string;
    new_paragraph_id?: string;
  };
}

// 分镜图批量操作请求
export interface PanelBatchRequest {
  chapter_id: string;
  operations: PanelEditOperation[];
}