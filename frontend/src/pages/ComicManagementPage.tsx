import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box,
  Typography,
  Card,
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
  MoreVert as MoreVertIcon,
  Delete as DeleteIcon,
  Image as ImageIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { comicService } from '../services/comicService';
import * as ComicModels from '../models/comic';
import LoadingState from '../components/LoadingState';
import CoverManager from '../components/CoverManager';
import PanelGridDisplay from '../components/PanelGridDisplay';
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
  const [chapters, setChapters] = useState<ComicModels.ChapterInfo[]>([]);
  const [covers, setCovers] = useState<{
    primary_cover: ComicModels.CoverInfo | null;
    chapter_covers: ComicModels.CoverInfo[];
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
  const [selectedChapter, setSelectedChapter] = useState<ComicModels.ChapterInfo | null>(null);
  const [chapterDetail, setChapterDetail] = useState<ComicModels.ChapterDetail | null>(null);
  const [loadingChapterDetail, setLoadingChapterDetail] = useState(false);

  // 使用ref存储最近点击的章节，避免React状态更新的时序问题
  const lastClickedChapterRef = useRef<ComicModels.ChapterInfo | null>(null);

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
      let formattedChapters: ComicModels.ChapterInfo[] = [];
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
  const loadChapterDetail = async (chapter: ComicModels.ChapterInfo) => {
    console.log('🔄 loadChapterDetail 开始:', {
      projectId: projectId,
      chapterId: chapter.chapter_id,
      chapterTitle: chapter.title
    });

    if (!projectId) {
      console.error('❌ projectId 为空，无法加载章节详情');
      return;
    }

    try {
      setLoadingChapterDetail(true);
      console.log('⏳ 开始调用 comicService.getChapterDetail...');
      const detail = await comicService.getChapterDetail(projectId, chapter.chapter_id);
      console.log('✅ 章节详情加载成功:', {
        panelsCount: detail?.panels?.length,
        paragraphsCount: detail?.paragraphs?.length,
        chapterTitle: detail?.title
      });
      setChapterDetail(detail);
      setSelectedChapter(chapter);
    } catch (err) {
      console.error('❌ 加载章节详情失败:', err);
      showSnackbar('加载章节详情失败', 'error');
    } finally {
      setLoadingChapterDetail(false);
      console.log('🏁 loadChapterDetail 完成');
    }
  };

  // 分镜图操作处理函数
  const handlePanelUpdateNotes = async (panelId: number, notes: string) => {
    // TODO: 实现更新分镜图备注的API调用
    console.log('更新分镜图备注:', panelId, notes);
    showSnackbar('分镜图备注更新功能开发中...', 'info');
  };

  const handlePanelDelete = async (panelIds: number[]) => {
    console.log('🗑️ handlePanelDelete 被调用:', {
      panelIds,
      projectId,
      selectedChapter,
      selectedChapterId: selectedChapter?.chapter_id
    });

    if (!projectId || !selectedChapter) {
      console.error('❌ 缺少必要参数:', { projectId, selectedChapter });
      showSnackbar('缺少项目或章节信息', 'error');
      return;
    }

    console.log('🔄 开始删除分镜图:', panelIds);

    try {
      // 逐个删除分镜图
      for (const panelId of panelIds) {
        console.log('🗑️ 正在删除分镜图:', {
          projectId,
          chapterId: selectedChapter.chapter_id,
          panelId
        });
        await comicService.deletePanel(projectId, selectedChapter.chapter_id, panelId);
        console.log('✅ 分镜图删除成功:', panelId);
      }

      showSnackbar(`成功删除 ${panelIds.length} 张分镜图`, 'success');

      // 重新加载章节详情以更新显示
      await loadChapterDetail(selectedChapter);

    } catch (error) {
      console.error('❌ 删除分镜图失败:', error);
      showSnackbar(`删除分镜图失败: ${error instanceof Error ? error.message : '未知错误'}`, 'error');
    }
  };

  const handlePanelReorder = async (panelIds: number[], newOrder: number[]) => {
    // TODO: 实现重新排序分镜图的API调用
    console.log('重新排序分镜图:', panelIds, newOrder);
    showSnackbar('分镜图排序功能开发中...', 'info');
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
  const generateChapterCover = async (chapter: ComicModels.ChapterInfo) => {
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
  const handleChapterMenuOpen = (event: React.MouseEvent<HTMLElement>, chapter: ComicModels.ChapterInfo) => {
    console.log('📂 打开章节菜单:', {
      chapterId: chapter.chapter_id,
      chapterTitle: chapter.title,
      chapter: chapter
    });
    setAnchorEl(event.currentTarget);
    setSelectedChapter(chapter);
    // 同时存储到ref中，确保菜单项点击时能获取到正确的章节
    lastClickedChapterRef.current = chapter;
  };

  // 关闭章节菜单
  const handleChapterMenuClose = () => {
    console.log('🔚 关闭章节菜单，当前selectedChapter:', selectedChapter);
    setAnchorEl(null);
    // 不要立即清空selectedChapter，让菜单项有机会使用它
    // setSelectedChapter(null);
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
                        <IconButton
                          onClick={(e) => {
                            e.stopPropagation();
                            e.preventDefault();
                            console.log('🔘 点击了三个点按钮:', {
                              chapterId: chapter.chapter_id,
                              chapterTitle: chapter.title,
                              chapter: chapter
                            });
                            handleChapterMenuOpen(e, chapter);
                          }}
                        >
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
            console.log('🔘 点击了"查看图片"菜单项:', {
              selectedChapter: selectedChapter,
              hasSelectedChapter: !!selectedChapter,
              lastClickedChapter: lastClickedChapterRef.current
            });

            handleChapterMenuClose();

            // 优先使用ref中的章节，避免React状态更新的时序问题
            const chapterToLoad = lastClickedChapterRef.current || selectedChapter;

            if (chapterToLoad) {
              console.log('✅ 使用章节加载详情:', chapterToLoad.title);
              loadChapterDetail(chapterToLoad);
            } else {
              console.error('❌ 没有可用的章节数据');
              // 备用方法：直接从章节数组中获取第一个章节
              const firstChapter = filteredAndSortedChapters[0];
              if (firstChapter) {
                console.log('🔄 使用备用方法加载第一个章节:', firstChapter);
                loadChapterDetail(firstChapter);
              }
            }
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

      {/* 章节分镜图详情对话框 */}
      <Dialog
        open={!!selectedChapter}
        onClose={() => setSelectedChapter(null)}
        maxWidth="xl"
        fullWidth
        PaperProps={{
          sx: {
            height: '90vh',
            maxHeight: '90vh',
          }
        }}
      >
        <DialogTitle>
          {selectedChapter?.title || `第${selectedChapter?.chapter_number || 1}章`} - 分镜图详情
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
            {selectedChapter && (
              <>
                <Chip
                  label={`${selectedChapter.total_panels} 张分镜图`}
                  size="small"
                  color="primary"
                  variant="outlined"
                />
                <Chip
                  label={`${selectedChapter.confirmed_panels} 已确认`}
                  size="small"
                  color="success"
                  variant="outlined"
                />
                {selectedChapter.has_unconfirmed_panels && (
                  <Chip
                    label={`${selectedChapter.unconfirmed_panels} 待确认`}
                    size="small"
                    color="warning"
                    variant="outlined"
                  />
                )}
              </>
            )}
          </Box>
        </DialogTitle>
        <DialogContent dividers sx={{ p: 2 }}>
          {loadingChapterDetail ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <LoadingState message="正在加载章节详情..." />
            </Box>
          ) : chapterDetail ? (
            <PanelGridDisplay
              panels={chapterDetail.panels}
              paragraphs={chapterDetail.paragraphs}
              onPanelUpdateNotes={handlePanelUpdateNotes}
              onPanelDelete={handlePanelDelete}
              onPanelReorder={handlePanelReorder}
              editable={true}
              title="章节分镜图"
              projectId={projectId}
            />
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography color="text.secondary">
                暂无分镜图数据
              </Typography>
            </Box>
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