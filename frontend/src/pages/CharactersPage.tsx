import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Paper,
  Button,
  Grid,
  Card,
  CardContent,
  CardActions,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Avatar,
  IconButton,
  Menu,
  MenuItem,
  Alert,
  Snackbar,
  Fab,
  CircularProgress,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  MoreVert as MoreIcon,
  Person as PersonIcon,
  ArrowBack as ArrowBackIcon,
} from '@mui/icons-material';
import CharacterCardViewDialog from '../components/CharacterCardViewDialog';
import { useQuery, useMutation } from '@tanstack/react-query';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { characterService, handleApiError } from '../services';

interface Character {
  id: string;
  project_id: string;
  name: string;
  description?: string;
  image_url?: string;
  traits: string[];
  created_at?: string;
  updated_at?: string;
}

const CharactersPage: React.FC = () => {
  const { id } = useParams<{ id?: string }>();
  const finalProjectId = id;
  const navigate = useNavigate();
  const location = useLocation();

  // 页面加载时的调试信息
  console.log('CharactersPage 组件加载:', {
    urlParams: { id },
    projectId: finalProjectId,
    pathname: location.pathname,
    search: location.search
  });

  // 状态管理
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [cardViewDialogOpen, setCardViewDialogOpen] = useState(false);
  const [menuAnchorEl, setMenuAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedCharacter, setSelectedCharacter] = useState<Character | null>(null);
  const [editingCharacterId, setEditingCharacterId] = useState<string | null>(null);
  const [notification, setNotification] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error';
  }>({
    open: false,
    message: '',
    severity: 'success',
  });

  // 防止重复触发URL参数处理
  const [processedUrlParams, setProcessedUrlParams] = useState(false);

  // 当项目ID变化时重置URL参数处理状态
  useEffect(() => {
    setProcessedUrlParams(false);
  }, [finalProjectId, navigate]);

  // 表单数据
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    traits: '',
  });

  // 获取项目角色列表
  const {
    data: charactersData,
    isLoading,
    error,
    refetch,
  } = useQuery<Character[]>({
    queryKey: ['characters', finalProjectId],
    queryFn: () => {
      return finalProjectId ? characterService.getProjectCharacters(finalProjectId) : Promise.resolve([]);
    },
    enabled: !!finalProjectId,
    staleTime: 0,
  });

  // charactersData 是从 API 返回的数组，使用 useMemo 优化性能
  const characters = useMemo(() => charactersData ?? [], [charactersData]);

  // 添加调试日志
  console.log('CharactersPage 调试信息:', {
    projectId: finalProjectId,
    isLoading,
    error: error?.message,
    charactersData,
    charactersLength: characters.length,
    characters: characters
  });

  // 检查URL参数，自动打开角色卡查看对话框
  useEffect(() => {
    console.log('URL参数处理useEffect触发:', {
      processedUrlParams,
      search: location.search,
      charactersCount: characters.length
    });

    // 如果已经处理过URL参数，则不再处理
    if (processedUrlParams) {
      console.log('URL参数已处理过，跳过');
      return;
    }

    const searchParams = new URLSearchParams(location.search);
    const viewCard = searchParams.get('viewCard');
    const characterId = searchParams.get('characterId');

    // 解码URL编码的角色名称
    const decodedViewCard = viewCard ? decodeURIComponent(viewCard) : null;

    console.log('URL参数检查结果:', { viewCard, decodedViewCard, characterId, charactersCount: characters.length });

    if (decodedViewCard && characterId && characters.length > 0) {
      // 查找对应的角色
      const targetCharacter = characters.find(char => char.name === decodedViewCard || char.id === characterId);
      if (targetCharacter) {
        console.log('找到目标角色，准备打开对话框:', targetCharacter.name);

        // 标记为已处理
        setProcessedUrlParams(true);

        // 延迟一下确保对话框能正确打开
        setTimeout(() => {
          console.log('延迟后打开对话框');
          openCardViewDialog(targetCharacter);
        }, 500);

        // 清除URL参数，避免重复触发
        navigate(`/project/${finalProjectId}/characters`, { replace: true });
      } else {
        console.log('未找到目标角色');
      }
    }
  }, [location.search, characters, finalProjectId, processedUrlParams, navigate]);

  // 创建角色
  const createCharacterMutation = useMutation({
    mutationFn: (data: { name: string; description?: string; traits: string[] }) =>
      characterService.createCharacter({
        ...data,
        project_id: finalProjectId!,
      }),
    onSuccess: () => {
      setCreateDialogOpen(false);
      setFormData({ name: '', description: '', traits: '' });
      showNotification('角色创建成功', 'success');
      refetch();
    },
    onError: (error) => {
      const apiError = handleApiError(error);
      showNotification(apiError.message, 'error');
    },
  });

  // 更新角色
  const updateCharacterMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Character> }) =>
      characterService.updateCharacter(id, data),
    onSuccess: () => {
      setEditDialogOpen(false);
      setSelectedCharacter(null);
      setEditingCharacterId(null);
      showNotification('角色更新成功', 'success');
      refetch();
    },
    onError: (error) => {
      const apiError = handleApiError(error);
      showNotification(apiError.message, 'error');
    },
  });

  // 删除角色
  const deleteCharacterMutation = useMutation({
    mutationFn: (character: Character) => characterService.deleteCharacter(character),
    onSuccess: () => {
      setDeleteDialogOpen(false);
      setSelectedCharacter(null);
      showNotification('角色删除成功', 'success');
      refetch();
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

  // 处理创建角色
  const handleCreateCharacter = () => {
    if (!formData.name.trim()) {
      showNotification('请输入角色名称', 'error');
      return;
    }

    const traitsArray = formData.traits
      .split(',')
      .map(trait => trait.trim())
      .filter(trait => trait.length > 0);

    createCharacterMutation.mutate({
      name: formData.name.trim(),
      description: formData.description.trim() || undefined,
      traits: traitsArray,
    });
  };

  // 打开编辑对话框
  const openEditDialog = (character: Character) => {
    setSelectedCharacter(character);
    setEditingCharacterId(character.id);
    setFormData({
      name: character.name,
      description: character.description || '',
      traits: character.traits.join(', '),
    });
    setEditDialogOpen(true);
  };

  // 处理编辑角色
  const handleEditCharacter = () => {
    // 使用editingCharacterId而不是selectedCharacter
    if (!editingCharacterId) {
      showNotification('请先选择要编辑的角色', 'error');
      return;
    }

    if (!formData.name.trim()) {
      showNotification('请输入角色名称', 'error');
      return;
    }

    const traitsArray = formData.traits
      .split(',')
      .map(trait => trait.trim())
      .filter(trait => trait.length > 0);

    updateCharacterMutation.mutate({
      id: editingCharacterId,
      data: {
        name: formData.name.trim(),
        description: formData.description.trim() || undefined,
        traits: traitsArray,
      },
    });
  };

  // 打开角色卡查看对话框
  const openCardViewDialog = (character: Character) => {
    setSelectedCharacter(character);
    setCardViewDialogOpen(true);
  };

  // 处理生成角色卡
  const handleGenerateCharacterCard = (character: Character) => {
    navigate(`/project/${finalProjectId}/characters/${character.id}/${character.name}/generate-card`);
  };

  // 菜单处理
  const handleMenuClick = (event: React.MouseEvent<HTMLElement>, character: Character) => {
    setMenuAnchorEl(event.currentTarget);
    setSelectedCharacter(character);
  };

  // 关闭菜单
  const handleMenuClose = () => {
    setMenuAnchorEl(null);
    setSelectedCharacter(null);
  };

  // 不清除角色状态的菜单关闭函数
  const handleMenuCloseWithoutClearingCharacter = () => {
    setMenuAnchorEl(null);
  };

  
  if (error) {
    return (
      <Container maxWidth="lg">
        <Box sx={{ py: 4 }}>
          <Alert severity="error" sx={{ mb: 2 }}>
            加载角色列表失败: {handleApiError(error).message}
          </Alert>
          <Button variant="outlined" onClick={() => refetch()}>
            重试
          </Button>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        {/* 页面标题 */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Button
              startIcon={<ArrowBackIcon />}
              onClick={() => navigate(`/project/${finalProjectId}`)}
              sx={{ mr: 2 }}
            >
              返回项目
            </Button>
            <Typography variant="h4" component="h1">
              角色管理
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
          >
            新建角色
          </Button>
        </Box>

        {/* 角色列表 */}
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <CircularProgress size={60} />
          </Box>
        ) : characters.length === 0 ? (
          <Paper sx={{ p: 6, textAlign: 'center' }}>
            <PersonIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              还没有角色
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              创建您的第一个角色，AI将帮助您生成一致的角色形象
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setCreateDialogOpen(true)}
            >
              创建角色
            </Button>
          </Paper>
        ) : (
          <Grid container spacing={3}>
            {characters.map((character: Character) => (
              <Grid item xs={12} sm={6} md={4} key={character.id}>
                <Card
                  sx={{
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    transition: 'transform 0.2s, box-shadow 0.2s',
                    '&:hover': {
                      transform: 'translateY(-4px)',
                      boxShadow: 4,
                    },
                  }}
                >
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <Avatar
                        src={character.image_url}
                        alt={character.name}
                        sx={{ width: 64, height: 64, mr: 2 }}
                      >
                        {character.name.charAt(0)}
                      </Avatar>
                      <Box sx={{ flexGrow: 1 }}>
                        <Typography variant="h6" component="h2" noWrap>
                          {character.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          创建于 {format(new Date(character.created_at || ''), 'yyyy-MM-dd', { locale: zhCN })}
                        </Typography>
                      </Box>
                      <IconButton
                        size="small"
                        onClick={(e) => handleMenuClick(e, character)}
                      >
                        <MoreIcon />
                      </IconButton>
                    </Box>

                    {character.description && (
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{
                          mb: 2,
                          display: '-webkit-box',
                          WebkitLineClamp: 3,
                          WebkitBoxOrient: 'vertical',
                          overflow: 'hidden',
                        }}
                      >
                        {character.description}
                      </Typography>
                    )}

                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 2 }}>
                      {character.traits.map((trait: string, index: number) => (
                        <Chip
                          key={index}
                          label={trait}
                          size="small"
                          variant="outlined"
                          color="primary"
                        />
                      ))}
                    </Box>
                  </CardContent>

                  <CardActions>
                    <Button
                      size="small"
                      startIcon={<EditIcon />}
                      onClick={() => openEditDialog(character)}
                    >
                      编辑
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      color="secondary"
                      onClick={() => openCardViewDialog(character)}
                    >
                      查看角色卡
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      color="primary"
                      onClick={() => handleGenerateCharacterCard(character)}
                    >
                      生成角色卡
                    </Button>
                  </CardActions>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}

        {/* 浮动创建按钮 (移动端) */}
        <Fab
          color="primary"
          aria-label="add"
          sx={{
            position: 'fixed',
            bottom: 16,
            right: 16,
            display: { xs: 'flex', sm: 'none' },
          }}
          onClick={() => setCreateDialogOpen(true)}
        >
          <AddIcon />
        </Fab>
      </Box>

      {/* 菜单 */}
      <Menu
        anchorEl={menuAnchorEl}
        open={Boolean(menuAnchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem
          onClick={() => {
            if (selectedCharacter) {
              setDeleteDialogOpen(true);
              // 使用不清除角色状态的菜单关闭函数
              handleMenuCloseWithoutClearingCharacter();
            }
          }}
          sx={{ color: 'error.main' }}
        >
          <DeleteIcon sx={{ mr: 1 }} />
          删除角色
        </MenuItem>
      </Menu>

      {/* 创建角色对话框 */}
      <Dialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>创建新角色</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="角色名称"
            fullWidth
            variant="outlined"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            label="角色描述"
            fullWidth
            multiline
            rows={3}
            variant="outlined"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            helperText="描述角色的外貌、性格、背景等"
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            label="角色特征"
            fullWidth
            variant="outlined"
            value={formData.traits}
            onChange={(e) => setFormData({ ...formData, traits: e.target.value })}
            helperText="用逗号分隔多个特征，如：勇敢、善良、聪明"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>
            取消
          </Button>
          <Button
            onClick={handleCreateCharacter}
            variant="contained"
            disabled={createCharacterMutation.isPending || !formData.name.trim()}
          >
            {createCharacterMutation.isPending ? <CircularProgress size={20} /> : '创建'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 编辑角色对话框 */}
      <Dialog
        open={editDialogOpen}
        onClose={() => {
          setEditDialogOpen(false);
          setEditingCharacterId(null);
        }}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>编辑角色</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="角色名称"
            fullWidth
            variant="outlined"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            label="角色描述"
            fullWidth
            multiline
            rows={3}
            variant="outlined"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            helperText="描述角色的外貌、性格、背景等"
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            label="角色特征"
            fullWidth
            variant="outlined"
            value={formData.traits}
            onChange={(e) => setFormData({ ...formData, traits: e.target.value })}
            helperText="用逗号分隔多个特征，如：勇敢、善良、聪明"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {
            setEditDialogOpen(false);
            setSelectedCharacter(null);
            setEditingCharacterId(null);
          }}
          >
            取消
          </Button>
          <Button
            onClick={handleEditCharacter}
            variant="contained"
            disabled={updateCharacterMutation.isPending}
          >
            {updateCharacterMutation.isPending ? <CircularProgress size={20} /> : '保存'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 删除角色对话框 */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => {
          setDeleteDialogOpen(false);
          setSelectedCharacter(null);
        }}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>确认删除角色</DialogTitle>
        <DialogContent>
          <Typography>
            确定要删除角色 "{selectedCharacter?.name}" 吗？此操作无法撤销。
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {
            setDeleteDialogOpen(false);
            setSelectedCharacter(null);
          }}
          >
            取消
          </Button>
          <Button
            onClick={() => selectedCharacter && deleteCharacterMutation.mutate(selectedCharacter)}
            color="error"
            variant="contained"
            disabled={deleteCharacterMutation.isPending}
          >
            {deleteCharacterMutation.isPending ? <CircularProgress size={20} /> : '删除'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 角色卡查看对话框 */}
      <CharacterCardViewDialog
        open={cardViewDialogOpen}
        character={selectedCharacter}
        onClose={() => setCardViewDialogOpen(false)}
      />

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

export default CharactersPage;