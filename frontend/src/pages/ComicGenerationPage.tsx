import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
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
  Stepper,
  Step,
  StepLabel,
  StepContent,
  LinearProgress,
  Alert,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  FormGroup,
  FormControlLabel,
  Checkbox,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  PlayArrow as PlayArrowIcon,
  Pause as PauseIcon,
  Stop as StopIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  RadioButtonUnchecked as PendingIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Visibility as VisibilityIcon,
  Edit as EditIcon,
  Image as ImageIcon,
  TextFields as TextFieldsIcon,
  AutoStories as ScriptIcon,
  Person as PersonIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { comicService, characterService, workflowService, handleApiError } from '../services';
import NovelSelector from '../components/NovelSelector';

interface GenerationStep {
  id: string;
  name: string;
  description: string;
  agent: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  progress: number;
  startTime?: string;
  endTime?: string;
  result?: any;
  error?: string;
}

interface ProjectCharacter {
  id: string;
  name: string;
  description: string;
  created_at: string;
}

interface ComicGenerationResult {
  comic_id: string;
  title: string;
  panels: Array<{
    panel_number: number;
    scene_description: string;
    dialogue: string;
    image_url?: string;
    local_path?: string;
    status: string;
  }>;
  total_panels: number;
  estimated_pages: number;
  generation_time: number;
}

const ComicGenerationPage: React.FC = () => {
  const { id: projectId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // 状态管理
  const [activeStep, setActiveStep] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const [generationSteps, setGenerationSteps] = useState<GenerationStep[]>([]);
  const [notification, setNotification] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'warning';
  }>({
    open: false,
    message: '',
    severity: 'success',
  });

  // 表单数据
  const [formData, setFormData] = useState({
    selected_novel_file: '' as string,
    novel_content: '' as string,
    reference_images: [] as string[],
    style_requirements: '',
    selected_images: [] as string[], // 新增：用户选择的图片
    available_project_characters: [] as ProjectCharacter[], // 新增：项目可用角色
    selected_project_characters: [] as string[], // 新增：用户选择的角色
  });

  // 结果数据
  const [generationResult, setGenerationResult] = useState<ComicGenerationResult | null>(null);
  const [previewPanel, setPreviewPanel] = useState<number | null>(null);

  // 获取项目角色
  const { data: characters = [] } = useQuery({
    queryKey: ['characters', projectId],
    queryFn: () => projectId ? characterService.getProjectCharacters(projectId) : Promise.resolve([]),
    enabled: !!projectId,
  });

  // 启动漫画生成工作流
  const startGenerationMutation = useMutation({
    mutationFn: (data: any) => {
      // 构建完整的请求参数，包含所有用户配置
      const workflowParameters = {
        ...data,
        // 新增：用户选择的图片
        selected_reference_images: formData.selected_images,
        // 新增：用户选择的项目角色
        selected_project_characters: formData.selected_project_characters,

        // 确保图片学习参数被传递
        reference_images_for_learning: formData.reference_images,

        // 传递其他用户配置
        user_preferences: {
          style_requirements: formData.style_requirements
        }
      };

      return workflowService.startWorkflow({
        project_id: projectId!,
        workflow_type: 'comic_generation',
        parameters: workflowParameters,
      });
    },
    onSuccess: (result) => {
      setWorkflowId(result.id); // 使用转换后的响应格式
      setIsGenerating(true);
      initializeGenerationSteps();
      showNotification('漫画生成工作流已启动', 'success');
    },
    onError: (error) => {
      const apiError = handleApiError(error);
      showNotification(`启动失败: ${apiError.message}`, 'error');
    },
  });

  // 获取工作流状态
  const { data: workflowData, refetch: refetchWorkflowStatus } = useQuery({
    queryKey: ['workflow_status', workflowId],
    queryFn: () => workflowId ? workflowService.getWorkflowStatus(workflowId) : null,
    enabled: !!workflowId && isGenerating,
    refetchInterval: 2000, // 每2秒查询一次状态
  });

  // 处理工作流状态变化
  useEffect(() => {
    if (workflowData) {
      updateGenerationSteps(workflowData);
      if (workflowData.status === 'completed' || workflowData.status === 'failed') {
        setIsGenerating(false);
        if (workflowData.status === 'completed') {
          setGenerationResult(workflowData.result);
          showNotification('漫画生成完成！', 'success');
        } else {
          showNotification(`生成失败: ${workflowData.error_message}`, 'error');
        }
      }
    }
  }, [workflowData]);

  // 初始化生成步骤
  const initializeGenerationSteps = () => {
    setGenerationSteps([
      {
        id: 'text_analysis',
        name: '文本分析',
        description: '分析小说文本，提取角色、场景、情感等关键信息',
        agent: 'TextAnalyzer',
        status: 'pending',
        progress: 0,
      },
      {
        id: 'text_segmentation',
        name: '文本分段',
        description: '智能将长文本分割成符合情节完整性的段落',
        agent: 'TextSegmenter',
        status: 'pending',
        progress: 0,
      },
      {
        id: 'script_generation',
        name: '脚本生成',
        description: '将分析结果转为详细的漫画分镜脚本',
        agent: 'ScriptGenerator',
        status: 'pending',
        progress: 0,
      },
      {
        id: 'image_generation',
        name: '图像生成',
        description: '根据脚本生成漫画图像',
        agent: 'ImageGenerator',
        status: 'pending',
        progress: 0,
      },
      {
        id: 'character_consistency',
        name: '角色一致性检查',
        description: '确保角色在漫画中保持一致',
        agent: 'CharacterConsistencyAgent',
        status: 'pending',
        progress: 0,
      },
      {
        id: 'scene_composition',
        name: '场景合成',
        description: '角色+场景合成，风格统一',
        agent: 'SceneComposer',
        status: 'pending',
        progress: 0,
      },
      {
        id: 'quality_assessment',
        name: '质量评估',
        description: '评估整体质量',
        agent: 'QualityAssessor',
        status: 'pending',
        progress: 0,
      },
      {
        id: 'coherence_check',
        name: '连贯性检查',
        description: '检查逻辑连贯性',
        agent: 'CoherenceChecker',
        status: 'pending',
        progress: 0,
      },
    ]);
  };

  // 更新生成步骤状态
  const updateGenerationSteps = (workflowData: any) => {
    if (!workflowData?.steps) return;

    setGenerationSteps(prevSteps =>
      prevSteps.map(step => {
        const workflowStep = workflowData.steps.find((ws: any) => ws.step_id === step.id);
        if (workflowStep) {
          return {
            ...step,
            status: workflowStep.status,
            progress: workflowStep.progress,
            startTime: workflowStep.started_at,
            endTime: workflowStep.completed_at,
            result: workflowStep.output_data,
            error: workflowStep.error_message,
          };
        }
        return step;
      })
    );
  };

  // 处理开始生成
  const handleStartGeneration = () => {
    if (!formData.selected_novel_file.trim()) {
      showNotification('请选择小说文件', 'error');
      return;
    }

    if (!formData.novel_content.trim()) {
      showNotification('小说内容为空，请重新选择文件', 'error');
      return;
    }

    startGenerationMutation.mutate({
      text_content: formData.novel_content,
      selected_novel_file: formData.selected_novel_file,
      manga_type: '连载漫画',
      reference_images: formData.reference_images,
      style_requirements: formData.style_requirements,
    });
  };

  // 处理停止生成
  const handleStopGeneration = () => {
    if (workflowId) {
      workflowService.cancelWorkflow(workflowId).then(() => {
        setIsGenerating(false);
        showNotification('生成已停止', 'warning');
      });
    }
  };

  // 处理重新生成
  const handleRegenerate = () => {
    setActiveStep(0);
    setGenerationResult(null);
    setWorkflowId(null);
    initializeGenerationSteps();
  };

  // 处理小说选择
  const handleNovelSelect = (filename: string, content: string) => {
    setFormData({
      ...formData,
      selected_novel_file: filename,
      novel_content: content,
    });
  };

  // 显示通知
  const showNotification = (message: string, severity: 'success' | 'error' | 'warning') => {
    setNotification({ open: true, message, severity });
  };

  // 关闭通知
  const closeNotification = () => {
    setNotification({ ...notification, open: false });
  };

  // 获取步骤状态图标
  const getStepIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon color="success" />;
      case 'running':
        return <PendingIcon color="primary" />;
      case 'error':
        return <ErrorIcon color="error" />;
      default:
        return <PendingIcon color="disabled" />;
    }
  };

  // 获取步骤颜色
  const getStepColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'running':
        return 'primary';
      case 'error':
        return 'error';
      default:
        return 'grey';
    }
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
              漫画生成
            </Typography>
          </Box>
          <Box>
            {!isGenerating ? (
              <Button
                variant="contained"
                startIcon={<PlayArrowIcon />}
                onClick={handleStartGeneration}
                disabled={startGenerationMutation.isPending}
                size="large"
              >
                开始生成
              </Button>
            ) : (
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button
                  variant="outlined"
                  startIcon={<StopIcon />}
                  onClick={handleStopGeneration}
                  color="error"
                >
                  停止
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<RefreshIcon />}
                  onClick={() => refetchWorkflowStatus()}
                >
                  刷新
                </Button>
              </Box>
            )}
          </Box>
        </Box>

        <Grid container spacing={3}>
          {/* 左侧：输入和配置 */}
          <Grid item xs={12} md={6}>
            {/* 小说选择组件 */}
            <NovelSelector
              projectId={projectId!}
              selectedNovel={formData.selected_novel_file}
              onNovelSelect={handleNovelSelect}
              disabled={isGenerating}
            />

            <Paper sx={{ p: 3, mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                生成配置
              </Typography>
              <TextField
                fullWidth
                multiline
                rows={3}
                label="风格要求（可选）"
                placeholder="描述您想要的特定风格要求，如'暗黑风格'、'萌系'等..."
                value={formData.style_requirements}
                onChange={(e) => setFormData({ ...formData, style_requirements: e.target.value })}
                disabled={isGenerating}
                helperText="风格要求将作为生成参考，主要风格通过上传参考图片控制"
              />
            </Paper>

            {/* 项目角色选择 */}
            {characters.length > 0 && (
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  选择角色 (可选)
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  选择用于漫画生成的角色，不选择则不使用任何角色
                </Typography>
                <FormGroup>
                  {characters.map((character) => (
                    <FormControlLabel
                      key={character.id}
                      control={
                        <Checkbox
                          checked={formData.selected_project_characters.includes(character.id)}
                          onChange={(e) => {
                            const characterId = character.id;
                            if (e.target.checked) {
                              setFormData({
                                ...formData,
                                selected_project_characters: [...formData.selected_project_characters, characterId]
                              });
                            } else {
                              setFormData({
                                ...formData,
                                selected_project_characters: formData.selected_project_characters.filter(id => id !== characterId)
                              });
                            }
                          }}
                        />
                      }
                      label={
                        <Box>
                          <Typography variant="body1">{character.name}</Typography>
                          <Typography variant="body2" color="text.secondary">
                            {character.description}
                          </Typography>
                          <Box sx={{ mt: 1 }}>
                            <Chip
                              label={`${character.traits.length} 特征`}
                              size="small"
                              variant="outlined"
                            />
                          </Box>
                        </Box>
                      }
                    />
                  ))}
                </FormGroup>
              </Paper>
            )}
          </Grid>

          {/* 右侧：生成进度和结果 */}
          <Grid item xs={12} md={6}>
            {/* 生成进度 */}
            <Paper sx={{ p: 3, mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                生成进度
              </Typography>
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  总体进度: {Math.round(generationSteps.filter(s => s.status === 'completed').length / generationSteps.length * 100)}%
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={generationSteps.filter(s => s.status === 'completed').length / generationSteps.length * 100}
                  sx={{ mt: 1 }}
                />
              </Box>
              <Stepper activeStep={activeStep} orientation="vertical">
                {generationSteps.map((step, index) => (
                  <Step key={step.id} completed={step.status === 'completed'}>
                    <StepLabel
                      icon={getStepIcon(step.status)}
                      color={getStepColor(step.status)}
                    >
                      <Box>
                        <Typography variant="subtitle2">
                          {step.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {step.agent}
                        </Typography>
                      </Box>
                    </StepLabel>
                    <StepContent>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        {step.description}
                      </Typography>
                      {step.status === 'running' && (
                        <Box>
                          <LinearProgress
                            variant="determinate"
                            value={step.progress}
                            sx={{ mb: 1 }}
                          />
                          <Typography variant="caption">
                            进度: {step.progress}%
                          </Typography>
                        </Box>
                      )}
                      {step.error && (
                        <Alert severity="error" sx={{ mb: 1 }}>
                          {step.error}
                        </Alert>
                      )}
                      {step.status === 'completed' && step.startTime && (
                        <Typography variant="caption" color="success.main">
                          完成，用时: step.endTime ?
                            Math.round((new Date(step.endTime).getTime() - new Date(step.startTime).getTime()) / 1000) + '秒' :
                            '处理中'
                        </Typography>
                      )}
                    </StepContent>
                  </Step>
                ))}
              </Stepper>
            </Paper>

            {/* 生成结果 */}
            {generationResult && (
              <Paper sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6">
                    生成结果
                  </Typography>
                  <Button
                    variant="outlined"
                    startIcon={<RefreshIcon />}
                    onClick={handleRegenerate}
                    size="small"
                  >
                    重新生成
                  </Button>
                </Box>

                <Typography variant="subtitle1" gutterBottom>
                  {generationResult.title}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  共 {generationResult.total_panels} 个分镜，预计 {generationResult.estimated_pages} 页
                </Typography>

                {/* 分镜列表 */}
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography>查看分镜详情</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <List>
                      {generationResult.panels.map((panel) => (
                        <ListItem key={panel.panel_number} divider>
                          <ListItemIcon>
                            <ImageIcon />
                          </ListItemIcon>
                          <ListItemText
                            primary={`分镜 ${panel.panel_number}`}
                            secondary={
                              <Box>
                                <Typography variant="body2" color="text.secondary">
                                  {panel.scene_description}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  对话: {panel.dialogue}
                                </Typography>
                              </Box>
                            }
                          />
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Chip
                              label={panel.status}
                              size="small"
                              color={panel.status === 'completed' ? 'success' : 'default'}
                            />
                            {panel.image_url && (
                              <Tooltip title="查看图片">
                                <IconButton
                                  size="small"
                                  onClick={() => setPreviewPanel(panel.panel_number)}
                                >
                                  <VisibilityIcon />
                                </IconButton>
                              </Tooltip>
                            )}
                          </Box>
                        </ListItem>
                      ))}
                    </List>
                  </AccordionDetails>
                </Accordion>

                {/* 操作按钮 */}
                <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                  <Button
                    variant="contained"
                    startIcon={<VisibilityIcon />}
                    onClick={() => navigate(`/comic/${generationResult.comic_id}`)}
                  >
                    查看完整漫画
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<EditIcon />}
                    onClick={() => {/* TODO: 编辑功能 */}}
                  >
                    编辑漫画
                  </Button>
                </Box>
              </Paper>
            )}
          </Grid>
        </Grid>

        {/* 图片预览对话框 */}
        <Dialog
          open={previewPanel !== null}
          onClose={() => setPreviewPanel(null)}
          maxWidth="md"
          fullWidth
        >
          <DialogTitle>
            分镜 {previewPanel} 预览
          </DialogTitle>
          <DialogContent>
            {previewPanel && generationResult && (
              <Box sx={{ textAlign: 'center', py: 2 }}>
                <img
                  src={generationResult.panels.find(p => p.panel_number === previewPanel)?.image_url}
                  alt={`分镜 ${previewPanel}`}
                  style={{ maxWidth: '100%', maxHeight: '500px' }}
                />
                <Typography variant="body2" sx={{ mt: 2 }}>
                  {generationResult.panels.find(p => p.panel_number === previewPanel)?.scene_description}
                </Typography>
              </Box>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setPreviewPanel(null)}>
              关闭
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
    </Container>
  );
};

export default ComicGenerationPage;