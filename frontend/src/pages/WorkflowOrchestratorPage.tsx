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
  IconButton,
  Tooltip,
  Divider,
  Switch,
  FormControlLabel,
  InputAdornment,
  Slider,
  Tabs,
  Tab,
  Badge,
  Menu,
  MenuItem as MenuItemComponent,
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
  Settings as SettingsIcon,
  Save as SaveIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  Remove as RemoveIcon,
  Visibility as VisibilityIcon,
  Edit as EditIcon,
  ContentCopy as ContentCopyIcon,
  FileUpload as FileUploadIcon,
  DragIndicator as DragIndicatorIcon,
  SmartToy as SmartToyIcon,
  TextFields as TextFieldsIcon,
  Image as ImageIcon,
  Person as PersonIcon,
  Landscape as SceneIcon,
  Analytics as AnalyticsIcon,
  Verified as VerifiedIcon,
  Timeline as TimelineIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import { workflowService, characterService, handleApiError } from '../services';

interface AgentConfig {
  id: string;
  name: string;
  displayName: string;
  description: string;
  icon: React.ReactNode;
  enabled: boolean;
  order: number;
  parameters: Record<string, any>;
  dependencies: string[];
  estimatedTime: number;
}

interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  agents: AgentConfig[];
  isDefault: boolean;
  isCustom: boolean;
}

interface WorkflowExecution {
  workflow_id: string;
  template_id?: string;
  project_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  current_step?: string;
  total_steps: number;
  completed_steps: number;
  started_at: string;
  estimated_completion_time?: string;
  total_cost?: number;
  steps: any[];
  result?: any;
  error_message?: string;
}

const WorkflowOrchestratorPage: React.FC = () => {
  const { id: projectId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // 状态管理
  const [activeTab, setActiveTab] = useState(0);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('default');
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionId, setExecutionId] = useState<string | null>(null);
  const [notification, setNotification] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'warning';
  }>({
    open: false,
    message: '',
    severity: 'success',
  });

  // 默认Agent配置
  const defaultAgents: AgentConfig[] = [
    {
      id: 'text_analyzer',
      name: 'TextAnalyzer',
      displayName: '文本分析专家',
      description: '分析小说文本，提取角色、场景、情感等关键信息',
      icon: <TextFieldsIcon />,
      enabled: true,
      order: 0,
      parameters: {
        analysis_depth: 'comprehensive',
        extract_characters: true,
        extract_scenes: true,
        extract_emotions: true,
        model_preference: 'doubao-seed-1-6-flash-250828',
        temperature: 0.2,
      },
      dependencies: [],
      estimatedTime: 30,
    },
    {
      id: 'text_segmenter',
      name: 'TextSegmenter',
      displayName: '文本分段专家',
      description: '智能将长文本分割成符合情节完整性的段落',
      icon: <TimelineIcon />,
      enabled: true,
      order: 1,
      parameters: {
        segment_length: 1000,
        preserve_scenes: true,
        semantic_segmentation: true,
        min_segment_length: 200,
        max_segment_length: 2000,
      },
      dependencies: ['text_analyzer'],
      estimatedTime: 15,
    },
    {
      id: 'script_generator',
      name: 'ScriptGenerator',
      displayName: '脚本生成专家',
      description: '将分析结果转为详细的漫画分镜脚本',
      icon: <EditIcon />,
      enabled: true,
      order: 2,
      parameters: {
        script_style: 'manga',
        panel_per_scene: 3,
        include_dialogue: true,
        include_action: true,
        target_pages: 10,
        model_preference: 'doubao-seed-1-6-flash-250828',
        temperature: 0.3,
      },
      dependencies: ['text_analyzer', 'text_segmenter'],
      estimatedTime: 45,
    },
    {
      id: 'character_consistency',
      name: 'CharacterConsistencyAgent',
      displayName: '角色一致性专家',
      description: '确保角色在漫画中保持一致',
      icon: <PersonIcon />,
      enabled: true,
      order: 3,
      parameters: {
        consistency_threshold: 0.8,
        apply_corrections: true,
        check_visual_features: true,
        check_personality: true,
        check_appearance: true,
      },
      dependencies: ['script_generator'],
      estimatedTime: 20,
    },
    {
      id: 'scene_composer',
      name: 'SceneComposer',
      displayName: '场景合成专家',
      description: '角色+场景合成，风格统一',
      icon: <SceneIcon />,
      enabled: true,
      order: 4,
      parameters: {
        composition_style: 'balanced',
        ensure_readability: true,
        background_detail: 'medium',
        character_emphasis: 0.7,
        style_consistency: true,
      },
      dependencies: ['script_generator', 'character_consistency'],
      estimatedTime: 25,
    },
    {
      id: 'image_generator',
      name: 'ImageGenerator',
      displayName: '图像生成专家',
      description: '根据脚本生成漫画图像',
      icon: <ImageIcon />,
      enabled: true,
      order: 5,
      parameters: {
        model: 'doubao-seedream-4-0-250828',
        image_size: '1024x1024',
        quality: 'standard',
        style: 'manga',
        batch_generation: true,
        max_images_per_batch: 5,
      },
      dependencies: ['script_generator', 'scene_composer'],
      estimatedTime: 120,
    },
    {
      id: 'quality_assessor',
      name: 'QualityAssessor',
      displayName: '质量评估专家',
      description: '评估整体质量',
      icon: <AnalyticsIcon />,
      enabled: true,
      order: 6,
      parameters: {
        assessment_criteria: ['readability', 'completeness', 'accuracy', 'coherence'],
        quality_threshold: 0.7,
        generate_feedback: true,
        detailed_report: false,
      },
      dependencies: ['image_generator'],
      estimatedTime: 15,
    },
    {
      id: 'coherence_checker',
      name: 'CoherenceChecker',
      displayName: '连贯性检查专家',
      description: '检查逻辑连贯性',
      icon: <VerifiedIcon />,
      enabled: true,
      order: 7,
      parameters: {
        check_narrative_flow: true,
        check_character_behavior: true,
        check_scene_transitions: true,
        strict_mode: false,
        auto_fix_minor_issues: true,
      },
      dependencies: ['image_generator', 'quality_assessor'],
      estimatedTime: 20,
    },
  ];

  // 工作流模板
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([
    {
      id: 'default',
      name: '标准流程',
      description: '包含所有8个专家的标准工作流程',
      agents: defaultAgents,
      isDefault: true,
      isCustom: false,
    },
    {
      id: 'fast',
      name: '快速流程',
      description: '简化版本，只包含核心步骤',
      agents: defaultAgents.filter(agent =>
        ['text_analyzer', 'script_generator', 'image_generator'].includes(agent.id)
      ),
      isDefault: false,
      isCustom: false,
    },
    {
      id: 'high_quality',
      name: '高质量流程',
      description: '包含所有质量检查的完整流程',
      agents: defaultAgents,
      isDefault: false,
      isCustom: false,
    },
  ]);

  const [currentAgents, setCurrentAgents] = useState<AgentConfig[]>(defaultAgents);
  const [workflowText, setWorkflowText] = useState('');
  const [executionResult, setExecutionResult] = useState<WorkflowExecution | null>(null);
  const [agentDialogOpen, setAgentDialogOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<AgentConfig | null>(null);

  // 获取项目角色
  const { data: characters = [] } = useQuery({
    queryKey: ['characters', projectId],
    queryFn: () => projectId ? characterService.getProjectCharacters(projectId) : Promise.resolve([]),
    enabled: !!projectId,
  });

  // 执行工作流
  const executeWorkflowMutation = useMutation({
    mutationFn: (config: any) => workflowService.startWorkflow({
      project_id: projectId!,
      workflow_type: 'comic_generation',
      parameters: {
        text_content: workflowText,
        agent_config: config,
        character_data: characters,
      },
    }),
    onSuccess: (result) => {
      setExecutionId(result.id);
      setIsExecuting(true);
      showNotification('工作流执行已启动', 'success');
    },
    onError: (error) => {
      const apiError = handleApiError(error);
      showNotification(`启动失败: ${apiError.message}`, 'error');
    },
  });

  // 获取执行状态
  const { data: executionData, refetch: refetchExecutionStatus } = useQuery({
    queryKey: ['workflow_execution', executionId],
    queryFn: () => executionId ? workflowService.getWorkflowStatus(executionId) : null,
    enabled: !!executionId && isExecuting,
    refetchInterval: 2000,
  });

  // 处理执行状态变化
  useEffect(() => {
    if (executionData) {
      setExecutionResult(executionData);
      if (executionData.status === 'completed' || executionData.status === 'failed') {
        setIsExecuting(false);
        if (executionData.status === 'completed') {
          showNotification('工作流执行完成！', 'success');
        } else {
          showNotification(`执行失败: ${executionData.error_message}`, 'error');
        }
      }
    }
  }, [executionData]);

  // 处理Agent启用/禁用
  const handleToggleAgent = (agentId: string) => {
    setCurrentAgents(prev =>
      prev.map(agent =>
        agent.id === agentId ? { ...agent, enabled: !agent.enabled } : agent
      )
    );
  };

  // 处理Agent参数更新
  const handleUpdateAgentParameters = (agentId: string, parameters: Record<string, any>) => {
    setCurrentAgents(prev =>
      prev.map(agent =>
        agent.id === agentId ? { ...agent, parameters: { ...agent.parameters, ...parameters } } : agent
      )
    );
  };

  // 处理Agent配置对话框
  const openAgentDialog = (agent: AgentConfig) => {
    setSelectedAgent({ ...agent, parameters: { ...agent.parameters } });
    setAgentDialogOpen(true);
  };

  // 保存Agent配置
  const handleSaveAgentConfig = () => {
    if (selectedAgent) {
      handleUpdateAgentParameters(selectedAgent.id, selectedAgent.parameters);
      setAgentDialogOpen(false);
      setSelectedAgent(null);
    }
  };

  // 选择工作流模板
  const handleSelectTemplate = (templateId: string) => {
    const template = templates.find(t => t.id === templateId);
    if (template) {
      setCurrentAgents([...template.agents]);
      setSelectedTemplate(templateId);
    }
  };

  // 执行工作流
  const handleExecuteWorkflow = () => {
    if (!workflowText.trim()) {
      showNotification('请输入文本内容', 'error');
      return;
    }

    const enabledAgents = currentAgents.filter(agent => agent.enabled);
    if (enabledAgents.length === 0) {
      showNotification('请至少启用一个Agent', 'error');
      return;
    }

    executeWorkflowMutation.mutate({
      text_content: workflowText,
      agents: enabledAgents,
    });
  };

  // 停止执行
  const handleStopExecution = () => {
    if (executionId) {
      workflowService.cancelWorkflow(executionId).then(() => {
        setIsExecuting(false);
        showNotification('执行已停止', 'warning');
      });
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

  // 获取Agent状态图标
  const getAgentIcon = (status: string) => {
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
              工作流编排器
            </Typography>
          </Box>
          <Box>
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={() => {/* TODO: 保存配置 */}}
              sx={{ mr: 2 }}
            >
              保存配置
            </Button>
            <Button
              variant="contained"
              startIcon={<PlayArrowIcon />}
              onClick={handleExecuteWorkflow}
              disabled={isExecuting || executeWorkflowMutation.isPending}
              size="large"
            >
              执行工作流
            </Button>
          </Box>
        </Box>

        <Grid container spacing={3}>
          {/* 左侧：文本输入和模板选择 */}
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 3, mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                工作流模板
              </Typography>
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>选择模板</InputLabel>
                <Select
                  value={selectedTemplate}
                  onChange={(e) => handleSelectTemplate(e.target.value)}
                  disabled={isExecuting}
                >
                  {templates.map(template => (
                    <MenuItem key={template.id} value={template.id}>
                      <Box>
                        <Typography variant="body2">
                          {template.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {template.description}
                        </Typography>
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Button
                fullWidth
                variant="outlined"
                startIcon={<AddIcon />}
                onClick={() => {/* TODO: 创建自定义模板 */}}
              >
                创建自定义模板
              </Button>
            </Paper>

            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                输入文本
              </Typography>
              <TextField
                fullWidth
                multiline
                rows={10}
                label="文本内容"
                placeholder="在这里输入要处理的文本内容..."
                value={workflowText}
                onChange={(e) => setWorkflowText(e.target.value)}
                disabled={isExecuting}
                helperText={`${workflowText.length} 字符`}
              />
              <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                <Button
                  variant="outlined"
                  startIcon={<FileUploadIcon />}
                  onClick={() => {/* TODO: 文件上传 */}}
                  disabled={isExecuting}
                >
                  上传文件
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<ContentCopyIcon />}
                  onClick={() => {/* TODO: 示例文本 */}}
                  disabled={isExecuting}
                >
                  示例文本
                </Button>
              </Box>
            </Paper>
          </Grid>

          {/* 右侧：Agent配置 */}
          <Grid item xs={12} md={8}>
            <Paper sx={{ p: 3, mb: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h6">
                  Agent配置 ({currentAgents.filter(a => a.enabled).length}/{currentAgents.length})
                </Typography>
                <Badge badgeContent={currentAgents.filter(a => a.enabled).length} color="primary">
                  <SmartToyIcon />
                </Badge>
              </Box>

              <Stepper activeStep={-1} orientation="vertical">
                {currentAgents.map((agent, index) => (
                  <Step key={agent.id} expanded>
                    <StepLabel
                      icon={getAgentIcon(executionResult?.status || 'pending')}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          {agent.icon}
                          <Box sx={{ ml: 1 }}>
                            <Typography variant="subtitle2">
                              {agent.displayName}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              预计 {agent.estimatedTime}s · {agent.name}
                            </Typography>
                          </Box>
                        </Box>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Tooltip title="配置参数">
                            <IconButton
                              size="small"
                              onClick={() => openAgentDialog(agent)}
                              disabled={isExecuting}
                            >
                              <SettingsIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title={agent.enabled ? '禁用' : '启用'}>
                            <Switch
                              size="small"
                              checked={agent.enabled}
                              onChange={() => handleToggleAgent(agent.id)}
                              disabled={isExecuting}
                            />
                          </Tooltip>
                        </Box>
                      </Box>
                    </StepLabel>
                    <StepContent>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        {agent.description}
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {Object.entries(agent.parameters).map(([key, value]) => (
                          <Chip
                            key={key}
                            label={`${key}: ${typeof value === 'boolean' ? (value ? '是' : '否') : value}`}
                            size="small"
                            variant="outlined"
                            color={agent.enabled ? 'primary' : 'default'}
                          />
                        ))}
                      </Box>
                      {agent.dependencies.length > 0 && (
                        <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                          依赖: {agent.dependencies.join(', ')}
                        </Typography>
                      )}
                    </StepContent>
                  </Step>
                ))}
              </Stepper>
            </Paper>

            {/* 执行状态 */}
            {executionResult && (
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  执行状态
                </Typography>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    状态: {executionResult.status}
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={executionResult.progress}
                    sx={{ mt: 1 }}
                  />
                  <Typography variant="caption" sx={{ mt: 1 }}>
                    进度: {executionResult.progress}%
                  </Typography>
                </Box>
                {executionResult.started_at && (
                  <Typography variant="caption" color="text.secondary">
                    开始时间: {executionResult.started_at ? format(new Date(executionResult.started_at), 'yyyy-MM-dd HH:mm:ss') : '未知'}
                  </Typography>
                )}
                {executionResult.steps && executionResult.steps.find(s => s.status === 'completed')?.completed_at && (
                  <Typography variant="caption" color="text.secondary">
                    完成时间: {executionResult.steps.find(s => s.status === 'completed')?.completed_at ? format(new Date(executionResult.steps.find(s => s.status === 'completed')?.completed_at), 'yyyy-MM-dd HH:mm:ss') : '未知'}
                  </Typography>
                )}
                {executionResult.error_message && (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    {executionResult.error_message}
                  </Alert>
                )}
              </Paper>
            )}
          </Grid>
        </Grid>

        {/* Agent配置对话框 */}
        <Dialog
          open={agentDialogOpen}
          onClose={() => setAgentDialogOpen(false)}
          maxWidth="md"
          fullWidth
        >
          <DialogTitle>
            配置 {selectedAgent?.displayName}
          </DialogTitle>
          <DialogContent>
            {selectedAgent && (
              <Box sx={{ py: 2 }}>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {selectedAgent.description}
                </Typography>
                {Object.entries(selectedAgent.parameters).map(([key, value]) => (
                  <Box key={key} sx={{ mb: 2 }}>
                    <TextField
                      fullWidth
                      label={key}
                      value={typeof value === 'boolean' ? String(value) : value}
                      onChange={(e) => {
                        let newValue: any = e.target.value;
                        if (typeof value === 'boolean') {
                          newValue = e.target.value === 'true';
                        } else if (typeof value === 'number') {
                          newValue = Number(e.target.value);
                        }
                        setSelectedAgent({
                          ...selectedAgent,
                          parameters: {
                            ...selectedAgent.parameters,
                            [key]: newValue
                          }
                        });
                      }}
                      type={typeof value === 'number' ? 'number' : 'text'}
                      helperText={`当前值: ${value}`}
                    />
                  </Box>
                ))}
              </Box>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setAgentDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSaveAgentConfig} variant="contained">
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
    </Container>
  );
};

export default WorkflowOrchestratorPage;