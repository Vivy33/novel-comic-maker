import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Paper,
  Button,
  Grid,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
  Snackbar,
  Tabs,
  Tab,
  Chip,
  IconButton,
  Tooltip,
  LinearProgress,
  Card,
  CardMedia,
  CardContent,
  CardActions,
  Divider,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Upload as UploadIcon,
  Image as ImageIcon,
  Download as DownloadIcon,
  Refresh as RefreshIcon,
  Visibility as VisibilityIcon,
  AutoFixHigh as AutoFixHighIcon,
  Bookmark as BookmarkIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
} from '@mui/icons-material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { novelService, handleApiError } from '../services';
import { CoverGenerationResponse } from '../services';
import { default as coverService } from '../services/coverService';
import NovelSelector from '../components/NovelSelector';

interface Cover {
  cover_id: string;
  title: string;
  description: string;
  image_url: string;
  local_path?: string;
  cover_type: string;
  related_novel?: string;
  status: string;
  created_at: string;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`cover-generation-tabpanel-${index}`}
      aria-labelledby={`cover-generation-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const CoverGenerationPage: React.FC = () => {
  const { id: projectId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // 状态管理
  const [tabValue, setTabValue] = useState(0);
  const [coverType, setCoverType] = useState<'project' | 'chapter'>('project');
  const [selectedNovel, setSelectedNovel] = useState('');
  const [novelContent, setNovelContent] = useState('');
  const [coverPrompt, setCoverPrompt] = useState('');
  const [coverSize, setCoverSize] = useState('1024x1024');
  const [referenceImage, setReferenceImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageLoading, setImageLoading] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [fileDialogOpen, setFileDialogOpen] = useState(false);
  const [notification, setNotification] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'warning';
  }>({
    open: false,
    message: '',
    severity: 'success',
  });

  
  // 页面初始化
  React.useEffect(() => {
    // 添加全局错误捕获
    const handleError = (event: ErrorEvent) => {
      console.error('页面发生错误:', event.error);
      showNotification('页面发生错误，请刷新重试', 'error');
    };

    window.addEventListener('error', handleError);

    return () => {
      window.removeEventListener('error', handleError);
    };
  }, [projectId]);

  // 清除图片选择
  const clearImageSelection = () => {
    setImagePreview(null);
    setReferenceImage(null);
    setImageLoading(false);
    setImageError(false);
    setFileDialogOpen(false);
    showNotification('已清除参考图片', 'success');
  };

  
  // 统一的文件选择处理函数
  const handleFileSelectClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    // 防止重复点击
    if (imageLoading || fileDialogOpen) {
      return;
    }

    // 设置对话框状态
    setFileDialogOpen(true);

    // 创建临时input元素
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = (event) => {
      handleImageSelect(event as any);
    };

    // 监听对话框关闭（用户取消选择）
    const handleCancel = () => {
      setTimeout(() => {
        if (fileDialogOpen && !imageLoading) {
          setFileDialogOpen(false);
        }
      }, 100);
    };

    // 添加取消监听
    input.addEventListener('cancel', handleCancel);
    document.addEventListener('focus', handleCancel, true);

    input.click();

    // 清理监听器
    setTimeout(() => {
      input.removeEventListener('cancel', handleCancel);
      document.removeEventListener('focus', handleCancel, true);
    }, 1000);
  };

  // 拖拽上传处理函数
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();

    const files = e.dataTransfer.files;

    if (files && files.length > 0) {
      const file = files[0];

      // 创建一个模拟的input事件对象
      const mockInput = document.createElement('input');
      mockInput.type = 'file';
      mockInput.files = files;

      const mockEvent = {
        target: mockInput,
        currentTarget: mockInput,
        preventDefault: () => {},
        stopPropagation: () => {},
        nativeEvent: new Event('change')
      } as any;

      handleImageSelect(mockEvent);
    }
  };

  // 处理图片加载状态
  const handleImageLoadStart = () => {
    setImageLoading(true);
    setImageError(false);
  };

  const handleImageLoad = () => {
    setImageLoading(false);
    setImageError(false);
  };

  const handleImageError = () => {
    setImageLoading(false);
    setImageError(true);
    showNotification('图片预览失败', 'error');
  };

  // 获取项目封面列表
  const { data: coversData, isLoading: coversLoading } = useQuery({
    queryKey: ['project-covers', projectId],
    queryFn: () => projectId ? coverService.getProjectCovers(projectId) : Promise.resolve({ success: true, covers: [], total_count: 0 }),
    enabled: !!projectId,
  });

  // 生成封面
  const generateMutation = useMutation({
    mutationFn: (data: {
      coverType: 'project' | 'chapter';
      novelFilename?: string;
      coverPrompt: string;
      coverSize: string;
      referenceImage?: File;
    }) =>
      coverService.generateCover({
        projectId: projectId!,
        coverType: data.coverType,
        novelFilename: data.novelFilename,
        coverPrompt: data.coverPrompt,
        coverSize: data.coverSize,
        referenceImage: data.referenceImage,
      }),
    onSuccess: (response: CoverGenerationResponse) => {
      if (response.success) {
        showNotification('封面生成成功！', 'success');
        // 重置表单
        setCoverPrompt('');
        setReferenceImage(null);
        setImagePreview(null);
        // 刷新封面列表
        queryClient.invalidateQueries({ queryKey: ['project-covers', projectId] });
      }
    },
    onError: (error) => {
      const apiError = handleApiError(error);
      showNotification(`生成失败: ${apiError.message}`, 'error');
    },
  });

  // 删除封面
  const deleteMutation = useMutation({
    mutationFn: (coverId: string) => coverService.deleteCover(projectId!, coverId),
    onSuccess: () => {
      showNotification('封面删除成功', 'success');
      queryClient.invalidateQueries({ queryKey: ['project-covers', projectId] });
    },
    onError: (error) => {
      const apiError = handleApiError(error);
      showNotification(`删除失败: ${apiError.message}`, 'error');
    },
  });

  // 处理封面类型切换
  const handleCoverTypeChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    setCoverType(newValue === 0 ? 'project' : 'chapter');
    setSelectedNovel('');
    setNovelContent('');
    // 重置封面描述，让用户重新填写
    setCoverPrompt('');
  };

  // 处理小说选择
  const handleNovelSelect = (filename: string, content: string) => {
    setSelectedNovel(filename);
    setNovelContent(content);
  };

  // 处理参考图片选择
  const handleImageSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    try {
      // 防止重复处理
      if (imageLoading || fileDialogOpen) {
        return;
      }

      const file = event.target.files?.[0];

      if (!file) {
        setFileDialogOpen(false);
        return;
      }

      // 基本类型验证
      if (!file.type.startsWith('image/')) {
        showNotification(`请选择图片文件，当前类型: ${file.type}`, 'error');
        setFileDialogOpen(false);
        return;
      }

      setFileDialogOpen(false); // 关闭对话框状态
      setImageLoading(true);   // 设置加载状态
      showNotification('正在处理图片...', 'success');

      // 设置文件引用
      setReferenceImage(file);

      // FileReader 处理
      const reader = new FileReader();

      reader.onload = (e) => {
        const result = e.target?.result as string;

        if (result && typeof result === 'string') {
          setImagePreview(result);
          setImageLoading(false);
          showNotification(`图片已加载: ${file.name}`, 'success');
        } else {
          setImageLoading(false);
          showNotification('图片处理失败', 'error');
        }
      };

      reader.onerror = (error) => {
        console.error('图片读取失败:', error);
        setImageLoading(false);
        setFileDialogOpen(false);
        showNotification('图片读取失败', 'error');
      };

      reader.readAsDataURL(file);

    } catch (error) {
      console.error('图片处理出现错误:', error);
      setImageLoading(false);
      setFileDialogOpen(false);
      showNotification('图片处理出现错误', 'error');
    }
  };

  // 处理生成
  const handleGenerate = () => {
    // 增强验证：检查图片状态
    if (referenceImage && imageError) {
      showNotification('参考图片加载失败，请重新选择图片', 'error');
      return;
    }

    if (referenceImage && imageLoading) {
      showNotification('图片还在加载中，请稍候', 'warning');
      return;
    }

    if (coverType === 'chapter' && !selectedNovel) {
      showNotification('请选择小说文件', 'error');
      return;
    }

    if (!coverPrompt.trim()) {
      showNotification('请输入封面描述', 'error');
      return;
    }

    // 检查图片文件大小限制（10MB）
    if (referenceImage && referenceImage.size > 10 * 1024 * 1024) {
      showNotification('图片文件过大，请选择小于10MB的图片', 'error');
      return;
    }

    // 显示生成开始的通知
    showNotification('开始生成封面...', 'success');

    generateMutation.mutate({
      coverType,
      novelFilename: coverType === 'chapter' ? selectedNovel : undefined,
      coverPrompt: coverPrompt.trim(),
      coverSize,
      referenceImage: referenceImage || undefined,
    });
  };

  // 处理删除
  const handleDelete = (coverId: string) => {
    if (window.confirm('确定要删除这个封面吗？')) {
      deleteMutation.mutate(coverId);
    }
  };

  // 下载封面
  const handleDownload = async (cover: any) => {
    try {
      const blob = await coverService.downloadCover(cover.image_url);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${cover.title}.png`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      showNotification('封面下载成功', 'success');
    } catch (error) {
      showNotification('下载失败', 'error');
    }
  };

  // 显示通知
  const showNotification = (message: string, severity: 'success' | 'error' | 'warning') => {
    setNotification({ open: true, message, severity });
  };

  // 关闭通知
  const closeNotification = () => {
    setNotification({ ...notification, open: false });
  };

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 4 }}>
        {/* 页面标题 */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Button
              startIcon={<ArrowBackIcon />}
              onClick={() => navigate(`/project/${projectId}`)}
              sx={{ mr: 2 }}
            >
              返回项目
            </Button>
            <Typography variant="h4" component="h1">
              封面生成
            </Typography>
          </Box>
        </Box>

        <Grid container spacing={3}>
          {/* 左侧：生成配置 */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom sx={{ p: 3, pb: 0 }}>
                封面配置
              </Typography>

              {/* 封面类型选择 */}
              <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                <Tabs value={tabValue} onChange={handleCoverTypeChange}>
                  <Tab label="项目封面" icon={<BookmarkIcon />} />
                  <Tab label="章节封面" icon={<ImageIcon />} />
                </Tabs>
              </Box>

              {/* 项目封面配置 */}
              <TabPanel value={tabValue} index={0}>
                <Alert severity="info" sx={{ mb: 3 }}>
                  项目封面基于整个项目信息生成，适合作为漫画系列的主封面。
                </Alert>

                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  label="封面描述"
                  placeholder="描述您想要的封面风格和内容，如'科幻风格，主角站在城市之巅'..."
                  value={coverPrompt}
                  onChange={(e) => setCoverPrompt(e.target.value)}
                  sx={{ mb: 3 }}
                />
              </TabPanel>

              {/* 章节封面配置 */}
              <TabPanel value={tabValue} index={1}>
                <Alert severity="info" sx={{ mb: 3 }}>
                  章节封面基于选定小说的内容生成，适合为单个章节创建专属封面。
                  <strong>请先选择小说文件，然后填写封面描述。</strong>
                </Alert>

                {/* 小说选择 */}
                <NovelSelector
                  projectId={projectId!}
                  selectedNovel={selectedNovel}
                  onNovelSelect={handleNovelSelect}
                />

                {!selectedNovel && (
                  <Alert severity="warning" sx={{ mb: 2 }}>
                    ⚠️ 请先在上方选择小说文件，然后才能填写封面描述
                  </Alert>
                )}

                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  label="封面描述"
                  placeholder="描述您想要的封面风格和内容，如'科幻风格，主角站在城市之巅'..."
                  value={coverPrompt}
                  onChange={(e) => setCoverPrompt(e.target.value)}
                  sx={{
                    mb: 3,
                    mt: 3,
                    '& .MuiInputBase-input.Mui-disabled': {
                      WebkitTextFillColor: 'text.secondary',
                      color: 'text.secondary',
                    },
                    '& .Mui-disabled .MuiInputBase-input': {
                      cursor: 'not-allowed',
                    },
                  }}
                  disabled={!selectedNovel}
                  helperText={
                    !selectedNovel
                      ? `请先在上方选择小说文件 (当前状态: ${selectedNovel ? '已选择' : '未选择'})`
                      : `已选择: ${selectedNovel.substring(selectedNovel.lastIndexOf('/') + 1) || selectedNovel}`
                  }
                />

                              </TabPanel>

              {/* 通用配置 */}
              <Box sx={{ p: 3, pt: 0 }}>
                {/* 尺寸选择 */}
                <FormControl fullWidth sx={{ mb: 3 }}>
                  <InputLabel>封面尺寸</InputLabel>
                  <Select
                    value={coverSize}
                    label="封面尺寸"
                    onChange={(e) => setCoverSize(e.target.value)}
                  >
                    <MenuItem value="1024x1024">正方形 (1024x1024)</MenuItem>
                    <MenuItem value="1024x768">横向 (1024x768)</MenuItem>
                    <MenuItem value="768x1024">纵向 (768x1024)</MenuItem>
                    <MenuItem value="1280x720">高清横向 (1280x720)</MenuItem>
                    <MenuItem value="720x1280">高清纵向 (720x1280)</MenuItem>
                  </Select>
                </FormControl>

                {/* 参考图片上传 */}
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    参考图片（可选）
                  </Typography>

                  {/* 拖拽上传区域 */}
                  <Box
                    sx={{
                      position: 'relative',
                      border: '2px dashed',
                      borderColor: referenceImage ? 'success.main' : 'grey.300',
                      borderRadius: 2,
                      p: 3,
                      textAlign: 'center',
                      backgroundColor: referenceImage ? 'success.50' : 'grey.50',
                      cursor: imageLoading ? 'not-allowed' : 'pointer',
                      transition: 'all 0.2s ease',
                      '&:hover': {
                        backgroundColor: imageLoading ? 'inherit' : 'primary.50',
                        borderColor: imageLoading ? 'inherit' : 'primary.main'
                      }
                    }}
                    onDragOver={handleDragOver}
                    onDragEnter={handleDragEnter}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    onClick={handleFileSelectClick}
                  >
                    <UploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
                    <Typography variant="body1" gutterBottom>
                      {imageLoading ? '正在处理图片...' :
                       (referenceImage ? '重新选择图片' : '点击选择或拖拽图片到此处')}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      支持 JPG、PNG、GIF 等图片格式
                    </Typography>
                  </Box>

  
                  {referenceImage && (
                    <Box sx={{ mt: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Chip
                        label={referenceImage.name}
                        size="small"
                        color={imageError ? "error" : "success"}
                        variant="outlined"
                        onDelete={clearImageSelection}
                        deleteIcon={<DeleteIcon fontSize="small" />}
                      />
                      <Typography variant="caption" color="text.secondary">
                        ({(referenceImage.size / 1024).toFixed(1)} KB)
                      </Typography>
                      {imageLoading && (
                        <CircularProgress size={16} sx={{ ml: 1 }} />
                      )}
                    </Box>
                  )}
                </Box>

                {/* 参考图片预览 */}
                {(imagePreview || imageLoading) && (
                  <Box sx={{ mb: 3 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Typography variant="subtitle2">
                        参考图片预览
                      </Typography>
                      <IconButton
                        size="small"
                        onClick={clearImageSelection}
                        sx={{ color: 'text.secondary' }}
                        disabled={imageLoading}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Box>
                    <Box
                      sx={{
                        border: '2px solid',
                        borderColor: imageError ? 'error.main' : 'grey.300',
                        borderRadius: 2,
                        overflow: 'hidden',
                        height: 200,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        backgroundColor: 'grey.50',
                        position: 'relative',
                      }}
                    >
                      {imageLoading ? (
                        <Box sx={{ textAlign: 'center' }}>
                          <CircularProgress size={40} sx={{ mb: 1 }} />
                          <Typography variant="body2" color="text.secondary">
                            加载图片中...
                          </Typography>
                        </Box>
                      ) : imageError ? (
                        <Box sx={{ textAlign: 'center', p: 2 }}>
                          <Typography variant="body2" color="error" sx={{ mb: 1 }}>
                            图片加载失败
                          </Typography>
                          <Button
                            variant="outlined"
                            size="small"
                            onClick={() => {
                              setImageError(false);
                              if (imagePreview) {
                                setImagePreview(imagePreview); // 重新触发加载
                              }
                            }}
                          >
                            重试
                          </Button>
                        </Box>
                      ) : imagePreview ? (
                        <>
                          <img
                            src={imagePreview}
                            alt="参考图片"
                            style={{
                              maxWidth: '100%',
                              maxHeight: '100%',
                              objectFit: 'contain',
                            }}
                            onLoadStart={handleImageLoadStart}
                            onLoad={handleImageLoad}
                            onError={handleImageError}
                          />
                          {referenceImage && (
                            <Box
                              sx={{
                                position: 'absolute',
                                bottom: 0,
                                left: 0,
                                right: 0,
                                backgroundColor: 'rgba(0, 0, 0, 0.7)',
                                color: 'white',
                                p: 1,
                                textAlign: 'center',
                              }}
                            >
                              <Typography variant="caption">
                                {referenceImage.name} ({(referenceImage.size / 1024).toFixed(1)} KB)
                              </Typography>
                            </Box>
                          )}
                        </>
                      ) : (
                        <Box sx={{ textAlign: 'center' }}>
                          <Typography variant="body2" color="text.secondary">
                            无图片预览
                          </Typography>
                        </Box>
                      )}
                    </Box>
                  </Box>
                )}

                {/* 生成按钮 */}
                <Button
                  variant="contained"
                  fullWidth
                  startIcon={generateMutation.isPending ? <CircularProgress size={20} /> : <AutoFixHighIcon />}
                  onClick={handleGenerate}
                  disabled={
                    generateMutation.isPending ||
                    (coverType === 'chapter' && !selectedNovel) ||
                    !coverPrompt.trim() ||
                    imageLoading ||
                    imageError
                  }
                  sx={{ py: 1.5 }}
                >
                  {generateMutation.isPending ? '生成中...' :
                   imageLoading ? '图片加载中...' :
                   imageError ? '图片加载失败' :
                   '生成封面'}
                </Button>

                {/* 生成进度 */}
                {generateMutation.isPending && (
                  <Box sx={{ mt: 2 }}>
                    <LinearProgress />
                    <Typography variant="body2" sx={{ mt: 1, textAlign: 'center' }}>
                      正在生成封面，请稍候...
                    </Typography>
                  </Box>
                )}
              </Box>
            </Paper>
          </Grid>

          {/* 右侧：已有封面 */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                已生成的封面
              </Typography>

              {coversLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                  <CircularProgress />
                </Box>
              ) : coversData?.covers && coversData.covers.length > 0 ? (
                <Grid container spacing={2}>
                  {coversData.covers.map((cover: Cover) => (
                    <Grid item xs={12} sm={6} key={cover.cover_id}>
                      <Card>
                        <CardMedia
                          component="img"
                          height="200"
                          image={cover.image_url}
                          alt={cover.title}
                          sx={{ objectFit: 'cover' }}
                        />
                        <CardContent sx={{ pb: 1 }}>
                          <Typography variant="subtitle2" noWrap>
                            {cover.title}
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                            <Chip
                              label={cover.cover_type === 'project' ? '项目封面' : '章节封面'}
                              size="small"
                              color={cover.cover_type === 'project' ? 'primary' : 'secondary'}
                            />
                            <Chip
                              label={cover.status}
                              size="small"
                              variant="outlined"
                            />
                          </Box>
                        </CardContent>
                        <CardActions sx={{ pt: 0 }}>
                          <Tooltip title="查看大图">
                            <IconButton
                              size="small"
                              onClick={() => window.open(cover.image_url, '_blank')}
                            >
                              <VisibilityIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="下载">
                            <IconButton
                              size="small"
                              onClick={() => handleDownload(cover)}
                            >
                              <DownloadIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="删除">
                            <IconButton
                              size="small"
                              onClick={() => handleDelete(cover.cover_id)}
                              disabled={deleteMutation.isPending}
                              color="error"
                            >
                              <DeleteIcon />
                            </IconButton>
                          </Tooltip>
                        </CardActions>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              ) : (
                <Box
                  sx={{
                    textAlign: 'center',
                    py: 4,
                    border: '2px dashed',
                    borderColor: 'grey.300',
                    borderRadius: 1,
                    backgroundColor: 'grey.50',
                  }}
                >
                  <ImageIcon sx={{ fontSize: 64, color: 'grey.400', mb: 2 }} />
                  <Typography variant="h6" color="text.secondary" gutterBottom>
                    尚未生成封面
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    使用左侧配置生成您的第一个封面
                  </Typography>
                </Box>
              )}
            </Paper>
          </Grid>
        </Grid>

        {/* 通知提示 */}
        <Snackbar
          open={notification.open}
          autoHideDuration={6000}
          onClose={closeNotification}
        >
          <Alert
            onClose={closeNotification}
            severity={notification.severity}
            sx={{ width: '100%' }}
          >
            {notification.message}
          </Alert>
        </Snackbar>
      </Box>
    </Container>
  );
};

export default CoverGenerationPage;
