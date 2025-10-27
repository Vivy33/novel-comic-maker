import React, { useState } from 'react';
import {
  Box,
  Grid,
  Card,
  CardMedia,
  CardContent,
  Typography,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Chip,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Badge,
} from '@mui/material';
import {
  ZoomIn as ZoomInIcon,
  MoreVert as MoreVertIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  DragIndicator as DragIcon,
  CheckCircle as CheckCircleIcon,
  RadioButtonUnchecked as UncheckedIcon,
} from '@mui/icons-material';
import { ComicPanel, ParagraphInfo } from '../models/comic';

interface PanelGridDisplayProps {
  panels: ComicPanel[];
  paragraphs?: ParagraphInfo[];
  onPanelReorder?: (panelIds: number[], newOrder: number[]) => void;
  onPanelDelete?: (panelIds: number[]) => void;
  onPanelUpdateNotes?: (panelId: number, notes: string) => void;
  onPanelReassign?: (panelIds: number[], paragraphId: string) => void;
  editable?: boolean;
  title?: string;
  projectId?: string;  // 新增项目ID prop
}

const PanelGridDisplay: React.FC<PanelGridDisplayProps> = ({
  panels,
  paragraphs = [],
  onPanelReorder,
  onPanelDelete,
  onPanelUpdateNotes,
  onPanelReassign,
  editable = false,
  title = "分镜图",
  projectId,  // 新增项目ID prop
}) => {
  const [selectedPanels, setSelectedPanels] = useState<Set<number>>(new Set());
  const [previewPanel, setPreviewPanel] = useState<ComicPanel | null>(null);
  const [editNotesPanel, setEditNotesPanel] = useState<ComicPanel | null>(null);
  const [notesText, setNotesText] = useState('');
  const [panelMenuAnchor, setPanelMenuAnchor] = useState<null | HTMLElement>(null);
  const [selectedPanelForMenu, setSelectedPanelForMenu] = useState<ComicPanel | null>(null);

  // 添加组件加载调试日志
  console.log('🎯 PanelGridDisplay 组件加载:', {
    panelsCount: panels.length,
    paragraphsCount: paragraphs.length,
    projectId: projectId,
    title: title
  });

  // 处理图片路径，将相对路径转换为完整URL
  const getImageUrl = (imagePath: string | null | undefined): string => {
    if (!imagePath) {
      return '/placeholder-image.png';
    }

    // 如果是完整URL，直接返回
    if (imagePath.startsWith('http')) {
      return imagePath;
    }

    // 如果是相对路径，转换为静态文件服务URL
    if (imagePath.startsWith('images/')) {
      // 优先使用传入的projectId，否则从URL推断
      let currentProjectId = projectId;

      if (!currentProjectId) {
        const currentPath = window.location.pathname;
        const projectIdMatch = currentPath.match(/\/project\/([^\/]+)/);
        currentProjectId = projectIdMatch ? projectIdMatch[1] : '';
      }

      // URL解码以处理中文项目ID
      if (currentProjectId) {
        try {
          const decodedProjectId = decodeURIComponent(currentProjectId);
          const finalUrl = `/projects/${decodedProjectId}/chapters/chapter_001/${imagePath}`;

          // 调试日志
          console.log('🖼️ getImageUrl debug:', {
            originalProjectId: currentProjectId,
            decodedProjectId: decodedProjectId,
            imagePath: imagePath,
            finalUrl: finalUrl
          });

          return finalUrl;
        } catch (error) {
          console.error('❌ URL解码失败:', error, '使用原始ID');
          return `/projects/${currentProjectId}/chapters/chapter_001/${imagePath}`;
        }
      }
    }

    return imagePath;
  };

  // 按段落分组分镜图
  const getPanelsByParagraph = () => {
    if (paragraphs.length > 0) {
      return paragraphs.map(paragraph => ({
        paragraph,
        panels: panels.filter(panel => panel.paragraph_id === paragraph.paragraph_id),
      }));
    } else {
      // 如果没有段落信息，创建一个默认分组
      return [{
        paragraph: {
          paragraph_id: 'default',
          paragraph_index: 0,
          content: '未分组分镜图',
          panels: panels,
          panel_count: panels.length,
          confirmed_count: panels.filter(p => p.confirmed).length,
        },
        panels,
      }];
    }
  };

  const handlePanelSelect = (panelId: number, event: React.MouseEvent) => {
    event.stopPropagation();
    const newSelected = new Set(selectedPanels);
    if (newSelected.has(panelId)) {
      newSelected.delete(panelId);
    } else {
      newSelected.add(panelId);
    }
    setSelectedPanels(newSelected);
  };

  const handlePanelPreview = (panel: ComicPanel) => {
    console.log('🔍 handlePanelPreview 被调用:', {
      panelId: panel.panel_id,
      imagePath: panel.image_path,
      description: panel.description
    });
    setPreviewPanel(panel);
  };

  const handlePanelMenuOpen = (event: React.MouseEvent<HTMLElement>, panel: ComicPanel) => {
    event.stopPropagation();
    setPanelMenuAnchor(event.currentTarget);
    setSelectedPanelForMenu(panel);
  };

  const handlePanelMenuClose = () => {
    setPanelMenuAnchor(null);
    setSelectedPanelForMenu(null);
  };

  const handleEditNotes = (panel: ComicPanel) => {
    setEditNotesPanel(panel);
    setNotesText(panel.notes || '');
    handlePanelMenuClose();
  };

  const handleSaveNotes = () => {
    if (editNotesPanel && onPanelUpdateNotes) {
      onPanelUpdateNotes(editNotesPanel.panel_id, notesText);
      setEditNotesPanel(null);
      setNotesText('');
    }
  };

  const handleDeletePanel = () => {
    if (selectedPanelForMenu && onPanelDelete) {
      onPanelDelete([selectedPanelForMenu.panel_id]);
      handlePanelMenuClose();
    }
  };

  const handleBatchDelete = () => {
    if (selectedPanels.size > 0 && onPanelDelete) {
      onPanelDelete(Array.from(selectedPanels));
      setSelectedPanels(new Set());
    }
  };

  const PanelCard: React.FC<{ panel: ComicPanel; isParagraphGroup?: boolean }> = ({ panel, isParagraphGroup = false }) => {
    console.log('🖼️ PanelCard 渲染:', {
      panelId: panel.panel_id,
      imagePath: panel.image_path,
      isClickable: true
    });

    return (
    <Card
      sx={{
        position: 'relative',
        cursor: 'pointer',
        transition: 'transform 0.2s, box-shadow 0.2s',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: 3,
        },
        border: selectedPanels.has(panel.panel_id) ? '2px solid primary.main' : '1px solid #e0e0e0',
      }}
      onClick={() => handlePanelPreview(panel)}
    >
      {/* 选择框 */}
      {editable && (
        <Box
          sx={{
            position: 'absolute',
            top: 8,
            left: 8,
            zIndex: 1,
            backgroundColor: 'rgba(255,255,255,0.9)',
            borderRadius: '50%',
            width: 24,
            height: 24,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
          onClick={(e) => handlePanelSelect(panel.panel_id, e)}
        >
          {selectedPanels.has(panel.panel_id) ? (
            <CheckCircleIcon sx={{ fontSize: 16, color: 'primary.main' }} />
          ) : (
            <UncheckedIcon sx={{ fontSize: 16, color: 'grey.500' }} />
          )}
        </Box>
      )}

      {/* 更多菜单 */}
      {editable && (
        <IconButton
          size="small"
          sx={{
            position: 'absolute',
            top: 8,
            right: 8,
            zIndex: 1,
            backgroundColor: 'rgba(255,255,255,0.9)',
          }}
          onClick={(e) => handlePanelMenuOpen(e, panel)}
        >
          <MoreVertIcon fontSize="small" />
        </IconButton>
      )}

      <CardMedia
        component="img"
        image={getImageUrl(panel.image_path)}
        alt={`分镜图 ${panel.panel_id}`}
        sx={{
          height: 160,
          objectFit: 'cover',
        }}
        onError={(e) => {
          const target = e.target as HTMLImageElement;
          target.src = '/placeholder-image.png';
        }}
      />
      <CardContent sx={{ p: 1, '&:last-child': { pb: 1 } }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
          <Typography variant="caption" fontWeight="bold">
            #{panel.panel_id}
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            {panel.confirmed ? (
              <CheckCircleIcon sx={{ fontSize: 14, color: 'success.main' }} />
            ) : (
              <UncheckedIcon sx={{ fontSize: 14, color: 'grey.400' }} />
            )}
            {panel.notes && (
              <Tooltip title="有备注">
                <EditIcon sx={{ fontSize: 14, color: 'info.main' }} />
              </Tooltip>
            )}
          </Box>
        </Box>

        <Typography
          variant="caption"
          color="text.secondary"
          sx={{
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
            lineHeight: 1.2,
          }}
        >
          {panel.description || panel.scene_description}
        </Typography>

        {/* 段落信息 */}
        {panel.paragraph_id && panel.paragraph_id !== 'default' && (
          <Chip
            label={`段落 ${panel.paragraph_index || panel.paragraph_id}`}
            size="small"
            variant="outlined"
            sx={{ mt: 0.5, fontSize: '10px', height: 18 }}
          />
        )}
      </CardContent>
    </Card>
    );
  };

  const panelsByParagraph = getPanelsByParagraph();

  return (
    <Box>
      {/* 标题和批量操作 */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h6">{title}</Typography>
        {editable && selectedPanels.size > 0 && (
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="批量删除">
              <IconButton size="small" color="error" onClick={handleBatchDelete}>
                <DeleteIcon />
              </IconButton>
            </Tooltip>
            <Badge badgeContent={selectedPanels.size} color="primary">
              <Typography variant="body2" color="text.secondary">
                已选择
              </Typography>
            </Badge>
          </Box>
        )}
      </Box>

      {/* 分段落显示分镜图 */}
      {panelsByParagraph.map(({ paragraph, panels: paragraphPanels }, index) => (
        <Box key={paragraph.paragraph_id} sx={{ mb: 3 }}>
          {/* 段落标题 */}
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              mb: 1.5,
              pb: 1,
              borderBottom: '1px solid #e0e0e0',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="subtitle1" fontWeight="bold">
                {paragraph.paragraph_index !== 0 ? `段落 ${paragraph.paragraph_index}` : paragraph.content}
              </Typography>
              <Chip
                label={`${paragraphPanels.length} 张分镜图`}
                size="small"
                color="primary"
                variant="outlined"
              />
              {paragraph.confirmed_count > 0 && (
                <Chip
                  label={`${paragraph.confirmed_count} 已确认`}
                  size="small"
                  color="success"
                  variant="outlined"
                />
              )}
            </Box>
            {editable && (
              <IconButton size="small">
                <DragIcon />
              </IconButton>
            )}
          </Box>

          {/* 段落内容预览 */}
          {paragraph.content && paragraph.content !== '未分组分镜图' && (
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{
                mb: 1.5,
                p: 1,
                backgroundColor: 'grey.50',
                borderRadius: 1,
                fontStyle: 'italic',
                display: '-webkit-box',
                WebkitLineClamp: 3,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
              }}
            >
              {paragraph.content}
            </Typography>
          )}

          {/* 分镜图网格 */}
          {paragraphPanels.length > 0 ? (
            <Grid container spacing={2}>
              {paragraphPanels.map((panel) => (
                <Grid item xs={12} sm={6} md={4} lg={3} key={panel.panel_id}>
                  <PanelCard panel={panel} />
                </Grid>
              ))}
            </Grid>
          ) : (
            <Box
              sx={{
                p: 3,
                textAlign: 'center',
                backgroundColor: 'grey.50',
                borderRadius: 1,
                border: '2px dashed #ccc',
              }}
            >
              <Typography variant="body2" color="text.secondary">
                该段落暂无分镜图
              </Typography>
            </Box>
          )}
        </Box>
      ))}

      {/* 图片预览对话框 */}
      <Dialog
        open={!!previewPanel}
        onClose={() => setPreviewPanel(null)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          分镜图 #{previewPanel?.panel_id} - {previewPanel?.description}
        </DialogTitle>
        <DialogContent>
          {previewPanel && (
            <Box>
              <Box
                component="img"
                src={getImageUrl(previewPanel.image_path)}
                alt={`分镜图 ${previewPanel.panel_id}`}
                sx={{
                  width: '100%',
                  maxHeight: 400,
                  objectFit: 'contain',
                  mb: 2,
                }}
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  target.src = '/placeholder-image.png';
                }}
              />
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" gutterBottom>
                    场景描述:
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {previewPanel.scene_description}
                  </Typography>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" gutterBottom>
                    角色: {previewPanel.characters.join(', ')}
                  </Typography>
                  <Typography variant="subtitle2" gutterBottom>
                    情感: {previewPanel.emotion}
                  </Typography>
                </Grid>
                {previewPanel.notes && (
                  <Grid item xs={12}>
                    <Typography variant="subtitle2" gutterBottom>
                      备注:
                    </Typography>
                    <Typography variant="body2" color="info.main">
                      {previewPanel.notes}
                    </Typography>
                  </Grid>
                )}
              </Grid>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewPanel(null)}>关闭</Button>
        </DialogActions>
      </Dialog>

      {/* 编辑备注对话框 */}
      <Dialog
        open={!!editNotesPanel}
        onClose={() => setEditNotesPanel(null)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>编辑分镜图备注</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            multiline
            rows={4}
            label="备注内容"
            value={notesText}
            onChange={(e) => setNotesText(e.target.value)}
            placeholder="添加关于这个分镜图的备注..."
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditNotesPanel(null)}>取消</Button>
          <Button onClick={handleSaveNotes} variant="contained">
            保存
          </Button>
        </DialogActions>
      </Dialog>

      {/* 面板操作菜单 */}
      <Menu
        anchorEl={panelMenuAnchor}
        open={!!panelMenuAnchor}
        onClose={handlePanelMenuClose}
      >
        <MenuItem onClick={() => selectedPanelForMenu && handleEditNotes(selectedPanelForMenu)}>
          <ListItemIcon>
            <EditIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>编辑备注</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleDeletePanel} sx={{ color: 'error.main' }}>
          <ListItemIcon>
            <DeleteIcon fontSize="small" color="error" />
          </ListItemIcon>
          <ListItemText>删除</ListItemText>
        </MenuItem>
      </Menu>
    </Box>
  );
};

export default PanelGridDisplay;