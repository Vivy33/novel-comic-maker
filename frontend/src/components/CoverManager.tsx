import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  CardMedia,
  CardContent,
  Typography,
  Button,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
  IconButton,
  Alert,
  CircularProgress,
  TextField,
  InputAdornment,
  Menu,
  MenuItem,
} from '@mui/material';
import {
  Search as SearchIcon,
  MoreVert as MoreVertIcon,
  Download as DownloadIcon,
  Delete as DeleteIcon,
  Star as StarIcon,
  Visibility as VisibilityIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { comicService, handleApiError } from '../services/index';
import { CoverInfo } from '../models/comic';

interface Cover extends CoverInfo {}

interface CoverManagerProps {
  projectId: string;
  coversData?: {
    primary_cover: CoverInfo | null;
    chapter_covers: CoverInfo[];
  };
  onRefresh?: () => void;
}

const CoverManager: React.FC<CoverManagerProps> = ({ projectId, coversData, onRefresh }) => {
  const [covers, setCovers] = useState<Cover[]>([]);
  const [filteredCovers, setFilteredCovers] = useState<Cover[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<'all' | 'project' | 'chapter'>('all');
  const [selectedCover, setSelectedCover] = useState<Cover | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [menuAnchorEl, setMenuAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedCoverForMenu, setSelectedCoverForMenu] = useState<Cover | null>(null);
  const [notification, setNotification] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // 加载封面数据
  const loadCovers = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      console.log('🎯 开始加载封面数据...');

      const response = await comicService.getProjectCovers(projectId);
      console.log('📊 封面数据:', response);

      if (response && response.primary_cover) {
        const allCovers = [response.primary_cover, ...(response.chapter_covers || [])];
        setCovers(allCovers);
        setFilteredCovers(allCovers);
      } else {
        setCovers([]);
        setFilteredCovers([]);
      }

      console.log('✅ 封面数据加载成功');
    } catch (err) {
      console.error('❌ 加载封面数据失败:', err);
      const apiError = handleApiError(err);
      setError(apiError.message);
      showNotification(apiError.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  // 显示通知
  const showNotification = (message: string, severity: 'success' | 'error') => {
    setNotification({ open: true, message, severity });
  };

  // 搜索和过滤封面
  useEffect(() => {
    let filtered = covers;

    // 按类型过滤
    if (filterType !== 'all') {
      filtered = filtered.filter(cover => cover.cover_type === filterType);
    }

    // 按搜索词过滤
    if (searchTerm) {
      const lowerSearchTerm = searchTerm.toLowerCase();
      filtered = filtered.filter(cover =>
        (cover.title && cover.title.toLowerCase().includes(lowerSearchTerm)) ||
        (cover.description && cover.description.toLowerCase().includes(lowerSearchTerm)) ||
        cover.cover_id.toLowerCase().includes(lowerSearchTerm)
      );
    }

    setFilteredCovers(filtered);
  }, [covers, searchTerm, filterType]);

  // 格式化文件大小
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // 格式化时间
  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // 打开预览
  const handlePreview = (cover: Cover) => {
    setSelectedCover(cover);
    setPreviewOpen(true);
  };

  // 关闭预览
  const handleClosePreview = () => {
    setPreviewOpen(false);
    setSelectedCover(null);
  };

  // 打开菜单
  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, cover: Cover) => {
    event.stopPropagation();
    setMenuAnchorEl(event.currentTarget);
    setSelectedCoverForMenu(cover);
  };

  // 关闭菜单
  const handleMenuClose = () => {
    setMenuAnchorEl(null);
    setSelectedCoverForMenu(null);
  };

  // 设置主封面
  const handleSetPrimary = async () => {
    if (!selectedCoverForMenu) return;

    try {
      console.log('🎯 设置主封面:', selectedCoverForMenu.cover_id);
      await comicService.setPrimaryCover(projectId, selectedCoverForMenu.cover_id);
      showNotification('主封面设置成功', 'success');
      loadCovers(); // 重新加载数据
    } catch (err) {
      console.error('❌ 设置主封面失败:', err);
      const apiError = handleApiError(err);
      showNotification(apiError.message, 'error');
    } finally {
      handleMenuClose();
    }
  };

  // 删除封面 - 显示确认对话框
  const handleDelete = () => {
    if (!selectedCoverForMenu) return;
    setDeleteConfirmOpen(true);
  };

  // 确认删除封面
  const confirmDelete = async () => {
    if (!selectedCoverForMenu) return;

    try {
      setIsDeleting(true);
      console.log('🗑️ 删除封面:', selectedCoverForMenu.cover_id);
      await comicService.deleteCover(projectId, selectedCoverForMenu.cover_id);
      showNotification('封面删除成功', 'success');

      // 关闭确认对话框和菜单
      setDeleteConfirmOpen(false);
      handleMenuClose();

      // 重新加载数据
      await loadCovers();

      // 如果有回调函数，调用它
      if (onRefresh) {
        onRefresh();
      }
    } catch (err) {
      console.error('❌ 删除封面失败:', err);
      const apiError = handleApiError(err);
      showNotification(apiError.message, 'error');
    } finally {
      setIsDeleting(false);
    }
  };

  // 取消删除
  const cancelDelete = () => {
    setDeleteConfirmOpen(false);
    handleMenuClose();
  };

  // 下载封面
  const handleDownload = (cover: Cover) => {
    const link = document.createElement('a');
    link.href = cover.thumbnail_url;
    link.download = `${cover.cover_id}.jpg`;
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // 关闭通知
  const handleCloseNotification = () => {
    setNotification({ ...notification, open: false });
  };

  // 使用外部传入的封面数据
  useEffect(() => {
    console.log('🎯 CoverManager: 收到封面数据更新:', coversData);
    if (coversData) {
      const allCovers = coversData.primary_cover
        ? [coversData.primary_cover, ...(coversData.chapter_covers || [])]
        : [...(coversData.chapter_covers || [])];

      console.log('🔧 CoverManager: 处理后的封面数据:', allCovers);
      setCovers(allCovers);
      setFilteredCovers(allCovers);
      setLoading(false);
      setError(null);
    } else {
      console.log('📭 CoverManager: 无封面数据，显示空状态');
      setCovers([]);
      setFilteredCovers([]);
      setLoading(false);
      setError(null);
    }
  }, [coversData]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <CircularProgress size={60} />
        <Typography variant="h6" sx={{ ml: 2 }}>
          加载封面数据中...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 3 }}>
        {error}
      </Alert>
    );
  }

  return (
    <Box>
      {/* 搜索和过滤控件 */}
      <Box sx={{ mb: 3, display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
        <TextField
          placeholder="搜索封面..."
          variant="outlined"
          size="small"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
          sx={{ minWidth: 250, flexGrow: 1 }}
        />

        <Button
          variant={filterType === 'all' ? 'contained' : 'outlined'}
          onClick={() => setFilterType('all')}
          size="small"
        >
          全部 ({covers.length})
        </Button>

        <Button
          variant={filterType === 'project' ? 'contained' : 'outlined'}
          onClick={() => setFilterType('project')}
          size="small"
        >
          项目封面 ({covers.filter(c => c.cover_type === 'project').length})
        </Button>

        <Button
          variant={filterType === 'chapter' ? 'contained' : 'outlined'}
          onClick={() => setFilterType('chapter')}
          size="small"
        >
          章节封面 ({covers.filter(c => c.cover_type === 'chapter').length})
        </Button>
      </Box>

      {/* 封面网格 */}
      {filteredCovers.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 8 }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            {searchTerm || filterType !== 'all' ? '没有找到匹配的封面' : '暂无封面'}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {searchTerm || filterType !== 'all'
              ? '尝试调整搜索条件或过滤器'
              : '请先在漫画生成页面创建封面'}
          </Typography>
        </Box>
      ) : (
        <Grid container spacing={3}>
          {filteredCovers.map((cover) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={cover.cover_id}>
              <Card
                sx={{
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: 4,
                  },
                  position: 'relative',
                }}
                onClick={() => handlePreview(cover)}
              >
                {/* 主封面标识 */}
                {cover.is_primary && (
                  <Chip
                    label="主封面"
                    size="small"
                    icon={<StarIcon />}
                    color="primary"
                    sx={{
                      position: 'absolute',
                      top: 8,
                      left: 8,
                      zIndex: 1,
                      fontSize: '0.7rem',
                      height: 24,
                    }}
                  />
                )}

                {/* 封面类型标识 */}
                <Chip
                  label={cover.cover_type === 'project' ? '项目' : '章节'}
                  size="small"
                  color={cover.cover_type === 'project' ? 'secondary' : 'default'}
                  sx={{
                    position: 'absolute',
                    top: 8,
                    right: 8,
                    zIndex: 1,
                    fontSize: '0.7rem',
                    height: 24,
                  }}
                />

                {/* 操作菜单按钮 */}
                <IconButton
                  size="small"
                  sx={{
                    position: 'absolute',
                    bottom: 8,
                    right: 8,
                    zIndex: 1,
                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                    '&:hover': {
                      backgroundColor: 'rgba(255, 255, 255, 1)',
                    },
                  }}
                  onClick={(e) => handleMenuOpen(e, cover)}
                >
                  <MoreVertIcon fontSize="small" />
                </IconButton>

                {/* 封面图片 */}
                <CardMedia
                  component="img"
                  height="200"
                  image={cover.thumbnail_url}
                  alt={cover.title || cover.cover_id}
                  sx={{
                    objectFit: 'cover',
                    backgroundColor: '#f5f5f5',
                  }}
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = '/placeholder-image.svg';
                  }}
                />

                <CardContent sx={{ pb: 1 }}>
                  <Typography variant="subtitle2" noWrap gutterBottom>
                    {cover.title || `封面 ${cover.cover_id.slice(-8)}`}
                  </Typography>

                  {cover.description && (
                    <Typography variant="body2" color="text.secondary" sx={{
                      fontSize: '0.75rem',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}>
                      {cover.description}
                    </Typography>
                  )}

                  <Box sx={{ mt: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="caption" color="text.secondary">
                      {formatFileSize(cover.file_size)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {formatDate(cover.created_at)}
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* 右键菜单 */}
      <Menu
        anchorEl={menuAnchorEl}
        open={Boolean(menuAnchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => {
          if (selectedCoverForMenu) {
            handlePreview(selectedCoverForMenu);
          }
          handleMenuClose();
        }}>
          <VisibilityIcon sx={{ mr: 1, fontSize: 'small' }} />
          查看大图
        </MenuItem>

        <MenuItem onClick={() => {
          if (selectedCoverForMenu) {
            handleDownload(selectedCoverForMenu);
          }
          handleMenuClose();
        }}>
          <DownloadIcon sx={{ mr: 1, fontSize: 'small' }} />
          下载封面
        </MenuItem>

        {!selectedCoverForMenu?.is_primary && (
          <MenuItem onClick={handleSetPrimary}>
            <StarIcon sx={{ mr: 1, fontSize: 'small' }} />
            设为主封面
          </MenuItem>
        )}

        <MenuItem onClick={handleDelete} sx={{ color: 'error.main' }}>
          <DeleteIcon sx={{ mr: 1, fontSize: 'small' }} />
          删除封面
        </MenuItem>
      </Menu>

      {/* 图片预览对话框 */}
      <Dialog
        open={previewOpen}
        onClose={handleClosePreview}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">
            {selectedCover?.title || `封面 ${selectedCover?.cover_id?.slice(-8)}`}
          </Typography>
          <IconButton onClick={handleClosePreview}>
            <CloseIcon />
          </IconButton>
        </DialogTitle>

        <DialogContent>
          {selectedCover && (
            <Box>
              <Box sx={{ textAlign: 'center', mb: 2 }}>
                <img
                  src={selectedCover.thumbnail_url}
                  alt={selectedCover.title || selectedCover.cover_id}
                  style={{
                    maxWidth: '100%',
                    maxHeight: '500px',
                    objectFit: 'contain',
                    borderRadius: '8px',
                  }}
                />
              </Box>

              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    <strong>封面ID:</strong> {selectedCover.cover_id}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    <strong>类型:</strong> {selectedCover.cover_type === 'project' ? '项目封面' : '章节封面'}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    <strong>文件大小:</strong> {formatFileSize(selectedCover.file_size)}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    <strong>创建时间:</strong> {formatDate(selectedCover.created_at)}
                  </Typography>
                </Grid>
                {selectedCover.description && (
                  <Grid item xs={12}>
                    <Typography variant="body2" color="text.secondary">
                      <strong>描述:</strong> {selectedCover.description}
                    </Typography>
                  </Grid>
                )}
              </Grid>
            </Box>
          )}
        </DialogContent>

        <DialogActions>
          <Button onClick={handleClosePreview}>
            关闭
          </Button>
          <Button
            variant="contained"
            onClick={() => {
              if (selectedCover) {
                handleDownload(selectedCover);
              }
            }}
            startIcon={<DownloadIcon />}
          >
            下载封面
          </Button>
        </DialogActions>
      </Dialog>

      {/* 删除确认对话框 */}
      <Dialog
        open={deleteConfirmOpen}
        onClose={cancelDelete}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>确认删除封面</DialogTitle>
        <DialogContent>
          <Typography>
            确定要删除这个封面吗？
          </Typography>
          {selectedCoverForMenu && (
            <Box sx={{ mt: 2, p: 2, border: '1px solid #e0e0e0', borderRadius: 1 }}>
              <Typography variant="body2" color="text.secondary">
                <strong>封面ID:</strong> {selectedCoverForMenu.cover_id.slice(-8)}
              </Typography>
              {selectedCoverForMenu.title && (
                <Typography variant="body2" color="text.secondary">
                  <strong>标题:</strong> {selectedCoverForMenu.title}
                </Typography>
              )}
              <Typography variant="body2" color="text.secondary">
                <strong>类型:</strong> {selectedCoverForMenu.cover_type === 'project' ? '项目封面' : '章节封面'}
              </Typography>
              {selectedCoverForMenu.is_primary && (
                <Typography variant="body2" color="warning.main" sx={{ mt: 1 }}>
                  <strong>⚠️ 这是主封面，删除后需要重新设置主封面</strong>
                </Typography>
              )}
            </Box>
          )}
          <Typography variant="body2" color="error" sx={{ mt: 2 }}>
            此操作无法撤销。
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={cancelDelete} disabled={isDeleting}>
            取消
          </Button>
          <Button
            onClick={confirmDelete}
            color="error"
            variant="contained"
            disabled={isDeleting}
            startIcon={isDeleting ? <CircularProgress size={16} /> : <DeleteIcon />}
          >
            {isDeleting ? '删除中...' : '确认删除'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 通知提示 */}
      {notification.open && (
        <Alert
          severity={notification.severity}
          onClose={handleCloseNotification}
          sx={{
            position: 'fixed',
            bottom: 20,
            right: 20,
            zIndex: 9999,
            minWidth: 300,
          }}
        >
          {notification.message}
        </Alert>
      )}
    </Box>
  );
};

export default CoverManager;