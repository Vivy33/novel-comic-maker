import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Paper,
  Button,
  Stepper,
  Step,
  StepLabel,
  LinearProgress,
  Alert,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Grid,
  Chip,
  IconButton,
  Tooltip,
  Card,
  CardMedia,
  CardActions,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  PlayArrow as PlayArrowIcon,
  Refresh as RefreshIcon,
  CheckCircle as CheckCircleIcon,
  RadioButtonUnchecked as PendingIcon,
  Visibility as VisibilityIcon,
  Edit as EditIcon,
  Image as ImageIcon,
  BrokenImage as BrokenImageIcon,
  Upload as UploadIcon,
  NavigateNext as NextIcon,
  NavigateBefore as PreviousIcon,
  RadioButtonUnchecked as RadioButtonUncheckedIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Save as SaveIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { workflowService, characterService, comicService, handleApiError } from '../services';
import NovelSelector from '../components/NovelSelector';
import CharacterCardImage from '../components/CharacterCardImage';
import type {
  TextSegmentationRequest,
  TextSegmentationResponse,
  SegmentGenerationRequest,
  SegmentGenerationResponse,
  SegmentConfirmationRequest,
  SegmentConfirmationResponse,
} from '../services/workflowService';

interface SegmentData {
  content: string;
  word_count: number;
  character_count: number;
  segment_index: number;
  // 新增漫画导向字段
  segment_type?: string;
  scene_setting?: string;
  characters?: string;
  emotional_tone?: string;
  key_events?: string[];
  transition_clues?: string[];
  character_descriptions?: Record<string, string[]>;
  scene_elements?: string[];
  visual_keywords?: string[];
  character_importance?: Record<string, boolean>;
  comic_suitability?: number;
  panel_focus?: string;
  visual_focus?: string;
}

interface GenerationImage {
  id: string;
  url: string;
  prompt?: string;
  status: 'generating' | 'completed' | 'error';
}

interface ProjectCharacter {
  id: string;
  name: string;
  description?: string;
  created_at: string;
}

const SegmentedComicGenerationPage: React.FC = () => {
  const { id: projectId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // 状态管理
  const [activeStep, setActiveStep] = useState(0);
  const [selectedNovelFile, setSelectedNovelFile] = useState('');
  const [novelContent, setNovelContent] = useState('');
  const [segments, setSegments] = useState<SegmentData[]>([]);
  const [currentSegmentIndex, setCurrentSegmentIndex] = useState(0);
  const [styleReferenceImages, setStyleReferenceImages] = useState<string[]>([]);
  const [selectedCharacters, setSelectedCharacters] = useState<string[]>([]);
  const [styleRequirements, setStyleRequirements] = useState('');
  const [generationCount, setGenerationCount] = useState(3);
  const [generationImages, setGenerationImages] = useState<GenerationImage[]>([]);
  const [selectedImageIndex, setSelectedImageIndex] = useState<number | null>(null);
  const [previousSegmentImage, setPreviousSegmentImage] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [editableSegmentText, setEditableSegmentText] = useState('');
  const [isUploadingImage, setIsUploadingImage] = useState(false);

  // 分段展开状态管理
  const [expandedSegments, setExpandedSegments] = useState<Set<number>>(new Set());

  // 分段编辑状态
  const [editingSegmentIndex, setEditingSegmentIndex] = useState<number | null>(null);
  const [editingSegmentText, setEditingSegmentText] = useState('');

  // 文件上传 ref
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [notification, setNotification] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'warning';
  }>({
    open: false,
    message: '',
    severity: 'success',
  });

  const [copiedPrompt, setCopiedPrompt] = useState<string>('');

  // 获取项目角色
  const { data: charactersResponse = [] } = useQuery({
    queryKey: ['characters', projectId],
    queryFn: () => characterService.getProjectCharacters(projectId!),
    enabled: !!projectId,
  });

  const characters = Array.isArray(charactersResponse) ? charactersResponse : [];

  // 文本分段API调用
  const segmentMutation = useMutation({
    mutationFn: (request: TextSegmentationRequest) =>
      workflowService.segmentAndPreviewNovel(request),
    onSuccess: (data: TextSegmentationResponse) => {
      setSegments(data.segments);
      setCurrentSegmentIndex(0);
      if (data.segments.length > 0) {
        setEditableSegmentText(data.segments[0].content);
      }
      setActiveStep(1);
      showNotification(`文本成功分段为 ${data.total_segments} 个段落`, 'success');
    },
    onError: (error) => {
      const apiError = handleApiError(error);
      showNotification(apiError.message, 'error');
    },
  });

  // 段落生成API调用
  const generateMutation = useMutation({
    mutationFn: (request: SegmentGenerationRequest) =>
      workflowService.generateSegmentComics(request),
    onSuccess: (data: SegmentGenerationResponse) => {
      // 解析生成的图片 - 修复: 使用generated_images字段而不是images
      const images: GenerationImage[] = (data.generation_result?.generated_images || []).map((img: any, index: number) => {
        // 优化URL处理：优先使用远程URL，本地路径需要转换为可访问的URL
        let imageUrl = img.image_url || img.local_path || '';

        // 如果是本地路径，转换为API访问URL
        if (img.local_path && !img.image_url) {
          // 提取相对路径并转换为API URL
          const relativePath = img.local_path.replace(/.*\/projects\//, '');
          // 使用完整的基础URL
          const baseUrl = window.location.origin;
          imageUrl = `${baseUrl}/projects/${relativePath}`;
        }

        return {
          id: `img_${index}`,
          url: imageUrl,
          prompt: img.prompt_used || '',
          status: img.status === 'success' ? 'completed' as const : 'error' as const,
        };
      });

      setGenerationImages(images);
      setSelectedImageIndex(null);
      setIsGenerating(false); // 重置生成状态
      showNotification(`成功生成 ${data.total_generated} 张图片`, 'success');
    },
    onError: (error) => {
      const apiError = handleApiError(error);
      setIsGenerating(false); // 重置生成状态
      showNotification(apiError.message, 'error');
    },
  });

  // 段落确认API调用
  const confirmMutation = useMutation({
    mutationFn: (request: SegmentConfirmationRequest) =>
      workflowService.confirmSegmentSelection(request),
    onSuccess: (data: SegmentConfirmationResponse) => {
      showNotification(`段落 ${data.segment_index + 1} 已确认`, 'success');

      if (data.has_next_segment && data.next_segment_index !== undefined) {
        // 进入下一段
        setCurrentSegmentIndex(data.next_segment_index);
        setEditableSegmentText(segments[data.next_segment_index].content);
        setGenerationImages([]);
        setSelectedImageIndex(null);
        setPreviousSegmentImage(data.confirmed_image_path || null);
      } else {
        // 所有序列完成
        setActiveStep(4);
        showNotification('所有段落处理完成！漫画生成成功！', 'success');
      }
    },
    onError: (error) => {
      const apiError = handleApiError(error);
      showNotification(apiError.message, 'error');
    },
  });

  // 显示通知
  const showNotification = (message: string, severity: 'success' | 'error' | 'warning') => {
    setNotification({ open: true, message, severity });
  };

  // 关闭通知
  const closeNotification = () => {
    setNotification({ ...notification, open: false });
  };

  // 处理小说选择
  const handleNovelSelect = (filename: string, content: string) => {
    setSelectedNovelFile(filename);
    setNovelContent(content);
  };

  // 分段展开/收起处理
  const handleToggleExpandSegment = (index: number) => {
    const newExpanded = new Set(expandedSegments);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedSegments(newExpanded);
  };

  // 开始编辑分段
  const handleEditSegment = (index: number) => {
    setEditingSegmentIndex(index);
    setEditingSegmentText(segments[index].content);
  };

  // 保存分段编辑
  const handleSaveSegmentEdit = () => {
    if (editingSegmentIndex === null) return;

    const updatedSegments = [...segments];
    updatedSegments[editingSegmentIndex] = {
      ...updatedSegments[editingSegmentIndex],
      content: editingSegmentText,
      character_count: editingSegmentText.length,
      word_count: editingSegmentText.split(/\s+/).filter(word => word.length > 0).length
    };

    setSegments(updatedSegments);
    setEditingSegmentIndex(null);
    setEditingSegmentText('');
    showNotification('分段内容已更新', 'success');
  };

  // 取消编辑
  const handleCancelEdit = () => {
    setEditingSegmentIndex(null);
    setEditingSegmentText('');
  };

  // 开始文本分段
  const handleStartSegmentation = () => {
    if (!novelContent.trim()) {
      showNotification('请先选择小说文件', 'error');
      return;
    }

    segmentMutation.mutate({
      novel_content: novelContent,
      project_name: projectId!,
      target_length: "medium",  // small(200字), medium(300字), large(500字)
      preserve_context: true,
      language: "chinese",     // chinese/english
    });
  };

  // 生成当前段落的组图
  const handleGenerateSegment = () => {
    if (!editableSegmentText.trim()) {
      showNotification('段落文本不能为空', 'error');
      return;
    }

    setIsGenerating(true);
    generateMutation.mutate({
      project_name: projectId!,
      segment_index: currentSegmentIndex,
      segment_text: editableSegmentText,
      style_reference_images: styleReferenceImages,
      selected_characters: selectedCharacters,
      style_requirements: styleRequirements,
      generation_count: generationCount,
      previous_segment_image: previousSegmentImage || undefined,
    });
  };

  // 确认选择的图片
  const handleConfirmSelection = () => {
    if (selectedImageIndex === null) {
      showNotification('请先选择一张图片', 'error');
      return;
    }

    confirmMutation.mutate({
      project_name: projectId!,
      segment_index: currentSegmentIndex,
      selected_image_index: selectedImageIndex,
    });
  };

  // 重新生成当前段落
  const handleRegenerate = () => {
    setGenerationImages([]);
    setSelectedImageIndex(null);
    handleGenerateSegment();
  };

  // 上传画风参考图片
  const handleUploadStyleReference = () => {
    fileInputRef.current?.click();
  };

  // 处理文件选择
  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // 验证文件类型
    if (!file.type.startsWith('image/')) {
      showNotification('请选择图片文件', 'error');
      return;
    }

    // 验证文件大小 (10MB 限制)
    if (file.size > 10 * 1024 * 1024) {
      showNotification('图片文件大小不能超过 10MB', 'error');
      return;
    }

    if (!projectId) {
      showNotification('项目ID不能为空', 'error');
      return;
    }

    setIsUploadingImage(true);
    try {
      const result = await comicService.uploadReferenceImage(projectId, file);
      if (result.success) {
        // 将上传的图片路径添加到参考图片列表
        setStyleReferenceImages(prev => [...prev, result.file_url]);
        showNotification('参考图片上传成功', 'success');
      } else {
        showNotification('参考图片上传失败', 'error');
      }
    } catch (error) {
      const apiError = handleApiError(error);
      showNotification(`上传失败: ${apiError.message}`, 'error');
    } finally {
      setIsUploadingImage(false);
      // 清空文件输入框
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const steps = [
    '选择小说文件',
    '文本分段预览',
    '生成配置',
    '逐段生成漫画',
    '完成',
  ];

  if (segmentMutation.isPending || generateMutation.isPending || confirmMutation.isPending) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            处理中...
          </Typography>
          <LinearProgress />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            正在处理您的请求，请稍候...
          </Typography>
        </Paper>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      {/* 头部 */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <IconButton onClick={() => navigate(-1)} sx={{ mr: 2 }}>
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h4" component="h1">
          智能分段漫画生成
        </Typography>
      </Box>

      {/* 步骤指示器 */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Stepper activeStep={activeStep} alternativeLabel>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>
      </Paper>

      {/* 第一步：选择小说文件 */}
      {activeStep === 0 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            选择小说文件
          </Typography>
          <NovelSelector
            projectId={projectId!}
            selectedNovel={selectedNovelFile}
            onNovelSelect={handleNovelSelect}
            disabled={segmentMutation.isPending}
          />

          {selectedNovelFile && (
            <Box sx={{ mt: 3 }}>
              <Button
                variant="contained"
                size="large"
                onClick={handleStartSegmentation}
                disabled={segmentMutation.isPending}
                startIcon={<PlayArrowIcon />}
              >
                开始分段处理
              </Button>
            </Box>
          )}
        </Paper>
      )}

      {/* 第二步：文本分段预览 */}
      {activeStep === 1 && segments.length > 0 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            文本分段结果
          </Typography>

          <Alert severity="success" sx={{ mb: 3 }}>
            成功将文本分为 {segments.length} 个段落
          </Alert>

          {/* 段落列表 */}
          <Grid container spacing={2}>
            {segments.map((segment, index) => {
              const isExpanded = expandedSegments.has(index);
              const isEditing = editingSegmentIndex === index;
              const isOverLimit = segment.character_count > 400;

              return (
                <Grid item xs={12} md={6} key={index}>
                  <Card
                    variant={index === currentSegmentIndex ? "outlined" : "elevation"}
                    sx={{
                      border: index === currentSegmentIndex ? 2 : 'none',
                      borderColor: isOverLimit ? 'warning.main' :
                                   (index === currentSegmentIndex ? 'primary.main' : 'inherit'),
                      position: 'relative'
                    }}
                  >
                    {isOverLimit && (
                      <Box
                        sx={{
                          position: 'absolute',
                          top: 8,
                          right: 8,
                          backgroundColor: 'warning.main',
                          color: 'white',
                          borderRadius: 1,
                          px: 1,
                          py: 0.25,
                          fontSize: 10,
                          fontWeight: 'bold',
                          zIndex: 1
                        }}
                      >
                        超限
                      </Box>
                    )}

                    <CardContent sx={{ pb: 1 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                        <Typography variant="subtitle2" color="primary" sx={{ fontWeight: 'bold' }}>
                          段落 {index + 1}
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 0.5 }}>
                          <IconButton
                            size="small"
                            onClick={() => handleToggleExpandSegment(index)}
                            sx={{ p: 0.5 }}
                          >
                            {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                          </IconButton>
                          <IconButton
                            size="small"
                            onClick={() => handleEditSegment(index)}
                            sx={{ p: 0.5 }}
                          >
                            <EditIcon fontSize="small" />
                          </IconButton>
                        </Box>
                      </Box>

                      {isEditing ? (
                        <TextField
                          multiline
                          fullWidth
                          minRows={4}
                          maxRows={10}
                          value={editingSegmentText}
                          onChange={(e) => setEditingSegmentText(e.target.value)}
                          placeholder="编辑分段内容..."
                          sx={{ mb: 1 }}
                          error={editingSegmentText.length > 400}
                          helperText={
                            editingSegmentText.length > 400
                              ? `字符数超限 (${editingSegmentText.length}/400)`
                              : `字符数: ${editingSegmentText.length}/400`
                          }
                        />
                      ) : (
                        <Typography
                          variant="body2"
                          sx={{
                            mb: 1,
                            maxHeight: isExpanded ? 'none' : 60,
                            overflow: isExpanded ? 'visible' : 'hidden',
                            position: 'relative',
                            '&:after': !isExpanded && segment.content.length > 100 ? {
                              content: '""',
                              position: 'absolute',
                              bottom: 0,
                              left: 0,
                              right: 0,
                              height: 20,
                              background: 'linear-gradient(transparent, white)'
                            } : {}
                          }}
                        >
                          {isExpanded ? segment.content : segment.content.slice(0, 100)}
                          {!isExpanded && segment.content.length > 100 && '...'}
                        </Typography>
                      )}

                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography
                          variant="caption"
                          color={isOverLimit ? 'warning.main' : 'text.secondary'}
                          sx={{
                            fontWeight: isOverLimit ? 'bold' : 'normal'
                          }}
                        >
                          字符数: {segment.character_count} | 词数: {segment.word_count}
                          {isOverLimit && ' (超出400字符限制)'}
                        </Typography>

                        {/* 漫画要素分析信息 */}
                        {isExpanded && (
                          <Box sx={{ mt: 1 }}>
                            {/* 场景设定 */}
                            {segment.scene_setting && (
                              <Box sx={{ mb: 1 }}>
                                <Typography variant="caption" color="primary" sx={{ fontWeight: 'bold' }}>
                                  场景:
                                </Typography>
                                <Typography variant="caption" sx={{ ml: 0.5 }}>
                                  {segment.scene_setting}
                                </Typography>
                              </Box>
                            )}

                            {/* 角色信息 */}
                            {segment.characters && (
                              <Box sx={{ mb: 1 }}>
                                <Typography variant="caption" color="primary" sx={{ fontWeight: 'bold' }}>
                                  角色:
                                </Typography>
                                <Typography variant="caption" sx={{ ml: 0.5 }}>
                                  {segment.characters}
                                </Typography>
                              </Box>
                            )}

                            {/* 环境要素 */}
                            {segment.scene_elements && segment.scene_elements.length > 0 && (
                              <Box sx={{ mb: 1 }}>
                                <Typography variant="caption" color="primary" sx={{ fontWeight: 'bold' }}>
                                  环境要素:
                                </Typography>
                                <Typography variant="caption" sx={{ ml: 0.5 }}>
                                  {segment.scene_elements.join('、')}
                                </Typography>
                              </Box>
                            )}

                            {/* 视觉关键词 */}
                            {segment.visual_keywords && segment.visual_keywords.length > 0 && (
                              <Box sx={{ mb: 1 }}>
                                <Typography variant="caption" color="primary" sx={{ fontWeight: 'bold' }}>
                                  视觉关键词:
                                </Typography>
                                <Typography variant="caption" sx={{ ml: 0.5 }}>
                                  {segment.visual_keywords.join('、')}
                                </Typography>
                              </Box>
                            )}

                            {/* 情感基调 */}
                            {segment.emotional_tone && (
                              <Box sx={{ mb: 1 }}>
                                <Typography variant="caption" color="primary" sx={{ fontWeight: 'bold' }}>
                                  情感基调:
                                </Typography>
                                <Typography variant="caption" sx={{ ml: 0.5 }}>
                                  {segment.emotional_tone}
                                </Typography>
                              </Box>
                            )}

                            {/* 关键事件 */}
                            {segment.key_events && segment.key_events.length > 0 && (
                              <Box sx={{ mb: 1 }}>
                                <Typography variant="caption" color="primary" sx={{ fontWeight: 'bold' }}>
                                  关键事件:
                                </Typography>
                                <Typography variant="caption" sx={{ ml: 0.5 }}>
                                  {segment.key_events.join('、')}
                                </Typography>
                              </Box>
                            )}

                            {/* 视觉焦点 */}
                            {segment.visual_focus && (
                              <Box sx={{ mb: 1 }}>
                                <Typography variant="caption" color="primary" sx={{ fontWeight: 'bold' }}>
                                  视觉焦点:
                                </Typography>
                                <Typography variant="caption" sx={{ ml: 0.5 }}>
                                  {segment.visual_focus}
                                </Typography>
                              </Box>
                            )}

                            {/* 画面焦点建议 */}
                            {segment.panel_focus && (
                              <Box sx={{ mb: 1 }}>
                                <Typography variant="caption" color="success.main" sx={{ fontWeight: 'bold' }}>
                                  画面焦点建议:
                                </Typography>
                                <Typography variant="caption" sx={{ ml: 0.5 }}>
                                  {segment.panel_focus}
                                </Typography>
                              </Box>
                            )}

                                                      </Box>
                        )}

                        {isEditing && (
                          <Box sx={{ display: 'flex', gap: 0.5 }}>
                            <IconButton
                              size="small"
                              onClick={handleSaveSegmentEdit}
                              disabled={editingSegmentText.length > 400}
                              color="primary"
                            >
                              <SaveIcon fontSize="small" />
                            </IconButton>
                            <IconButton
                              size="small"
                              onClick={handleCancelEdit}
                            >
                              <CloseIcon fontSize="small" />
                            </IconButton>
                          </Box>
                        )}
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              );
            })}
          </Grid>

          <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
            <Button
              variant="contained"
              onClick={() => setActiveStep(2)}
              startIcon={<PlayArrowIcon />}
            >
              进入生成配置
            </Button>
            <Button
              variant="outlined"
              onClick={() => {
                setSegments([]);
                setActiveStep(0);
              }}
            >
              重新分段
            </Button>
          </Box>
        </Paper>
      )}

      {/* 第三步：生成配置 */}
      {activeStep === 2 && segments.length > 0 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            生成配置
          </Typography>

          <Alert severity="info" sx={{ mb: 3 }}>
            请在开始生成前配置风格参考图片、角色选择和生成参数。这些配置将用于后续所有段落的生成。
          </Alert>

          <Grid container spacing={3}>
            {/* 左侧：配置选项 */}
            <Grid item xs={12} md={8}>
              {/* 风格参考图片上传 */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle1" gutterBottom>
                  风格参考图片（可选）
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  上传参考图片来统一漫画风格，不上传则使用默认风格
                </Typography>

                {/* 隐藏的文件输入框 */}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleFileSelect}
                  style={{ display: 'none' }}
                />

                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                  <Button
                    variant="outlined"
                    startIcon={<UploadIcon />}
                    onClick={handleUploadStyleReference}
                    disabled={isUploadingImage}
                  >
                    {isUploadingImage ? '上传中...' : '上传参考图片'}
                  </Button>

                  {isUploadingImage && (
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <LinearProgress sx={{ width: 100 }} />
                    </Box>
                  )}
                </Box>

                {styleReferenceImages.length > 0 && (
                  <Box>
                    <Typography variant="caption" color="success.main" sx={{ mb: 1, display: 'block' }}>
                      已上传 {styleReferenceImages.length} 张参考图片
                    </Typography>

                    {/* 参考图片预览 */}
                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                      {styleReferenceImages.map((imagePath, index) => (
                        <Chip
                          key={index}
                          label={`参考图片 ${index + 1}`}
                          onDelete={() => {
                            setStyleReferenceImages(prev => prev.filter((_, i) => i !== index));
                          }}
                          color="primary"
                          variant="outlined"
                          size="small"
                        />
                      ))}
                    </Box>
                  </Box>
                )}
              </Box>

              {/* 角色选择 */}
              {characters.length > 0 && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle1" gutterBottom>
                    选择角色（可选）
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    选择要在漫画中使用的角色，不选择则不使用任何特定角色
                  </Typography>

                  {/* 角色卡片网格 */}
                  <Grid container spacing={2} sx={{ mb: 2 }}>
                    {characters.map((character: ProjectCharacter) => (
                      <Grid item xs={12} sm={6} md={4} key={character.id}>
                        <Card
                          sx={{
                            cursor: 'pointer',
                            border: selectedCharacters.includes(character.id) ? '2px solid' : '1px solid',
                            borderColor: selectedCharacters.includes(character.id) ? 'primary.main' : 'grey.300',
                            '&:hover': {
                              boxShadow: 2,
                              borderColor: 'primary.light'
                            }
                          }}
                          onClick={() => {
                            if (selectedCharacters.includes(character.id)) {
                              setSelectedCharacters(prev => prev.filter(id => id !== character.id));
                            } else {
                              setSelectedCharacters(prev => [...prev, character.id]);
                            }
                          }}
                        >
                          <CardContent sx={{ pb: 1 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                              {/* 角色卡图片 */}
                              <Box sx={{ width: 60, height: 60, bgcolor: 'grey.200', borderRadius: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <CharacterCardImage
                                  projectId={projectId!}
                                  characterName={character.name}
                                  size="small"
                                />
                              </Box>

                              {/* 角色信息 */}
                              <Box sx={{ flex: 1 }}>
                                <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                                  {character.name}
                                </Typography>
                                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                                  {character.description || '暂无描述'}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  创建于: {new Date(character.created_at).toLocaleDateString('zh-CN')}
                                </Typography>
                              </Box>

                              {/* 选择指示器 */}
                              <Box>
                                {selectedCharacters.includes(character.id) ? (
                                  <CheckCircleIcon color="primary" />
                                ) : (
                                  <RadioButtonUncheckedIcon color="disabled" />
                                )}
                              </Box>
                            </Box>
                          </CardContent>
                        </Card>
                      </Grid>
                    ))}
                  </Grid>

                  {/* 已选择的角色显示 */}
                  {selectedCharacters.length > 0 && (
                    <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                      <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                        已选择 {selectedCharacters.length} 个角色:
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                        {selectedCharacters.map(characterId => {
                          const character = characters.find(c => c.id === characterId);
                          return character ? (
                            <Chip
                              key={characterId}
                              label={character.name}
                              onDelete={() => {
                                setSelectedCharacters(prev => prev.filter(id => id !== characterId));
                              }}
                              color="primary"
                              size="small"
                            />
                          ) : null;
                        })}
                      </Box>
                    </Box>
                  )}
                </Box>
              )}

              {/* 生成配置 */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle1" gutterBottom>
                  生成参数配置
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      type="number"
                      label="生成数量"
                      value={generationCount}
                      onChange={(e) => setGenerationCount(parseInt(e.target.value) || 3)}
                      inputProps={{ min: 1, max: 5 }}
                      helperText="每个段落生成的图片数量"
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="风格要求"
                      value={styleRequirements}
                      onChange={(e) => setStyleRequirements(e.target.value)}
                      helperText="描述想要的特定风格，如'暗黑风格'、'萌系'等"
                      size="small"
                    />
                  </Grid>
                </Grid>
              </Box>

              {/* 开始生成按钮 */}
              <Box sx={{ display: 'flex', gap: 2 }}>
                <Button
                  variant="contained"
                  size="large"
                  onClick={() => setActiveStep(3)}
                  startIcon={<PlayArrowIcon />}
                >
                  开始生成第一段漫画
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => setActiveStep(1)}
                >
                  返回分段预览
                </Button>
              </Box>
            </Grid>

            {/* 右侧：配置预览和说明 */}
            <Grid item xs={12} md={4}>
              <Paper variant="outlined" sx={{ p: 2, backgroundColor: 'grey.50' }}>
                <Typography variant="subtitle2" gutterBottom>
                  配置预览
                </Typography>

                {/* 参考图片预览 */}
                <Box sx={{ mb: 2 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                    参考图片：{styleReferenceImages.length} 张
                  </Typography>
                  {styleReferenceImages.length > 0 ? (
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                      {styleReferenceImages.slice(0, 3).map((imagePath, index) => (
                        <Box
                          key={index}
                          sx={{
                            width: 40,
                            height: 40,
                            bgcolor: 'grey.300',
                            borderRadius: 0.5,
                            overflow: 'hidden',
                            border: '1px solid',
                            borderColor: 'grey.400',
                            position: 'relative',
                          }}
                        >
                          <img
                            src={imagePath.startsWith('http') ? imagePath : `http://localhost:8000${imagePath}`}
                            alt={`参考图片 ${index + 1}`}
                            style={{
                              width: '100%',
                              height: '100%',
                              objectFit: 'cover',
                            }}
                            onError={(e) => {
                              // 图片加载失败时显示占位符
                              const target = e.target as HTMLImageElement;
                              target.style.display = 'none';
                              const placeholder = target.nextElementSibling as HTMLElement;
                              if (placeholder) {
                                placeholder.style.display = 'flex';
                              }
                            }}
                          />
                          <Box
                            sx={{
                              width: '100%',
                              height: '100%',
                              display: 'none',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontSize: 10,
                              color: 'text.secondary',
                              bgcolor: 'grey.300',
                            }}
                          >
                            <ImageIcon sx={{ fontSize: 16 }} />
                          </Box>
                        </Box>
                      ))}
                      {styleReferenceImages.length > 3 && (
                        <Typography variant="caption" color="text.secondary">
                          +{styleReferenceImages.length - 3}
                        </Typography>
                      )}
                    </Box>
                  ) : (
                    <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                      未上传参考图片
                    </Typography>
                  )}
                </Box>

                {/* 选中角色预览 */}
                <Box sx={{ mb: 2 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                    选中角色：{selectedCharacters.length} 个
                  </Typography>
                  {selectedCharacters.length > 0 ? (
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                      {selectedCharacters.slice(0, 2).map(characterId => {
                        const character = characters.find(c => c.id === characterId);
                        return character ? (
                          <Chip
                            key={characterId}
                            label={character.name}
                            size="small"
                            variant="outlined"
                          />
                        ) : null;
                      })}
                      {selectedCharacters.length > 2 && (
                        <Typography variant="caption" color="text.secondary">
                          +{selectedCharacters.length - 2}
                        </Typography>
                      )}
                    </Box>
                  ) : (
                    <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                      未选择角色
                    </Typography>
                  )}
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Typography variant="caption" color="text.secondary">
                    生成数量：{generationCount} 张/段
                  </Typography>
                </Box>

                {styleRequirements && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="caption" color="text.secondary">
                      风格要求：{styleRequirements.length > 30
                        ? `${styleRequirements.substring(0, 30)}...`
                        : styleRequirements}
                    </Typography>
                  </Box>
                )}

                {/* 配置状态指示 */}
                <Box sx={{ mt: 2, p: 1.5, bgcolor: 'background.paper', borderRadius: 1 }}>
                  <Typography variant="caption" sx={{ fontWeight: 'bold', display: 'block', mb: 1 }}>
                    配置完整度
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      参考图片:
                    </Typography>
                    {styleReferenceImages.length > 0 ? (
                      <CheckCircleIcon sx={{ fontSize: 12, color: 'success.main' }} />
                    ) : (
                      <RadioButtonUncheckedIcon sx={{ fontSize: 12, color: 'grey.400' }} />
                    )}
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      选择角色:
                    </Typography>
                    {selectedCharacters.length > 0 ? (
                      <CheckCircleIcon sx={{ fontSize: 12, color: 'success.main' }} />
                    ) : (
                      <RadioButtonUncheckedIcon sx={{ fontSize: 12, color: 'grey.400' }} />
                    )}
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      风格要求:
                    </Typography>
                    {styleRequirements ? (
                      <CheckCircleIcon sx={{ fontSize: 12, color: 'success.main' }} />
                    ) : (
                      <RadioButtonUncheckedIcon sx={{ fontSize: 12, color: 'grey.400' }} />
                    )}
                  </Box>
                </Box>

                <Alert severity="info" sx={{ mt: 2 }}>
                  <Typography variant="caption">
                    配置保存后将用于所有段落的生成，确保风格统一性。
                  </Typography>
                </Alert>
              </Paper>
            </Grid>
          </Grid>
        </Paper>
      )}

      {/* 第四步：逐段生成漫画 */}
      {activeStep === 3 && segments.length > 0 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            段落 {currentSegmentIndex + 1} 漫画生成
          </Typography>

          <Grid container spacing={3}>
            {/* 左侧：段落预览和控制 */}
            <Grid item xs={12} md={6}>
              {/* 前情提要显示 */}
              {previousSegmentImage && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle1" gutterBottom color="primary">
                    前情提要
                  </Typography>
                  <Paper variant="outlined" sx={{ p: 2, backgroundColor: 'blue.50' }}>
                    <Box
                      component="img"
                      src={previousSegmentImage.startsWith('http') ? previousSegmentImage : `http://localhost:8000${previousSegmentImage}`}
                      alt="前情提要"
                      sx={{
                        width: '100%',
                        maxHeight: 150,
                        objectFit: 'contain',
                        borderRadius: 1,
                        border: '1px solid',
                        borderColor: 'blue.200'
                      }}
                      onError={(e) => {
                        e.currentTarget.src = '/placeholder-image.png';
                      }}
                    />
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                      上一段确认的画面将作为剧情连贯性参考
                    </Typography>
                  </Paper>
                </Box>
              )}

              {/* 当前段落信息 */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle1" gutterBottom>
                  段落 {currentSegmentIndex + 1} / {segments.length}
                </Typography>
                <Paper variant="outlined" sx={{ p: 2, backgroundColor: 'grey.50' }}>
                  <TextField
                    multiline
                    fullWidth
                    minRows={3}
                    maxRows={8}
                    value={editableSegmentText}
                    onChange={(e) => setEditableSegmentText(e.target.value)}
                    variant="outlined"
                    size="small"
                    placeholder="编辑当前段落的文本内容..."
                    disabled={isGenerating}
                    sx={{
                      '& .MuiOutlinedInput-root': {
                        fontFamily: 'monospace',
                        fontSize: '0.875rem',
                        backgroundColor: 'white',
                        borderRadius: 1,
                      }
                    }}
                  />
                  <Box sx={{ mt: 1, display: 'flex', justifyContent: 'flex-end' }}>
                    <Button
                      size="small"
                      variant="outlined"
                      disabled={isGenerating}
                      onClick={() => {
                        // 这里可以添加保存编辑后的文本到后端的逻辑
                        console.log('保存编辑后的文本:', editableSegmentText);
                      }}
                      sx={{ fontSize: '0.75rem' }}
                    >
                      保存编辑
                    </Button>
                  </Box>
                </Paper>
              </Box>

              {/* 生成状态显示 */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle1" gutterBottom>
                  当前配置
                </Typography>
                <Paper variant="outlined" sx={{ p: 2, backgroundColor: 'grey.50' }}>
                  <Grid container spacing={1}>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        生成数量：{generationCount} 张
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        选中角色：{selectedCharacters.length} 个
                      </Typography>
                    </Grid>
                    <Grid item xs={12}>
                      <Typography variant="caption" color="text.secondary">
                        参考图片：{styleReferenceImages.length} 张
                      </Typography>
                    </Grid>
                    {previousSegmentImage && (
                      <Grid item xs={12}>
                        <Typography variant="caption" color="primary">
                          📗 前情提要：已关联
                        </Typography>
                      </Grid>
                    )}
                    {styleRequirements && (
                      <Grid item xs={12}>
                        <Typography variant="caption" color="text.secondary">
                          风格：{styleRequirements}
                        </Typography>
                      </Grid>
                    )}
                  </Grid>
                  <Grid item xs={12}>
                    <Typography variant="caption" color="info.main" sx={{ mt: 1, display: 'block' }}>
                      💡 优先使用您的编辑文本，AI分析数据仅作补充
                    </Typography>
                  </Grid>
                </Paper>
              </Box>

              {/* 控制按钮 */}
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Button
                  variant="contained"
                  size="large"
                  onClick={handleGenerateSegment}
                  disabled={isGenerating || !editableSegmentText.trim()}
                  startIcon={isGenerating ? <RefreshIcon /> : <ImageIcon />}
                >
                  {isGenerating ? '正在生成...' : '生成组图'}
                </Button>

                {generationImages.length > 0 && (
                  <Box sx={{ display: 'flex', gap: 2 }}>
                    <Button
                      variant="outlined"
                      onClick={handleRegenerate}
                      startIcon={<RefreshIcon />}
                      disabled={isGenerating}
                    >
                      重新生成
                    </Button>
                    <Button
                      variant="outlined"
                      onClick={() => setActiveStep(2)}
                    >
                      修改配置
                    </Button>
                  </Box>
                )}
              </Box>
            </Grid>

            {/* 右侧：生成的图片 */}
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle1" gutterBottom>
                生成的图片
              </Typography>

              {generationImages.length === 0 ? (
                <Box sx={{
                  p: 4,
                  border: '2px dashed #ccc',
                  borderRadius: 2,
                  textAlign: 'center',
                  color: 'text.secondary'
                }}>
                  <ImageIcon sx={{ fontSize: 48, mb: 2 }} />
                  <Typography>
                    点击"生成组图"开始生成漫画图片
                  </Typography>
                </Box>
              ) : (
                <Grid container spacing={2}>
                  {generationImages.map((image, index) => (
                    <Grid item xs={6} key={image.id}>
                      <Card
                        sx={{
                          cursor: 'pointer',
                          border: selectedImageIndex === index ? 2 : 1,
                          borderColor: selectedImageIndex === index ? 'primary.main' : 'grey.300'
                        }}
                        onClick={() => setSelectedImageIndex(index)}
                      >
                        <CardMedia
                          component="img"
                          height="150"
                          image={image.url}
                          alt={`生成图片 ${index + 1}`}
                          sx={{
                            objectFit: 'cover',
                            backgroundColor: 'grey.100'
                          }}
                          onError={(e) => {
                            // 图片加载失败时显示占位符
                            const target = e.target as HTMLImageElement;
                            target.style.display = 'none';
                            const placeholder = target.nextElementSibling as HTMLElement;
                            if (placeholder) {
                              placeholder.style.display = 'flex';
                            }
                          }}
                        />
                        {/* 图片加载失败占位符 */}
                        <Box
                          sx={{
                            width: '100%',
                            height: '150px',
                            display: 'none',
                            alignItems: 'center',
                            justifyContent: 'center',
                            flexDirection: 'column',
                            backgroundColor: 'grey.100',
                            color: 'grey.500'
                          }}
                        >
                          <BrokenImageIcon sx={{ fontSize: 40, mb: 1 }} />
                          <Typography variant="caption">
                            图片加载失败
                          </Typography>
                        </Box>
                        <CardContent sx={{ p: 1 }}>
                          <Typography variant="caption" display="block">
                            图片 {index + 1}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                            {image.status === 'completed' ? '✓ 成功' : '✗ 失败'}
                          </Typography>
                          {selectedImageIndex === index && (
                            <Chip
                              label="已选择"
                              color="primary"
                              size="small"
                              sx={{ mt: 1 }}
                            />
                          )}
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              )}

              {selectedImageIndex !== null && (
                <Box sx={{ mt: 3 }}>
                  <Button
                    variant="contained"
                    color="success"
                    onClick={handleConfirmSelection}
                    disabled={confirmMutation.isPending}
                    startIcon={<CheckCircleIcon />}
                    fullWidth
                  >
                    确认选择
                  </Button>
                </Box>
              )}
            </Grid>
          </Grid>
        </Paper>
      )}

      {/* 第五步：完成 */}
      {activeStep === 4 && (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <CheckCircleIcon sx={{ fontSize: 64, color: 'success.main', mb: 2 }} />
          <Typography variant="h5" gutterBottom>
            漫画生成完成！
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            您已成功处理所有 {segments.length} 个段落，生成了完整的漫画。
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
            <Button
              variant="contained"
              onClick={() => {
                // 重置状态，允许重新开始
                setActiveStep(0);
                setSegments([]);
                setCurrentSegmentIndex(0);
                setGenerationImages([]);
                setSelectedImageIndex(null);
                setPreviousSegmentImage(null);
              }}
            >
              生成新的漫画
            </Button>
            <Button
              variant="outlined"
              onClick={() => navigate(-1)}
            >
              返回项目
            </Button>
          </Box>
        </Paper>
      )}

      {/* 通知 */}
      <Snackbar
        open={notification.open}
        autoHideDuration={6000}
        onClose={closeNotification}
      >
        <Alert onClose={closeNotification} severity={notification.severity}>
          {notification.message}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default SegmentedComicGenerationPage;