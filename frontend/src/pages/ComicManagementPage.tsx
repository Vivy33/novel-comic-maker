import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardMedia,
  Button,
  Grid,
  Chip,
  TextField,
  InputAdornment,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Checkbox,
  Alert,
  Snackbar,
  AlertTitle,
  IconButton,
  Menu,
  MenuList,
  ListItemIcon,
  ListItemText,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  Download as DownloadIcon,
  CameraAlt as CameraIcon,
  Add as AddIcon,
  MoreVert as MoreVertIcon,
  Delete as DeleteIcon,
  Image as ImageIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { comicService } from '../services/comicService';
import { ChapterInfo, CoverInfo } from '../models/comic';
import LoadingState from '../components/LoadingState';
import CoverManager from '../components/CoverManager';
import {
  Tabs,
  Tab,
} from '@mui/material';

interface ComicManagementPageProps {
  projectId: string;
}

const ComicManagementPage: React.FC<ComicManagementPageProps> = ({ projectId }) => {
  const navigate = useNavigate();

  console.log('🎯 ComicManagementPage 组件已加载，projectId:', projectId);

  // 状态管理
  const [currentTab, setCurrentTab] = useState(0);
  const [chapters, setChapters] = useState<ChapterInfo[]>([]);
  const [covers, setCovers] = useState<{
    primary_cover: CoverInfo | null;
    chapter_covers: CoverInfo[];
  }>({ primary_cover: null, chapter_covers: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 搜索和筛选状态
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('全部');
  const [sortBy, setSortBy] = useState('创建时间');
  const [sortOrder, setSortOrder] = useState('降序');
  const [selectedChapters, setSelectedChapters] = useState<Set<string>>(new Set());

  // 菜单和对话框状态
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedChapter, setSelectedChapter] = useState<ChapterInfo | null>(null);
  const [chapterImages, setChapterImages] = useState<any[]>([]);
  const [loadingImages, setLoadingImages] = useState(false);

  // 消息提示
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info' | 'warning';
  }>({
    open: false,
    message: '',
    severity: 'info',
  });

  // 加载章节数据
  const loadChapters = useCallback(async () => {
    console.log('🔄 loadChapters 被调用，projectId:', projectId);
    if (!projectId) {
      console.log('❌ projectId 为空，返回');
      return;
    }
    try {
      console.log('⏳ 开始加载章节数据...');
      setLoading(true);
      setError(null);
      const chaptersData = await comicService.getChapters(projectId);
      console.log('✅ 章节数据加载成功:', chaptersData);

      // 数据格式化处理 - 添加安全检查
      let formattedChapters: ChapterInfo[] = [];
      if (Array.isArray(chaptersData)) {
        formattedChapters = chaptersData.map(chapter => ({
          ...chapter,
          completion_percentage: chapter.total_panels > 0
            ? (chapter.confirmed_panels / chapter.total_panels) * 100
            : 0,
          has_unconfirmed_panels: (chapter.unconfirmed_panels || 0) > 0,
        }));
      } else {
        console.warn('⚠️ 章节数据格式异常:', chaptersData);
        formattedChapters = [];
      }

      console.log('🔧 格式化后的章节数据:', formattedChapters);
      setChapters(formattedChapters);
    } catch (err) {
      console.error('❌ 加载章节数据失败:', err);
      setError(`加载章节数据失败: ${err instanceof Error ? err.message : '未知错误'}`);
    } finally {
      console.log('🏁 loadChapters 完成，设置 loading 为 false');
      setLoading(false);
    }
  }, [projectId]);

  // 加载封面数据
  const loadCovers = useCallback(async () => {
    console.log('🎨 loadCovers 被调用，projectId:', projectId);
    if (!projectId) {
      console.log('❌ loadCovers: projectId 为空，跳过');
      return;
    }
    try {
      console.log('⏳ 开始加载封面数据...');
      const coversData = await comicService.getProjectCovers(projectId);
      console.log('✅ 封面数据加载成功:', coversData);
      setCovers(coversData);
    } catch (err) {
      console.error('❌ 加载封面数据失败:', err);
      // 封面加载失败不影响主要功能，但记录错误
      console.warn('⚠️ 封面数据加载失败，但不影响章节功能');
    }
  }, [projectId]);

  // 加载章节详情和图片
  const loadChapterDetail = async (chapter: ChapterInfo) => {
    if (!projectId) return;
    try {
      setLoadingImages(true);
      const detail = await comicService.getChapterDetail(projectId, chapter.chapter_id);
      setChapterImages(detail.panels || []);
      setSelectedChapter(chapter);
    } catch (err) {
      console.error('加载章节详情失败:', err);
      showSnackbar('加载章节详情失败', 'error');
    } finally {
      setLoadingImages(false);
    }
  };

  // 生成项目封面
  const generateProjectCover = async () => {
    if (!projectId) return;
    try {
      // 调用封面生成API
      showSnackbar('项目封面生成功能开发中...', 'info');
    } catch (err) {
      console.error('生成项目封面失败:', err);
      showSnackbar('生成项目封面失败', 'error');
    }
  };

  // 生成章节封面
  const generateChapterCover = async (chapter: ChapterInfo) => {
    if (!projectId) return;
    try {
      // 调用章节封面生成API
      showSnackbar('章节封面生成功能开发中...', 'info');
    } catch (err) {
      console.error('生成章节封面失败:', err);
      showSnackbar('生成章节封面失败', 'error');
    }
  };

  // 删除章节
  const deleteChapter = async (chapterId: string) => {
    if (!projectId) return;
    try {
      // 调用删除章节API
      showSnackbar('删除章节功能开发中...', 'info');
    } catch (err) {
      console.error('删除章节失败:', err);
      showSnackbar('删除章节失败', 'error');
    }
  };

  // 导出章节
  const exportChapter = async (chapterId: string) => {
    if (!projectId) return;
    try {
      const result = await comicService.exportChapter(projectId, chapterId);
      if (result.success) {
        showSnackbar('章节导出成功', 'success');
      }
    } catch (err) {
      console.error('导出失败:', err);
      showSnackbar('导出失败，请稍后重试', 'error');
    }
  };

  // 全选/取消全选
  const handleSelectAll = () => {
    if (selectedChapters.size === chapters.length) {
      setSelectedChapters(new Set());
    } else {
      setSelectedChapters(new Set(chapters.map(chapter => chapter.chapter_id)));
    }
  };

  // 批量导出
  const handleBatchExport = () => {
    if (selectedChapters.size === 0) {
      showSnackbar('请先选择要导出的章节', 'warning');
      return;
    }
    showSnackbar(`批量导出 ${selectedChapters.size} 个章节功能开发中...`, 'info');
  };

  // 刷新数据
  const handleRefresh = () => {
    loadChapters();
    loadCovers();
  };

  // 显示消息
  const showSnackbar = (message: string, severity: 'success' | 'error' | 'info' | 'warning') => {
    setSnackbar({ open: true, message, severity });
  };

  // 关闭消息提示
  const closeSnackbar = () => {
    setSnackbar(prev => ({ ...prev, open: false }));
  };

  // 处理章节选择
  const handleChapterSelect = (chapterId: string) => {
    const newSelected = new Set(selectedChapters);
    if (newSelected.has(chapterId)) {
      newSelected.delete(chapterId);
    } else {
      newSelected.add(chapterId);
    }
    setSelectedChapters(newSelected);
  };

  // 打开章节菜单
  const handleChapterMenuOpen = (event: React.MouseEvent<HTMLElement>, chapter: ChapterInfo) => {
    setAnchorEl(event.currentTarget);
    setSelectedChapter(chapter);
  };

  // 关闭章节菜单
  const handleChapterMenuClose = () => {
    setAnchorEl(null);
    setSelectedChapter(null);
  };

  // 处理标签页切换
  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  // 计算统计数据
  const stats = {
    total: chapters.length,
    completed: chapters.filter(c => c.status === 'completed').length,
    generating: chapters.filter(c => c.status === 'generating').length,
    projectCover: covers && covers.primary_cover ? 1 : 0,
    chapterCover: covers && covers.chapter_covers ? covers.chapter_covers.length : 0,
  };

  // 筛选和排序章节数据
  const filteredAndSortedChapters = chapters
    .filter(chapter => {
      const title = chapter.title || `第${chapter.chapter_number}章`;
      const matchesSearch = title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                           `第${chapter.chapter_number}章`.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = statusFilter === '全部' || chapter.status === statusFilter;
      return matchesSearch && matchesStatus;
    })
    .sort((a, b) => {
      let aValue: any, bValue: any;

      switch (sortBy) {
        case '创建时间':
          aValue = new Date(a.created_at).getTime();
          bValue = new Date(b.created_at).getTime();
          break;
        case '更新时间':
          aValue = new Date(a.updated_at).getTime();
          bValue = new Date(b.updated_at).getTime();
          break;
        case '章节号':
          aValue = a.chapter_number;
          bValue = b.chapter_number;
          break;
        default:
          aValue = new Date(a.created_at).getTime();
          bValue = new Date(b.created_at).getTime();
      }

      return sortOrder === '升序' ? aValue - bValue : bValue - aValue;
    });

  // useEffect 必须在所有 hooks 之后
  useEffect(() => {
    console.log('🚀 useEffect 被触发，projectId:', projectId);
    if (projectId) {
      console.log('📋 准备调用 loadChapters 和 loadCovers');
      loadChapters();
      loadCovers();
    } else {
      console.log('❌ projectId 为空，跳过加载');
    }
  }, [projectId, loadChapters, loadCovers]);

  useEffect(() => {
    console.log('📦 State changed: chapters:', chapters);
    console.log('📦 State changed: covers:', covers);
  }, [chapters, covers]);

  // 验证projectId
  if (!projectId) {
    console.error('❌ ComicManagementPage: projectId 为空或未定义');
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          <AlertTitle>项目ID错误</AlertTitle>
          项目ID未提供，请从项目页面访问漫画管理功能。
        </Alert>
      </Box>
    );
  }

  if (loading) {
    console.log('⏳ 当前处于 loading 状态，显示加载页面');
    return <LoadingState message="加载漫画数据中..." />;
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          <AlertTitle>加载失败</AlertTitle>
          {error}
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, backgroundColor: '#f5f5f5', minHeight: '100vh' }}>
      {/* 页面标题 */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, backgroundColor: 'white', p: 2, borderRadius: 1 }}>
        <Typography variant="h5" sx={{ fontWeight: 'bold', color: '#333' }}>
          漫画管理
        </Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={handleRefresh}
        >
          刷新数据
        </Button>
      </Box>

      {/* 统计卡片 */}
      <Box sx={{ mb: 3 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={2.4}>
            <Card sx={{ textAlign: 'center', p: 2 }}>
              <Typography variant="h4" sx={{ color: '#1890FF', fontWeight: 'bold' }}>
                {stats.total}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                总章节数
              </Typography>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={2.4}>
            <Card sx={{ textAlign: 'center', p: 2 }}>
              <Typography variant="h4" sx={{ color: '#52C41A', fontWeight: 'bold' }}>
                {stats.completed}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                已完成
              </Typography>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={2.4}>
            <Card sx={{ textAlign: 'center', p: 2 }}>
              <Typography variant="h4" sx={{ color: '#FA8C16', fontWeight: 'bold' }}>
                {stats.generating}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                生成中
              </Typography>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={2.4}>
            <Card sx={{ textAlign: 'center', p: 2 }}>
              <Typography variant="h4" sx={{ color: '#1890FF', fontWeight: 'bold' }}>
                {stats.projectCover}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                项目封面
              </Typography>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={2.4}>
            <Card sx={{ textAlign: 'center', p: 2 }}>
              <Typography variant="h4" sx={{ color: '#F5222D', fontWeight: 'bold' }}>
                {stats.chapterCover}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                章节封面
              </Typography>
            </Card>
          </Grid>
        </Grid>
      </Box>

      {/* 标签页 */}
      <Card sx={{ backgroundColor: 'white' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={currentTab} onChange={handleTabChange}>
            <Tab label="章节管理" />
            <Tab label="封面管理" />
          </Tabs>
        </Box>

        <Box sx={{ p: 0 }}>
          {/* 章节管理标签页 */}
          {currentTab === 0 && (
            <Box>
              {/* 搜索和筛选栏 */}
              <Box sx={{ backgroundColor: '#f9f9f9', p: 2, borderRadius: 1 }}>
                <Grid container spacing={2} alignItems="center">
                  <Grid item xs={12} md={4}>
                    <TextField
                      fullWidth
                      size="small"
                      placeholder="搜索章节..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      InputProps={{
                        startAdornment: (
                          <InputAdornment position="start">
                            <SearchIcon />
                          </InputAdornment>
                        ),
                      }}
                    />
                  </Grid>
                  <Grid item xs={12} md={2}>
                    <FormControl fullWidth size="small">
                      <InputLabel>状态筛选</InputLabel>
                      <Select
                        value={statusFilter}
                        label="状态筛选"
                        onChange={(e) => setStatusFilter(e.target.value)}
                      >
                        <MenuItem value="全部">全部</MenuItem>
                        <MenuItem value="completed">已完成</MenuItem>
                        <MenuItem value="generating">生成中</MenuItem>
                        <MenuItem value="pending">待处理</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12} md={2}>
                    <FormControl fullWidth size="small">
                      <InputLabel>排序方式</InputLabel>
                      <Select
                        value={sortBy}
                        label="排序方式"
                        onChange={(e) => setSortBy(e.target.value)}
                      >
                        <MenuItem value="创建时间">创建时间</MenuItem>
                        <MenuItem value="更新时间">更新时间</MenuItem>
                        <MenuItem value="章节号">章节号</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12} md={2}>
                    <FormControl fullWidth size="small">
                      <InputLabel>排序顺序</InputLabel>
                      <Select
                        value={sortOrder}
                        label="排序顺序"
                        onChange={(e) => setSortOrder(e.target.value)}
                      >
                        <MenuItem value="降序">降序</MenuItem>
                        <MenuItem value="升序">升序</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12} md={2}>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Button
                        variant="outlined"
                        startIcon={<CheckCircleIcon />}
                        onClick={handleSelectAll}
                        fullWidth
                      >
                        全选
                      </Button>
                      <Button
                        variant="contained"
                        sx={{ backgroundColor: '#666', '&:hover': { backgroundColor: '#555' } }}
                        startIcon={<DownloadIcon />}
                        onClick={handleBatchExport}
                        fullWidth
                      >
                        批量导出
                      </Button>
                    </Box>
                  </Grid>
                </Grid>
              </Box>

              {/* 章节列表 */}
              {filteredAndSortedChapters.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <ImageIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                  <Typography variant="h6" color="text.secondary">
                    暂无章节数据
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    请先使用"漫画生成"功能创建章节
                  </Typography>
                  <Button
                    variant="contained"
                    sx={{ mt: 2 }}
                    onClick={() => navigate(`/project/${projectId}/generate-segmented`)}
                  >
                    开始生成漫画
                  </Button>
                </Box>
              ) : (
                <Box>
                  {filteredAndSortedChapters.map((chapter, index) => (
                    <Box key={chapter.chapter_id}>
                      <Box sx={{ p: 2, display: 'flex', alignItems: 'center' }}>
                        <Checkbox
                          checked={selectedChapters.has(chapter.chapter_id)}
                          onChange={() => handleChapterSelect(chapter.chapter_id)}
                        />
                        <Box sx={{ flexGrow: 1, ml: 2 }}>
                          <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                            {chapter.title || `第${chapter.chapter_number}章`}
                          </Typography>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 0.5 }}>
                            <Chip
                              label={chapter.status === 'completed' ? '已完成' :
                                     chapter.status === 'generating' ? '生成中' : '待处理'}
                              color={chapter.status === 'completed' ? 'success' :
                                     chapter.status === 'generating' ? 'warning' : 'default'}
                              size="small"
                            />
                            <Typography variant="body2" color="text.secondary">
                              创建时间: {new Date(chapter.created_at).toLocaleString('zh-CN')}
                            </Typography>
                          </Box>
                        </Box>
                        <IconButton onClick={(e) => handleChapterMenuOpen(e, chapter)}>
                          <MoreVertIcon />
                        </IconButton>
                      </Box>
                      {index < filteredAndSortedChapters.length - 1 && <Divider />}
                    </Box>
                  ))}
                </Box>
              )}
            </Box>
          )}

          {/* 封面管理标签页 */}
          {currentTab === 1 && (
            <Box sx={{ p: 2 }}>
              <CoverManager
                projectId={projectId}
                coversData={covers}
                onRefresh={loadCovers}
              />
            </Box>
          )}
        </Box>
      </Card>

      {/* 章节操作菜单 */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleChapterMenuClose}
      >
        <MenuList>
          <MenuItem onClick={() => {
            if (selectedChapter) {
              loadChapterDetail(selectedChapter);
            }
            handleChapterMenuClose();
          }}>
            <ListItemIcon>
              <ImageIcon />
            </ListItemIcon>
            <ListItemText>查看图片</ListItemText>
          </MenuItem>
          <MenuItem onClick={() => {
            if (selectedChapter) {
              generateChapterCover(selectedChapter);
            }
            handleChapterMenuClose();
          }}>
            <ListItemIcon>
              <CameraIcon />
            </ListItemIcon>
            <ListItemText>生成封面</ListItemText>
          </MenuItem>
          <MenuItem onClick={() => {
            if (selectedChapter) {
              exportChapter(selectedChapter.chapter_id);
            }
            handleChapterMenuClose();
          }}>
            <ListItemIcon>
              <DownloadIcon />
            </ListItemIcon>
            <ListItemText>导出章节</ListItemText>
          </MenuItem>
          <Divider />
          <MenuItem onClick={() => {
            if (selectedChapter) {
              deleteChapter(selectedChapter.chapter_id);
            }
            handleChapterMenuClose();
          }} sx={{ color: 'error.main' }}>
            <ListItemIcon>
              <DeleteIcon sx={{ color: 'error.main' }} />
            </ListItemIcon>
            <ListItemText>删除章节</ListItemText>
          </MenuItem>
        </MenuList>
      </Menu>

      {/* 章节图片详情对话框 */}
      <Dialog
        open={!!selectedChapter}
        onClose={() => setSelectedChapter(null)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          {selectedChapter?.title || `第${selectedChapter?.chapter_number || 1}章`} - 图片详情
        </DialogTitle>
        <DialogContent dividers>
          {loadingImages ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <Typography>加载图片中...</Typography>
            </Box>
          ) : (
            <Grid container spacing={2}>
              {chapterImages.map((image: any) => (
                <Grid item xs={12} sm={6} md={4} key={image.panel_id}>
                  <Card>
                    <CardMedia
                      component="img"
                      image={image.image_path}
                      alt={`图片 ${image.panel_id}`}
                      sx={{ height: 150, objectFit: 'cover' }}
                    />
                    <CardContent sx={{ p: 1, textAlign: 'center' }}>
                      <Typography variant="caption">
                        图片 {image.panel_id}
                        {image.confirmed && <CheckCircleIcon sx={{ fontSize: 16, color: 'success.main', ml: 1 }} />}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedChapter(null)}>
            关闭
          </Button>
        </DialogActions>
      </Dialog>

      {/* 消息提示 */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={closeSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={closeSnackbar}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default ComicManagementPage;