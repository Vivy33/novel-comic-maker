import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Paper,
  Button,
  CircularProgress,
  Chip,
  Grid,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Snackbar,
  Tabs,
  Tab,
} from '@mui/material';
import { ArrowBack as ArrowBackIcon, Edit as EditIcon } from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { projectService, handleApiError } from '../services';
import NovelManager from '../components/NovelManager';
import ComicManagementPage from './ComicManagementPage';

const ProjectPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // 状态管理
  const [currentTab, setCurrentTab] = useState(0);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editForm, setEditForm] = useState({
    name: '',
    description: '',
  });
  const [notification, setNotification] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });

  // 获取项目详情
  const {
    data: project,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['project', id],
    queryFn: () => id ? projectService.getProject(id) : Promise.resolve(null),
    enabled: !!id,
  });

  // 更新项目
  const updateProjectMutation = useMutation({
    mutationFn: (data: { name?: string; description?: string }) =>
      id ? projectService.updateProject(id, data) : Promise.resolve(null),
    onSuccess: (updatedProject) => {
      setEditDialogOpen(false);
      showNotification('项目更新成功', 'success');
      queryClient.invalidateQueries({ queryKey: ['project', id] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });

      // 如果项目名称改变了，更新URL以反映新的项目ID
      if (updatedProject && updatedProject.id !== id) {
        navigate(`/project/${updatedProject.id}`, { replace: true });
      }
    },
    onError: (error) => {
      const apiError = handleApiError(error);
      showNotification(apiError.message, 'error');
    },
  });

  // 显示通知
  const showNotification = (message: string, severity: 'success' | 'error') => {
    setNotification({ open: true, message, severity });
  };

  // 关闭通知
  const closeNotification = () => {
    setNotification({ ...notification, open: false });
  };

  // 打开编辑对话框
  const handleOpenEditDialog = () => {
    if (project) {
      setEditForm({
        name: project.name,
        description: project.description || '',
      });
      setEditDialogOpen(true);
    }
  };

  // 处理编辑项目
  const handleUpdateProject = () => {
    if (!editForm.name.trim()) {
      showNotification('请输入项目名称', 'error');
      return;
    }

    const updateData: { name?: string; description?: string } = {
      name: editForm.name,
    };

    if (editForm.description !== project?.description) {
      updateData.description = editForm.description;
    }

    updateProjectMutation.mutate(updateData);
  };

  // 处理标签页切换
  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  if (isLoading) {
    return (
      <Container maxWidth="lg">
        <Box sx={{ py: 4, display: 'flex', justifyContent: 'center' }}>
          <CircularProgress size={60} />
        </Box>
      </Container>
    );
  }

  if (error) {
    const apiError = handleApiError(error);
    return (
      <Container maxWidth="lg">
        <Box sx={{ py: 4 }}>
          <Alert severity="error" sx={{ mb: 3 }}>
            {apiError.message}
          </Alert>
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate('/projects')}
          >
            返回项目列表
          </Button>
        </Box>
      </Container>
    );
  }

  if (!project) {
    return (
      <Container maxWidth="lg">
        <Box sx={{ py: 4 }}>
          <Alert severity="warning" sx={{ mb: 3 }}>
            项目不存在
          </Alert>
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate('/projects')}
          >
            返回项目列表
          </Button>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        {/* 返回按钮 */}
        <Box sx={{ mb: 3 }}>
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate('/projects')}
          >
            返回项目列表
          </Button>
        </Box>

        {/* 项目标题 */}
        <Paper sx={{ p: 4, mb: 3 }}>
          <Typography variant="h4" component="h1" gutterBottom>
            {project.name}
          </Typography>

          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Typography variant="h6" color="text.secondary" gutterBottom>
                项目信息
              </Typography>
              <Typography variant="body1" sx={{ mb: 1 }}>
                <strong>创建时间:</strong> {new Date(project.created_at).toLocaleString('zh-CN', {
                  year: 'numeric',
                  month: '2-digit',
                  day: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </Typography>
              <Typography variant="body1" sx={{ mb: 1 }}>
                <strong>更新时间:</strong> {new Date(project.updated_at).toLocaleString('zh-CN', {
                  year: 'numeric',
                  month: '2-digit',
                  day: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </Typography>
              {project.description && (
                <Typography variant="body1" sx={{ mt: 2, mb: 1 }}>
                  <strong>描述:</strong> {project.description}
                </Typography>
              )}
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography variant="h6" color="text.secondary" gutterBottom>
                项目状态
              </Typography>
              <Box sx={{ mb: 1 }}>
                <Chip
                  label={project.status}
                  color={
                    project.status === 'completed' ? 'success' :
                    project.status === 'in_progress' ? 'warning' :
                    project.status === 'error' ? 'error' : 'default'
                  }
                  size="small"
                />
              </Box>
              <Box sx={{ mt: 2 }}>
                <Button
                  variant="outlined"
                  startIcon={<EditIcon />}
                  onClick={handleOpenEditDialog}
                  size="small"
                >
                  编辑项目
                </Button>
              </Box>
            </Grid>
          </Grid>
        </Paper>

        {/* 项目内容标签页 */}
        <Paper sx={{ p: 0 }}>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs value={currentTab} onChange={handleTabChange}>
              <Tab label="小说库" />
              <Tab label="角色管理" />
              <Tab label="漫画生成" />
              <Tab label="漫画管理" />
            </Tabs>
          </Box>

          {/* 标签页内容 */}
          <Box sx={{ p: 3 }}>
            {currentTab === 0 && (
              <NovelManager projectId={id!} />
            )}

            {currentTab === 1 && (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <Button
                  variant="contained"
                  onClick={() => navigate(`/project/${id}/characters`)}
                  size="large"
                >
                  管理角色
                </Button>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                  配置和管理您的角色信息
                </Typography>
              </Box>
            )}

            {currentTab === 2 && (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <Typography variant="h6" gutterBottom>
                  选择生成方式
                </Typography>

                <Box sx={{ display: 'flex', gap: 3, justifyContent: 'center', mb: 3, flexWrap: 'wrap' }}>
                  {/* 封面生成 */}
                  <Paper
                    sx={{
                      p: 3,
                      width: 240,
                      height: 180,
                      display: 'flex',
                      flexDirection: 'column',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      '&:hover': {
                        transform: 'translateY(-2px)',
                        boxShadow: 3
                      }
                    }}
                    onClick={() => navigate(`/project/${id}/cover-generate`)}
                  >
                    <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'bold' }}>
                      ⚡ 封面生成
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2, flexGrow: 1 }}>
                      快速生成<br />漫画封面和章节封面
                    </Typography>
                    <Box sx={{ mt: 'auto' }}>
                      <Button variant="outlined" fullWidth>
                        开始生成
                      </Button>
                    </Box>
                  </Paper>

                  {/* 分段生成 */}
                  <Paper
                    sx={{
                      p: 3,
                      width: 240,
                      height: 180,
                      display: 'flex',
                      flexDirection: 'column',
                      cursor: 'pointer',
                      border: '2px solid',
                      borderColor: 'primary.main',
                      transition: 'all 0.2s',
                      '&:hover': {
                        transform: 'translateY(-2px)',
                        boxShadow: 3
                      }
                    }}
                    onClick={() => navigate(`/project/${id}/generate-segmented`)}
                  >
                    <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'bold', color: 'primary.main' }}>
                      🎯 分段生成
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2, flexGrow: 1 }}>
                      逐步分段生成，每段可手动选择最佳效果
                    </Typography>
                    <Box sx={{ mt: 'auto' }}>
                      <Button variant="contained" fullWidth>
                        开始生成
                      </Button>
                    </Box>
                  </Paper>

                  {/* 图片编辑 */}
                  <Paper
                    sx={{
                      p: 3,
                      width: 240,
                      height: 180,
                      display: 'flex',
                      flexDirection: 'column',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      '&:hover': {
                        transform: 'translateY(-2px)',
                        boxShadow: 3
                      }
                    }}
                    onClick={() => navigate(`/project/${id}/image-edit`)}
                  >
                    <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'bold' }}>
                      🖼️ 图片编辑
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2, flexGrow: 1 }}>
                      编辑和优化图片效果，使用AI工具增强图像
                    </Typography>
                    <Box sx={{ mt: 'auto' }}>
                      <Button variant="outlined" fullWidth>
                        开始编辑
                      </Button>
                    </Box>
                  </Paper>
                </Box>

                <Typography variant="body2" color="text.secondary">
                  💡 推荐：分段生成可以更好地控制质量，选择最佳图片效果
                </Typography>
              </Box>
            )}

            {currentTab === 3 && (
              <ComicManagementPage projectId={id!} />
            )}
          </Box>
        </Paper>
      </Box>

      {/* 编辑项目对话框 */}
      <Dialog
        open={editDialogOpen}
        onClose={() => setEditDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>编辑项目信息</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="项目名称"
            fullWidth
            variant="outlined"
            value={editForm.name}
            onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            label="项目描述"
            fullWidth
            multiline
            rows={3}
            variant="outlined"
            value={editForm.description}
            onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
            helperText="可选：描述您的项目内容和目标"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>
            取消
          </Button>
          <Button
            onClick={handleUpdateProject}
            variant="contained"
            disabled={updateProjectMutation.isPending || !editForm.name.trim()}
          >
            {updateProjectMutation.isPending ? '保存中...' : '保存'}
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
    </Container>
  );
};

export default ProjectPage;