import React, { useState, useRef } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Chip,
  Alert,
  LinearProgress,
  Tooltip,
  Menu,
  MenuItem,
  Snackbar,
  Divider,
} from '@mui/material';
import {
  Upload as UploadIcon,
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  MoreVert as MoreVertIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  Visibility as VisibilityIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { novelService, handleApiError, NovelFile, NovelContent } from '../services';

interface NovelManagerProps {
  projectId: string;
}

const NovelManager: React.FC<NovelManagerProps> = ({ projectId }) => {
  const queryClient = useQueryClient();

  // 状态管理
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [currentNovel, setCurrentNovel] = useState<NovelFile | null>(null);
  const [editContent, setEditContent] = useState('');
  const [createTitle, setCreateTitle] = useState('');
  const [createContent, setCreateContent] = useState('');
  const [notification, setNotification] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });

  const fileInputRef = useRef<HTMLInputElement>(null);

  // 获取小说文件列表
  const {
    data: novels = [],
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['novels', projectId],
    queryFn: () => novelService.getNovels(projectId),
    select: (response) => response.data,
  });

  // 上传小说文件
  const uploadMutation = useMutation({
    mutationFn: (data: { file: File; isPrimary: boolean }) =>
      novelService.uploadNovel(
        projectId,
        data.file,
        data.isPrimary,
        (progress) => setUploadProgress(progress)
      ),
    onSuccess: () => {
      setUploadDialogOpen(false);
      setSelectedFile(null);
      setUploadProgress(0);
      showNotification('小说文件上传成功', 'success');
      queryClient.invalidateQueries({ queryKey: ['novels', projectId] });
    },
    onError: (error) => {
      const apiError = handleApiError(error);
      showNotification(apiError.message, 'error');
    },
  });

  // 创建小说文件
  const createMutation = useMutation({
    mutationFn: (data: { title: string; content: string; isPrimary: boolean }) =>
      novelService.createNovel(projectId, data.title, data.content, data.isPrimary),
    onSuccess: () => {
      setCreateDialogOpen(false);
      setCreateTitle('');
      setCreateContent('');
      showNotification('小说文件创建成功', 'success');
      queryClient.invalidateQueries({ queryKey: ['novels', projectId] });
    },
    onError: (error) => {
      const apiError = handleApiError(error);
      showNotification(apiError.message, 'error');
    },
  });

  // 更新小说内容
  const updateMutation = useMutation({
    mutationFn: (data: { filename: string; content: string }) =>
      novelService.updateNovelContent(projectId, data.filename, data.content),
    onSuccess: (_, variables) => {
      setEditDialogOpen(false);
      setEditContent('');
      setCurrentNovel(null);
      showNotification('小说内容更新成功', 'success');
      // 失效小说列表缓存
      queryClient.invalidateQueries({ queryKey: ['novels', projectId] });
      // 失效具体小说内容的缓存
      queryClient.invalidateQueries({
        queryKey: ['novelContent', projectId, variables.filename]
      });
    },
    onError: (error) => {
      const apiError = handleApiError(error);
      showNotification(apiError.message, 'error');
    },
  });

  // 删除小说文件
  const deleteMutation = useMutation({
    mutationFn: (filename: string) => novelService.deleteNovel(projectId, filename),
    onSuccess: () => {
      showNotification('小说文件删除成功', 'success');
      queryClient.invalidateQueries({ queryKey: ['novels', projectId] });
      setMenuAnchor(null);
    },
    onError: (error) => {
      const apiError = handleApiError(error);
      showNotification(apiError.message, 'error');
    },
  });

  // 设置主要小说
  const setPrimaryMutation = useMutation({
    mutationFn: (filename: string) => novelService.setPrimaryNovel(projectId, filename),
    onSuccess: () => {
      showNotification('小说大纲设置成功', 'success');
      queryClient.invalidateQueries({ queryKey: ['novels', projectId] });
      setMenuAnchor(null);
    },
    onError: (error) => {
      const apiError = handleApiError(error);
      showNotification(apiError.message, 'error');
    },
  });

  // 获取小说内容
  const { data: novelContent, isLoading: contentLoading } = useQuery({
    queryKey: ['novelContent', projectId, currentNovel?.filename],
    queryFn: async () => {
      if (!currentNovel) return null;
      try {
        const response = await novelService.getNovelContent(projectId, currentNovel.filename);
        return response.data;
      } catch (error) {
        console.error('Failed to fetch novel content:', error);
        throw error;
      }
    },
    enabled: !!currentNovel && !!currentNovel.filename && (editDialogOpen || viewDialogOpen),
  });

  // 使用useEffect来处理数据更新
  React.useEffect(() => {
    if (novelContent && novelContent.content) {
      setEditContent(novelContent.content);
    }
  }, [novelContent]);

  // 显示通知
  const showNotification = (message: string, severity: 'success' | 'error') => {
    setNotification({ open: true, message, severity });
  };

  // 关闭通知
  const closeNotification = () => {
    setNotification({ ...notification, open: false });
  };

  // 处理文件选择
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const validTypes = ['text/plain', 'text/markdown'];
      if (!validTypes.includes(file.type) && !file.name.match(/\.(txt|md)$/i)) {
        showNotification('只支持 .txt 和 .md 文件', 'error');
        return;
      }
      setSelectedFile(file);
    }
  };

  // 处理文件上传
  const handleUpload = (isPrimary: boolean = false) => {
    if (!selectedFile) {
      showNotification('请选择文件', 'error');
      return;
    }
    uploadMutation.mutate({ file: selectedFile, isPrimary });
  };

  // 处理小说创建
  const handleCreate = (isPrimary: boolean = false) => {
    if (!createTitle.trim()) {
      showNotification('请输入小说标题', 'error');
      return;
    }
    if (!createContent.trim()) {
      showNotification('请输入小说内容', 'error');
      return;
    }
    createMutation.mutate({ title: createTitle, content: createContent, isPrimary });
  };

  // 处理小说编辑
  const handleEdit = () => {
    if (!currentNovel || !editContent.trim()) {
      showNotification('内容不能为空', 'error');
      return;
    }
    updateMutation.mutate({ filename: currentNovel.filename, content: editContent });
  };

  // 打开菜单
  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, novel: NovelFile) => {
    setMenuAnchor(event.currentTarget);
    setCurrentNovel(novel);
  };

  // 关闭菜单
  const handleMenuClose = () => {
    setMenuAnchor(null);
    // 不要立即清空 currentNovel，让对话框能够正常工作
  };

  // 查看小说
  const handleView = () => {
    if (currentNovel) {
      setViewDialogOpen(true);
    }
    handleMenuClose();
  };

  // 编辑小说
  const handleEditClick = () => {
    if (currentNovel) {
      setEditDialogOpen(true);
    }
    handleMenuClose();
  };

  // 删除小说
  const handleDelete = () => {
    if (currentNovel) {
      if (window.confirm(`确定要删除小说"${currentNovel.title}"吗？`)) {
        deleteMutation.mutate(currentNovel.filename);
      }
    }
    handleMenuClose();
  };

  // 设置主要小说
  const handleSetPrimary = () => {
    if (currentNovel && !currentNovel.is_primary) {
      setPrimaryMutation.mutate(currentNovel.filename);
    }
    handleMenuClose();
  };

  if (error) {
    const apiError = handleApiError(error);
    return (
      <Alert severity="error" sx={{ mb: 3 }}>
        {apiError.message}
      </Alert>
    );
  }

  return (
    <Box>
      {/* 头部操作区 */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6">小说库管理</Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<UploadIcon />}
            onClick={() => setUploadDialogOpen(true)}
          >
            上传小说
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
          >
            新建小说
          </Button>
        </Box>
      </Box>

      {/* 小说文件列表 */}
      <Paper>
        {isLoading ? (
          <Box sx={{ p: 3 }}>
            <LinearProgress />
            <Typography variant="body2" sx={{ mt: 1, textAlign: 'center' }}>
              加载中...
            </Typography>
          </Box>
        ) : novels.length === 0 ? (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              暂无小说文件
            </Typography>
            <Typography variant="body2" color="text.secondary">
              上传或创建您的第一个小说文件
            </Typography>
          </Box>
        ) : (
          <List>
            {novels.map((novel, index) => (
              <React.Fragment key={novel.filename}>
                <ListItem>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 'medium' }}>
                          {novel.title}
                        </Typography>
                        {novel.is_primary && (
                          <Chip
                            label="大纲"
                            color="primary"
                            size="small"
                            icon={<StarIcon />}
                          />
                        )}
                      </Box>
                    }
                    secondary={
                      <Typography variant="body2" color="text.secondary" component="span">
                        <Box component="span">
                          文件大小: {novelService.formatFileSize(novel.size)} |
                          修改时间: {novelService.formatDate(novel.modified_at)}
                        </Box>
                      </Typography>
                    }
                  />
                  <ListItemSecondaryAction>
                    <IconButton
                      edge="end"
                      onClick={(e) => handleMenuOpen(e, novel)}
                    >
                      <MoreVertIcon />
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItem>
                {index < novels.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>
        )}
      </Paper>

      {/* 操作菜单 */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleView}>
          <VisibilityIcon sx={{ mr: 1 }} />
          查看内容
        </MenuItem>
        <MenuItem onClick={handleEditClick}>
          <EditIcon sx={{ mr: 1 }} />
          编辑内容
        </MenuItem>
        {currentNovel && !currentNovel.is_primary && (
          <MenuItem onClick={handleSetPrimary}>
            <StarIcon sx={{ mr: 1 }} />
            设为小说大纲
          </MenuItem>
        )}
        <MenuItem onClick={handleDelete} sx={{ color: 'error.main' }}>
          <DeleteIcon sx={{ mr: 1 }} />
          删除文件
        </MenuItem>
      </Menu>

      {/* 上传对话框 */}
      <Dialog open={uploadDialogOpen} onClose={() => setUploadDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>上传小说文件</DialogTitle>
        <DialogContent>
          <Box sx={{ mb: 2 }}>
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.md"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
            <Button
              variant="outlined"
              fullWidth
              onClick={() => fileInputRef.current?.click()}
              sx={{ py: 2 }}
            >
              {selectedFile ? selectedFile.name : '选择文件'}
            </Button>
            {selectedFile && (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                文件大小: {novelService.formatFileSize(selectedFile.size)}
              </Typography>
            )}
          </Box>
          {uploadMutation.isPending && (
            <Box sx={{ mb: 2 }}>
              <LinearProgress variant="determinate" value={uploadProgress} />
              <Typography variant="body2" sx={{ mt: 1, textAlign: 'center' }}>
                上传进度: {uploadProgress}%
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUploadDialogOpen(false)}>取消</Button>
          <Button
            onClick={() => handleUpload(false)}
            variant="outlined"
            disabled={!selectedFile || uploadMutation.isPending}
          >
            上传
          </Button>
          <Button
            onClick={() => handleUpload(true)}
            variant="contained"
            disabled={!selectedFile || uploadMutation.isPending}
          >
            上传并设为小说大纲
          </Button>
        </DialogActions>
      </Dialog>

      {/* 创建对话框 */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>创建新小说</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="小说标题"
            fullWidth
            variant="outlined"
            value={createTitle}
            onChange={(e) => setCreateTitle(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            label="小说内容"
            fullWidth
            multiline
            rows={8}
            variant="outlined"
            value={createContent}
            onChange={(e) => setCreateContent(e.target.value)}
            placeholder="在这里输入您的小说内容..."
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>取消</Button>
          <Button
            onClick={() => handleCreate(false)}
            variant="outlined"
            disabled={createMutation.isPending}
          >
            创建
          </Button>
          <Button
            onClick={() => handleCreate(true)}
            variant="contained"
            disabled={createMutation.isPending}
          >
            创建并设为小说大纲
          </Button>
        </DialogActions>
      </Dialog>

      {/* 查看对话框 */}
      <Dialog open={viewDialogOpen} onClose={() => setViewDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          {currentNovel?.title}
          {currentNovel?.is_primary && (
            <Chip label="大纲" color="primary" size="small" sx={{ ml: 1 }} />
          )}
        </DialogTitle>
        <DialogContent>
          {contentLoading ? (
            <LinearProgress />
          ) : (
            <TextField
              fullWidth
              multiline
              rows={15}
              variant="outlined"
              value={novelContent?.content || editContent}
              InputProps={{ readOnly: true }}
              sx={{ '& .MuiInputBase-root': { fontFamily: 'monospace' } }}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {
            setViewDialogOpen(false);
            setCurrentNovel(null);
          }}>关闭</Button>
        </DialogActions>
      </Dialog>

      {/* 编辑对话框 */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          编辑小说
          {currentNovel?.is_primary && (
            <Chip label="大纲" color="primary" size="small" sx={{ ml: 1 }} />
          )}
        </DialogTitle>
        <DialogContent>
          {contentLoading ? (
            <LinearProgress />
          ) : (
            <TextField
              fullWidth
              multiline
              rows={15}
              variant="outlined"
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              sx={{ '& .MuiInputBase-root': { fontFamily: 'monospace' } }}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {
            setEditDialogOpen(false);
            setCurrentNovel(null);
          }}>取消</Button>
          <Button
            onClick={handleEdit}
            variant="contained"
            disabled={updateMutation.isPending || contentLoading}
          >
            保存
          </Button>
        </DialogActions>
      </Dialog>

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
  );
};

export default NovelManager;