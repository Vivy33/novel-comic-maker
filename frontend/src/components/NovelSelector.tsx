import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Paper,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  LinearProgress,
  TextField,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Tooltip,
  IconButton,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Visibility as VisibilityIcon,
  Edit as EditIcon,
  TextSnippet as TextIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { novelService } from '../services';

interface NovelSelectorProps {
  projectId: string;
  selectedNovel: string | null;
  onNovelSelect: (filename: string, content: string) => void;
  disabled?: boolean;
}

const NovelSelector: React.FC<NovelSelectorProps> = ({
  projectId,
  selectedNovel,
  onNovelSelect,
  disabled = false,
}) => {
  const [expandedPreview, setExpandedPreview] = useState(false);
  const [internalSelectedNovel, setInternalSelectedNovel] = useState(selectedNovel || '');

  // 获取小说文件列表
  const {
    data: novelsResponse,
    isLoading: novelsLoading,
    error: novelsError,
  } = useQuery({
    queryKey: ['novels', projectId],
    queryFn: () => novelService.getNovels(projectId),
    enabled: !!projectId,
  });

  const novels = novelsResponse?.data || [];

  // 获取选中小说的内容
  const {
    data: novelContentResponse,
    isLoading: contentLoading,
    error: contentError,
  } = useQuery({
    queryKey: ['novelContent', projectId, internalSelectedNovel],
    queryFn: () => {
      if (!internalSelectedNovel) return null;
      return novelService.getNovelContent(projectId, internalSelectedNovel);
    },
    enabled: !!internalSelectedNovel && !!projectId,
  });

  const novelContent = novelContentResponse?.data;
  const selectedNovelData = novels.find(novel => novel.filename === internalSelectedNovel);

  // 当小说内容加载完成时，通知父组件
  useEffect(() => {
    if (novelContent?.content && internalSelectedNovel) {
      onNovelSelect(internalSelectedNovel, novelContent.content);
    }
  }, [novelContent, internalSelectedNovel, onNovelSelect]);

  // 处理小说选择
  const handleNovelChange = useCallback((event: any) => {
    const filename = event.target.value;
    setInternalSelectedNovel(filename);
    setExpandedPreview(!!filename);
  }, []);

  // 仅在初始化或父组件重置时同步状态
  useEffect(() => {
    // 如果内部状态为空，但父组件有值，则同步
    if (!internalSelectedNovel && selectedNovel) {
      setInternalSelectedNovel(selectedNovel);
      setExpandedPreview(true);
    }
  }, [selectedNovel, internalSelectedNovel]);

  // 获取字符数统计
  const getWordCount = (text: string) => {
    return text.length;
  };

  // 获取预计阅读时间
  const getEstimatedReadTime = (text: string) => {
    const wordsPerMinute = 200; // 中文阅读速度约200字/分钟
    const minutes = Math.ceil(getWordCount(text) / wordsPerMinute);
    return `${minutes} 分钟`;
  };

  if (novelsError) {
    return (
      <Alert severity="error" sx={{ mb: 3 }}>
        加载小说文件失败: {novelsError.message}
      </Alert>
    );
  }

  return (
    <Box>
      {/* 小说选择区域 */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <TextIcon />
          选择小说文件
        </Typography>

        <FormControl fullWidth disabled={disabled || novelsLoading}>
          <InputLabel>选择小说</InputLabel>
          <Select
            value={internalSelectedNovel}
            onChange={handleNovelChange}
            label="选择小说"
          >
            <MenuItem value="">
              <em>请选择小说文件...</em>
            </MenuItem>
            {novels.map((novel) => (
              <MenuItem key={novel.filename} value={novel.filename}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                  <Typography variant="body1" sx={{ flexGrow: 1 }}>
                    {novel.title}
                  </Typography>
                  {novel.is_primary && (
                    <Chip
                      label="主要"
                      color="primary"
                      size="small"
                      sx={{ ml: 1 }}
                    />
                  )}
                  <Typography variant="caption" color="text.secondary">
                    {novelService.formatFileSize(novel.size)}
                  </Typography>
                </Box>
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {novelsLoading && (
          <Box sx={{ mt: 2 }}>
            <LinearProgress />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              加载小说列表中...
            </Typography>
          </Box>
        )}

        {!novelsLoading && novels.length === 0 && (
          <Alert severity="info" sx={{ mt: 2 }}>
            当前项目暂无小说文件，请先上传或创建小说文件。
          </Alert>
        )}
      </Paper>

      {/* 选中小说的信息和预览 */}
      {selectedNovelData && (
        <Paper sx={{ p: 3, mb: 3 }}>
          {/* 小说基本信息 */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Box>
              <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {selectedNovelData.title}
                {selectedNovelData.is_primary && (
                  <Chip
                    label="主要小说"
                    color="primary"
                    size="small"
                  />
                )}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                文件大小: {novelService.formatFileSize(selectedNovelData.size)} |
                修改时间: {novelService.formatDate(selectedNovelData.modified_at)}
                {novelContent?.content && (
                  <> | 字符数: {getWordCount(novelContent.content.toLocaleString())} |
                  预计阅读: {getEstimatedReadTime(novelContent.content)}</>
                )}
              </Typography>
            </Box>
            <Tooltip title="在小说管理中编辑">
              <IconButton
                size="small"
                onClick={() => {
                  // TODO: 可以跳转到小说管理页面或打开编辑对话框
                  console.log('Navigate to novel management');
                }}
              >
                <EditIcon />
              </IconButton>
            </Tooltip>
          </Box>

          {/* 内容预览 */}
          {contentError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              加载小说内容失败: {contentError.message}
            </Alert>
          )}

          {contentLoading ? (
            <Box>
              <LinearProgress />
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                加载小说内容中...
              </Typography>
            </Box>
          ) : novelContent?.content ? (
            <Accordion
              expanded={expandedPreview}
              onChange={() => setExpandedPreview(!expandedPreview)}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <VisibilityIcon fontSize="small" />
                  <Typography>内容预览</Typography>
                  <Typography variant="caption" color="text.secondary">
                    ({getWordCount(novelContent.content)} 字符)
                  </Typography>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <TextField
                  fullWidth
                  multiline
                  rows={12}
                  variant="outlined"
                  value={novelContent.content}
                  InputProps={{
                    readOnly: true,
                    style: { fontFamily: 'monospace', fontSize: '14px' }
                  }}
                  sx={{
                    '& .MuiInputBase-root': {
                      backgroundColor: 'grey.50',
                    }
                  }}
                />
                <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="caption" color="text.secondary">
                    预计阅读时间: {getEstimatedReadTime(novelContent.content)}
                  </Typography>
                  <Typography variant="caption" color="success.main">
                    ✓ 已选择此小说用于生成漫画
                  </Typography>
                </Box>
              </AccordionDetails>
            </Accordion>
          ) : null}
        </Paper>
      )}
    </Box>
  );
};

export default NovelSelector;