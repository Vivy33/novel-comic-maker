import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Paper,
  Grid,
  Chip,
  Tab,
  Tabs,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
  TextField,
} from '@mui/material';
import {
  Close as CloseIcon,
  Person as PersonIcon,
  Psychology as PsychologyIcon,
  History as HistoryIcon,
  Star as StarIcon,
  Lightbulb as LightbulbIcon,
  Favorite as FavoriteIcon,
  Flag as FlagIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
} from '@mui/icons-material';
import { characterService, apiClient } from '../services';

interface CharacterCard {
  id: string;
  character_id: string;
  character_name: string;
  front_view: {
    appearance: string;
    personality: {
      positive: string;
      negative: string;
    };
    background: string;
    skills: string[];
    stats: {
      vitality: number;
      intelligence: number;
      charisma: number;
      agility: number;
    };
    image?: {
      filename: string;
      path: string;
      prompt?: string;
      negative_prompt?: string;
    };
  };
  back_view: {
    backstory: string;
    relationships: string[];
    secrets: string[];
    goals: string[];
    image?: {
      filename: string;
      path: string;
      prompt?: string;
      negative_prompt?: string;
    };
  };
  created_at: string;
  status: string;
}

interface CharacterCardViewDialogProps {
  open: boolean;
  character: any;
  onClose: () => void;
}

const CharacterCardViewDialog: React.FC<CharacterCardViewDialogProps> = ({
  open,
  character,
  onClose,
}) => {
  const [tabValue, setTabValue] = React.useState(0);
  const [characterCard, setCharacterCard] = React.useState<CharacterCard | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [deleteLoading, setDeleteLoading] = React.useState(false);
  const [isEditing, setIsEditing] = React.useState(false);
  const [editForm, setEditForm] = React.useState<Partial<CharacterCard> | null>(null);
  const [saveLoading, setSaveLoading] = React.useState(false);

  // 获取角色卡数据
  const fetchCharacterCard = React.useCallback(async () => {
    if (!character) return;

    console.log('开始获取角色卡数据，character对象:', character);
    console.log('character.project_id:', character.project_id);
    console.log('character.name:', character.name);

    setLoading(true);
    setError(null);
    try {
      const url = `/api/characters/${character.project_id}/${character.name}/card`;
      console.log('调用API URL:', url);

      const response = await apiClient.get<any>(url);
      console.log('API响应完整数据:', response);
      console.log('response.success:', response.success);
      console.log('typeof response.success:', typeof response.success);

      // 检查响应数据格式 (apiClient.get 已经返回 response.data)
      if (response && typeof response === 'object' && 'id' in response && !('success' in response)) {
        // 如果response直接包含角色卡数据（包含id字段但没有success字段），说明API返回的是原始数据
        console.log('检测到直接角色卡数据格式，直接设置角色卡');
        setCharacterCard(response as CharacterCard);
      } else if (response && response.success) {
        // 如果是包装格式，使用response.data
        console.log('检测到包装格式，使用response.data');
        setCharacterCard(response.data);
      } else if (response && response.success === false) {
        // 明确返回失败
        console.error('API返回success=false:', response);
        setError(response.message || '获取角色卡失败');
      } else {
        // 无法识别的格式
        console.error('无法识别的API响应格式:', response);
        setError('API响应格式错误');
      }
    } catch (err: any) {
      console.error('获取角色卡时发生错误:', err);
      console.error('错误详情:', {
        message: err.message,
        response: err.response,
        status: err.response?.status,
        data: err.response?.data,
        code: err.code
      });

      // 检查是否是网络错误（没有响应状态码）
      if (!err.response && (err.code === 'NETWORK_ERROR' || err.code === 'ECONNABORTED' || err.message.includes('Network Error'))) {
        setError('网络连接错误，请检查网络连接');
      } else if (err.response?.status === 404) {
        setError('该角色尚未生成角色卡，请先生成角色卡');
      } else if (err.response?.status >= 500) {
        setError('服务器内部错误，请稍后重试');
      } else {
        // 其他错误，检查是否有具体的错误消息
        const errorMessage = err.response?.data?.message || err.message || '获取角色卡失败';
        setError(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  }, [character]);

  React.useEffect(() => {
    console.log('CharacterCardViewDialog useEffect触发:', { open, characterName: character?.name });
    if (open && character) {
      fetchCharacterCard();
    }
  }, [open, character, fetchCharacterCard]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  // 删除角色卡
  const handleDeleteCharacterCard = async () => {
    if (!character) return;

    const confirmDelete = window.confirm(`确定要删除角色 "${character.name}" 的角色卡吗？删除后可以重新生成新的角色卡。`);
    if (!confirmDelete) return;

    setDeleteLoading(true);
    try {
      // characterService 已在顶部导入
      await characterService.deleteCharacterCard(character.project_id, character.name);

      // 清除角色卡状态
      setCharacterCard(null);
      setError(null);

      // 可以显示成功消息或直接关闭对话框
      alert('角色卡删除成功！');
      onClose();
    } catch (err) {
      console.error('删除角色卡失败:', err);
      setError('删除角色卡失败，请稍后重试');
    } finally {
      setDeleteLoading(false);
    }
  };

  // 开始编辑角色卡
  const handleStartEdit = () => {
    if (!characterCard) return;
    setIsEditing(true);
    setEditForm({
      front_view: {
        ...characterCard.front_view,
        personality: {
          ...characterCard.front_view.personality
        }
      },
      back_view: {
        ...characterCard.back_view
      }
    });
  };

  // 取消编辑
  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditForm(null);
  };

  // 保存编辑
  const handleSaveEdit = async () => {
    if (!editForm || !characterCard || !character) return;

    setSaveLoading(true);
    try {
      // characterService 已在顶部导入

      // 调用更新角色卡API
      await characterService.updateCharacterCard(
        character.project_id,
        character.name,
        editForm
      );

      // 后端已确认成功（HTTP 200），直接处理为成功
      // 更新本地状态 - 重新获取角色卡数据
      try {
        await fetchCharacterCard();
        setIsEditing(false);
        setEditForm(null);
        alert('角色卡保存成功！');
      } catch (fetchErr) {
        // 即使获取失败，也认为保存成功，因为后端已返回200
        setIsEditing(false);
        setEditForm(null);
        alert('角色卡保存成功！');
      }
    } catch (err) {
      console.error('保存角色卡失败:', err);
      setError('保存角色卡失败，请稍后重试');
    } finally {
      setSaveLoading(false);
    }
  };

  // 处理表单字段变化
  const handleFormFieldChange = (path: string, value: any) => {
    if (!editForm) return;

    const keys = path.split('.');
    const newForm = { ...editForm };
    let current: any = newForm;

    for (let i = 0; i < keys.length - 1; i++) {
      if (!current[keys[i]]) {
        current[keys[i]] = {};
      }
      current = current[keys[i]];
    }

    current[keys[keys.length - 1]] = value;
    setEditForm(newForm);
  };

  const StatBar: React.FC<{
  label: string;
  value: number;
  color: string;
  isEditing?: boolean;
  onChange?: (value: number) => void;
}> = ({ label, value, color, isEditing = false, onChange }) => (
    <Box sx={{ mb: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
        <Typography variant="body2" fontWeight="bold">{label}</Typography>
        <Typography variant="body2" color="text.secondary">{value}/100</Typography>
      </Box>
      {isEditing ? (
        <TextField
          fullWidth
          type="number"
          size="small"
          value={value}
          onChange={(e) => {
            const newValue = Math.min(100, Math.max(0, parseInt(e.target.value) || 0));
            onChange?.(newValue);
          }}
          inputProps={{ min: 0, max: 100 }}
          sx={{ mb: 1 }}
        />
      ) : (
        <Box
          sx={{
            height: 8,
            backgroundColor: 'grey.300',
            borderRadius: 1,
            overflow: 'hidden',
          }}
        >
          <Box
            sx={{
              height: '100%',
              width: `${value}%`,
              backgroundColor: color,
              transition: 'width 0.3s ease',
            }}
          />
        </Box>
      )}
    </Box>
  );

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h5" component="h2">
            {character?.name} - 角色卡
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            {characterCard && (
              <>
                {isEditing ? (
                  <>
                    <Tooltip title="保存编辑">
                      <IconButton
                        onClick={handleSaveEdit}
                        disabled={saveLoading}
                        color="primary"
                      >
                        {saveLoading ? <CircularProgress size={20} /> : <SaveIcon />}
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="取消编辑">
                      <IconButton
                        onClick={handleCancelEdit}
                        disabled={saveLoading}
                        color="warning"
                      >
                        <CancelIcon />
                      </IconButton>
                    </Tooltip>
                  </>
                ) : (
                  <>
                    <Tooltip title="编辑角色卡">
                      <IconButton
                        onClick={handleStartEdit}
                        color="primary"
                      >
                        <EditIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="删除角色卡">
                      <IconButton
                        onClick={handleDeleteCharacterCard}
                        disabled={deleteLoading}
                        color="error"
                      >
                        {deleteLoading ? <CircularProgress size={20} /> : <DeleteIcon />}
                      </IconButton>
                    </Tooltip>
                  </>
                )}
              </>
            )}
            <Button onClick={onClose} startIcon={<CloseIcon />}>
              关闭
            </Button>
          </Box>
        </Box>
      </DialogTitle>

      <DialogContent>
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {!loading && !error && characterCard && (
          <Box>
            {/* 角色卡标题 */}
            <Paper sx={{ p: 3, mb: 2, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}>
              <Typography variant="h4" component="h1" gutterBottom fontWeight="bold">
                {characterCard.character_name}
              </Typography>
              <Typography variant="h6" component="h2">
                角色身份卡
              </Typography>
            </Paper>

            {/* 正反面切换标签 */}
            <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
              <Tabs value={tabValue} onChange={handleTabChange}>
                <Tab label="正面 - 角色信息" icon={<PersonIcon />} />
                <Tab label="反面 - 角色历程" icon={<HistoryIcon />} />
              </Tabs>
            </Box>

            {tabValue === 0 && (
              <Grid container spacing={3}>
                {/* 角色图片 */}
                {characterCard.front_view.image && (
                  <Grid item xs={12} md={6}>
                    <Paper sx={{ p: 3, textAlign: 'center' }}>
                      <Typography variant="h6" gutterBottom>
                        角色立绘
                      </Typography>
                      <Box
                        component="img"
                        src={character ? `/api/characters/${character.project_id}/${character.name}/card-image/front` : ''}
                        alt={`${characterCard.character_name} - 正面视图`}
                        sx={{
                          maxWidth: '100%',
                          height: 'auto',
                          maxHeight: 400,
                          borderRadius: 2,
                          boxShadow: 2
                        }}
                        onError={(e) => {
                          console.error('Image load error:', e);
                          const target = e.target as HTMLImageElement;
                          if (characterCard.front_view.image?.path) {
                            target.src = characterCard.front_view.image.path;
                          }
                        }}
                      />
                    </Paper>
                  </Grid>
                )}

                {/* 外观描述 */}
                <Grid item xs={12} md={characterCard.front_view.image ? 6 : 12}>
                  <Paper sx={{ p: 3 }}>
                    <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                      <PersonIcon sx={{ mr: 1 }} />
                      外观特征
                    </Typography>
                    {isEditing && editForm ? (
                      <TextField
                        fullWidth
                        multiline
                        rows={4}
                        value={editForm.front_view?.appearance || ''}
                        onChange={(e) => handleFormFieldChange('front_view.appearance', e.target.value)}
                        label="外观描述"
                        variant="outlined"
                      />
                    ) : (
                      <Typography variant="body1" paragraph>
                        {characterCard.front_view.appearance}
                      </Typography>
                    )}
                  </Paper>
                </Grid>

                {/* 性格特征 */}
                <Grid item xs={12} md={6}>
                  <Paper sx={{ p: 3, height: '100%' }}>
                    <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                      <PsychologyIcon sx={{ mr: 1 }} />
                      性格特征
                    </Typography>

                    <Box sx={{ mb: 2 }}>
                      <Typography variant="subtitle2" color="success.main" gutterBottom>
                        <FavoriteIcon sx={{ fontSize: 16, mr: 0.5 }} />
                        积极特质
                      </Typography>
                      {isEditing && editForm ? (
                        <TextField
                          fullWidth
                          multiline
                          rows={3}
                          value={editForm.front_view?.personality?.positive || ''}
                          onChange={(e) => handleFormFieldChange('front_view.personality.positive', e.target.value)}
                          label="积极特质"
                          variant="outlined"
                        />
                      ) : (
                        <Typography variant="body2" paragraph>
                          {characterCard.front_view.personality.positive}
                        </Typography>
                      )}
                    </Box>

                    {characterCard.front_view.personality.negative && (
                      <Box>
                        <Typography variant="subtitle2" color="warning.main" gutterBottom>
                          <FlagIcon sx={{ fontSize: 16, mr: 0.5 }} />
                          消极特质
                        </Typography>
                        {isEditing && editForm ? (
                          <TextField
                            fullWidth
                            multiline
                            rows={3}
                            value={editForm.front_view?.personality?.negative || ''}
                            onChange={(e) => handleFormFieldChange('front_view.personality.negative', e.target.value)}
                            label="消极特质"
                            variant="outlined"
                          />
                        ) : (
                          <Typography variant="body2" paragraph>
                            {characterCard.front_view.personality.negative}
                          </Typography>
                        )}
                      </Box>
                    )}
                  </Paper>
                </Grid>

                {/* 能力值 */}
                <Grid item xs={12} md={6}>
                  <Paper sx={{ p: 3, height: '100%' }}>
                    <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                      <StarIcon sx={{ mr: 1 }} />
                      能力值
                    </Typography>

                    <StatBar
                      label="体力"
                      value={isEditing && editForm ? editForm.front_view?.stats?.vitality || 0 : characterCard.front_view.stats.vitality}
                      color="#f44336"
                      isEditing={isEditing}
                      onChange={(value) => handleFormFieldChange('front_view.stats.vitality', value)}
                    />
                    <StatBar
                      label="智力"
                      value={isEditing && editForm ? editForm.front_view?.stats?.intelligence || 0 : characterCard.front_view.stats.intelligence}
                      color="#2196f3"
                      isEditing={isEditing}
                      onChange={(value) => handleFormFieldChange('front_view.stats.intelligence', value)}
                    />
                    <StatBar
                      label="魅力"
                      value={isEditing && editForm ? editForm.front_view?.stats?.charisma || 0 : characterCard.front_view.stats.charisma}
                      color="#ff9800"
                      isEditing={isEditing}
                      onChange={(value) => handleFormFieldChange('front_view.stats.charisma', value)}
                    />
                    <StatBar
                      label="敏捷"
                      value={isEditing && editForm ? editForm.front_view?.stats?.agility || 0 : characterCard.front_view.stats.agility}
                      color="#4caf50"
                      isEditing={isEditing}
                      onChange={(value) => handleFormFieldChange('front_view.stats.agility', value)}
                    />
                  </Paper>
                </Grid>

                {/* 背景描述 */}
                <Grid item xs={12}>
                  <Paper sx={{ p: 3 }}>
                    <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                      <LightbulbIcon sx={{ mr: 1 }} />
                      背景描述
                    </Typography>
                    {isEditing && editForm ? (
                      <TextField
                        fullWidth
                        multiline
                        rows={3}
                        value={editForm.front_view?.background || ''}
                        onChange={(e) => handleFormFieldChange('front_view.background', e.target.value)}
                        label="背景描述"
                        variant="outlined"
                      />
                    ) : (
                      <Typography variant="body1" paragraph>
                        {characterCard.front_view.background}
                      </Typography>
                    )}
                  </Paper>
                </Grid>

                {/* 技能列表 */}
                <Grid item xs={12}>
                  <Paper sx={{ p: 3 }}>
                    <Typography variant="h6" gutterBottom>
                      技能列表
                    </Typography>
                    {isEditing && editForm ? (
                      <Box>
                        <TextField
                          fullWidth
                          multiline
                          rows={2}
                          value={editForm.front_view?.skills?.join('、') || ''}
                          onChange={(e) => {
                            const skillsArray = e.target.value.split(/[,，]/).map(s => s.trim()).filter(s => s.length > 0);
                            handleFormFieldChange('front_view.skills', skillsArray);
                          }}
                          label="技能列表 (用逗号分隔)"
                          variant="outlined"
                          helperText="例如：剑术、魔法治疗、烹饪、驾驶"
                        />
                      </Box>
                    ) : (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        {characterCard.front_view.skills.map((skill, index) => (
                          <Chip
                            key={index}
                            label={skill}
                            variant="outlined"
                            color="primary"
                            size="small"
                          />
                        ))}
                      </Box>
                    )}
                  </Paper>
                </Grid>
              </Grid>
            )}

            {tabValue === 1 && (
              <Grid container spacing={3}>
                {/* 背面图片 */}
                {characterCard.back_view.image && (
                  <Grid item xs={12} md={6}>
                    <Paper sx={{ p: 3, textAlign: 'center' }}>
                      <Typography variant="h6" gutterBottom>
                        背面立绘
                      </Typography>
                      <Box
                        component="img"
                        src={character ? `/api/characters/${character.project_id}/${character.name}/card-image/back` : ''}
                        alt={`${characterCard.character_name} - 背面视图`}
                        sx={{
                          maxWidth: '100%',
                          height: 'auto',
                          maxHeight: 400,
                          borderRadius: 2,
                          boxShadow: 2
                        }}
                        onError={(e) => {
                          console.error('Back image load error:', e);
                          const target = e.target as HTMLImageElement;
                          if (characterCard.back_view.image?.path) {
                            target.src = characterCard.back_view.image.path;
                          }
                        }}
                      />
                    </Paper>
                  </Grid>
                )}

                {/* 角色历程梗概 */}
                <Grid item xs={12} md={characterCard.back_view.image ? 6 : 12}>
                  <Paper sx={{ p: 3 }}>
                    <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                      <HistoryIcon sx={{ mr: 1 }} />
                      角色历程梗概
                    </Typography>
                    {isEditing && editForm ? (
                      <TextField
                        fullWidth
                        multiline
                        rows={5}
                        value={editForm.back_view?.backstory || ''}
                        onChange={(e) => handleFormFieldChange('back_view.backstory', e.target.value)}
                        label="角色历程梗概"
                        variant="outlined"
                      />
                    ) : (
                      <Typography variant="body1" paragraph sx={{ lineHeight: 1.8 }}>
                        {characterCard.back_view.backstory}
                      </Typography>
                    )}
                  </Paper>
                </Grid>

                {/* 人际关系 */}
                <Grid item xs={12} md={6}>
                  <Paper sx={{ p: 3, height: '100%' }}>
                    <Typography variant="h6" gutterBottom>
                      人际关系
                    </Typography>
                    {isEditing && editForm ? (
                      <Box>
                        <TextField
                          fullWidth
                          multiline
                          rows={2}
                          value={editForm.back_view?.relationships?.join('、') || ''}
                          onChange={(e) => {
                            const relationshipsArray = e.target.value.split(/[,，]/).map(s => s.trim()).filter(s => s.length > 0);
                            handleFormFieldChange('back_view.relationships', relationshipsArray);
                          }}
                          label="人际关系"
                          variant="outlined"
                          helperText="用逗号分隔多个关系，如：与主角是青梅竹马"
                        />
                      </Box>
                    ) : (
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        {characterCard.back_view.relationships.map((relationship, index) => (
                          <Chip
                            key={index}
                            label={relationship}
                            variant="outlined"
                            color="info"
                            size="small"
                          />
                        ))}
                      </Box>
                    )}
                  </Paper>
                </Grid>

                {/* 目标追求 */}
                <Grid item xs={12} md={6}>
                  <Paper sx={{ p: 3, height: '100%' }}>
                    <Typography variant="h6" gutterBottom>
                      目标追求
                    </Typography>
                    {isEditing && editForm ? (
                      <Box>
                        <TextField
                          fullWidth
                          multiline
                          rows={2}
                          value={editForm.back_view?.goals?.join('、') || ''}
                          onChange={(e) => {
                            const goalsArray = e.target.value.split(/[,，]/).map(s => s.trim()).filter(s => s.length > 0);
                            handleFormFieldChange('back_view.goals', goalsArray);
                          }}
                          label="目标追求"
                          variant="outlined"
                          helperText="用逗号分隔多个目标，如：拯救村庄、寻找失散的家人"
                        />
                      </Box>
                    ) : (
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        {characterCard.back_view.goals.map((goal, index) => (
                          <Chip
                            key={index}
                            label={goal}
                            variant="outlined"
                            color="success"
                            size="small"
                          />
                        ))}
                      </Box>
                    )}
                  </Paper>
                </Grid>

                {/* 秘密 */}
                <Grid item xs={12}>
                  <Paper sx={{ p: 3, bgcolor: 'grey.50' }}>
                    <Typography variant="h6" gutterBottom color="warning.main">
                      🔒 秘密
                    </Typography>
                    {isEditing && editForm ? (
                      <Box>
                        <TextField
                          fullWidth
                          multiline
                          rows={3}
                          value={editForm.back_view?.secrets?.join('、') || ''}
                          onChange={(e) => {
                            const secretsArray = e.target.value.split(/[,，]/).map(s => s.trim()).filter(s => s.length > 0);
                            handleFormFieldChange('back_view.secrets', secretsArray);
                          }}
                          label="秘密"
                          variant="outlined"
                          helperText="用逗号分隔多个秘密，如：隐藏的身份、过去的创伤、不为人知的能力"
                        />
                      </Box>
                    ) : (
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        {characterCard.back_view.secrets.map((secret, index) => (
                          <Box key={index} sx={{ p: 2, bgcolor: 'white', borderRadius: 1, border: '1px solid #e0e0e0' }}>
                            <Typography variant="body2" color="text.secondary">
                              {secret}
                            </Typography>
                          </Box>
                        ))}
                      </Box>
                    )}
                  </Paper>
                </Grid>
              </Grid>
            )}
          </Box>
        )}

        {!loading && !error && !characterCard && (
          <Alert severity="info">
            该角色尚未生成角色卡，请先在角色管理界面生成角色卡。
          </Alert>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} variant="contained">
          关闭
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default CharacterCardViewDialog;