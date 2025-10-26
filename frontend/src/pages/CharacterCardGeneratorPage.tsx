import React, { useState, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Grid,
  Paper,
  Alert,
  CircularProgress,
  LinearProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Divider,
  IconButton,
  Container
} from '@mui/material';
import { CloudUpload, Delete, AutoAwesome } from '@mui/icons-material';
import { useNavigate, useParams } from 'react-router-dom';
import { characterService, handleApiError } from '../services';
import apiClient from '../services/api';
import { Character } from '../services/api';


interface CharacterCardGeneratorProps {}

interface UploadedImage {
  file: File;
  preview_url: string;
  type: 'reference' | 'front' | 'back' | 'side';
}

const CharacterCardGenerator: React.FC<CharacterCardGeneratorProps> = () => {
  const navigate = useNavigate();
  const { id: projectId, characterId, characterName } = useParams<{
    id: string;
    characterId: string;
    characterName: string;
  }>();

  const [character, setCharacter] = useState<Character | null>(null);
  const [uploadedImages, setUploadedImages] = useState<UploadedImage[]>([]);
  const [prompt, setPrompt] = useState('');
  const [negativePrompt, setNegativePrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [generationProgress, setGenerationProgress] = useState({
    stage: '',
    message: '',
    progress: 0
  });

  // 获取角色详情 - 从URL参数中构建角色信息
  React.useEffect(() => {
    console.log('CharacterCardGeneratorPage - URL参数:', { characterId, projectId, characterName });
    if (characterId && projectId && characterName) {
      // 构建角色信息，因为后端API需要project_id和character_name
      const characterData: Character = {
        id: characterId,
        project_id: projectId,
        name: characterName,
        description: '', // 这些信息从URL参数无法获取，可以留空
        traits: [],
        created_at: '',
        updated_at: ''
      };
      console.log('CharacterCardGeneratorPage - 设置角色数据:', characterData);
      setCharacter(characterData);
    } else {
      console.error('CharacterCardGeneratorPage - 缺少必要参数:', { characterId, projectId, characterName });
    }
  }, [characterId, projectId, characterName]);

  // 处理文件上传
  const handleFileUpload = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || !characterId) return;

    Array.from(files).forEach(async (file) => {
      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = async (e) => {
          const preview_url = e.target?.result as string;
          const newImage: UploadedImage = {
            file,
            preview_url,
            type: 'reference' // 默认为参考图
          };

          // 添加到预览列表
          setUploadedImages(prev => [...prev, newImage]);

          // 直接上传到角色目录作为参考图片
          try {
            if (character) {
              await characterService.uploadCharacterReferenceImage(
                character.project_id,
                character.name,
                file
              );
              console.log('Reference image uploaded successfully:', file.name);
            }
          } catch (error) {
            console.error('Failed to upload reference image:', error);
            // 即使上传失败，也保留预览，让用户知道有问题
          }
        };
        reader.readAsDataURL(file);
      }
    });
  }, [characterId, character]);

  // 删除上传的图片
  const removeImage = useCallback((index: number) => {
    setUploadedImages(prev => prev.filter((_, i) => i !== index));
  }, []);

  // 更改图片类型
  const updateImageType = useCallback((index: number, type: UploadedImage['type']) => {
    setUploadedImages(prev =>
      prev.map((img, i) => i === index ? { ...img, type } : img)
    );
  }, []);

  // 生成角色卡
  const handleGenerateCard = useCallback(async () => {
    if (!projectId || !characterName) {
      setError('缺少项目ID或角色名称');
      return;
    }

    // 检查是否提供了足够的信息 - 不强制要求上传图片，但给予提示
    if (uploadedImages.length === 0) {
      // 显示提示信息，但不阻止生成
      setSuccess('提示：建议上传参考图片以获得更准确的角色卡，但您也可以仅使用文本描述生成。');
      // 3秒后清除提示信息，让生成过程继续
      setTimeout(() => {
        setSuccess(null);
      }, 3000);
    }

    if (!prompt.trim()) {
      setError('请提供生成描述以帮助AI生成更准确的角色卡');
      return;
    }

    setIsGenerating(true);
    // 保留无图片提示信息，不清除
    if (uploadedImages.length > 0) {
      setSuccess(null); // 只有上传了图片时才清除成功消息
    }

    try {
      // 开始分析阶段 - 模拟处理时间
      setGenerationProgress({
        stage: '正在分析角色信息',
        message: 'AI正在分析您的角色信息...',
        progress: 10
      });
      await new Promise(resolve => setTimeout(resolve, 1000));

      // 上传阶段
      setGenerationProgress({
        stage: '准备参考图片',
        message: uploadedImages.length > 0
          ? `正在准备上传 ${uploadedImages.length} 张参考图片...`
          : '跳过图片上传，将根据文本描述生成...',
        progress: 30
      });
      await new Promise(resolve => setTimeout(resolve, 800));

      // 参考图片已通过用户界面上传到角色目录，无需额外上传
      // 后端会自动扫描角色目录中的图片作为参考图片
      if (uploadedImages.length > 0) {
        setGenerationProgress({
          stage: '准备参考图片',
          message: `已准备 ${uploadedImages.length} 张参考图片，系统将自动分析图片特征`,
          progress: 50
        });
        await new Promise(resolve => setTimeout(resolve, 1000));
      } else {
        // 没有上传图片，直接跳到生成阶段
        setGenerationProgress({
          stage: '准备生成',
          message: '将根据文本描述生成角色卡...',
          progress: 50
        });
        await new Promise(resolve => setTimeout(resolve, 1200));
      }

      // 生成阶段 - 模拟更详细的步骤
      setGenerationProgress({
        stage: '正在生成正面视图',
        message: 'AI正在生成角色正面立绘...',
        progress: 60
      });
      await new Promise(resolve => setTimeout(resolve, 1500));

      setGenerationProgress({
        stage: '正在生成背面视图',
        message: 'AI正在生成角色背面立绘...',
        progress: 75
      });
      await new Promise(resolve => setTimeout(resolve, 1500));

      setGenerationProgress({
        stage: '正在生成角色信息',
        message: 'AI正在生成角色属性、技能和背景故事...',
        progress: 90
      });
      await new Promise(resolve => setTimeout(resolve, 1000));

      // 调用角色卡生成API
      await apiClient.post<any>(
        `/api/characters/${projectId}/${characterName}/generate-card`,
        {
          prompt,
          negative_prompt: negativePrompt
        }
      );

      
      setGenerationProgress({
        stage: '生成完成',
        message: '角色卡生成成功！准备跳转到角色详情页面...',
        progress: 100
      });

      setSuccess('角色卡生成成功！🎉 包含正面和背面视图的详细角色卡已生成完成。3秒后将自动跳转到角色管理页面查看...');

      // 3秒后跳转到角色管理页面
      setTimeout(() => {
        console.log('准备跳转，参数:', { projectId, characterName, characterId });

        if (!projectId) {
          console.error('项目ID缺失，无法跳转');
          setError('项目ID缺失，请手动前往角色管理页面查看');
          return;
        }

        const navigateUrl = characterName && characterId
          ? `/project/${projectId}/characters?viewCard=${encodeURIComponent(characterName)}&characterId=${characterId}`
          : `/project/${projectId}/characters`;

        console.log('跳转到:', navigateUrl);
        navigate(navigateUrl);
      }, 3000);

    } catch (error) {
      console.error('Failed to generate character card:', error);

      setGenerationProgress({
        stage: '生成失败',
        message: '生成角色卡时出现错误，请检查网络连接或重试',
        progress: 0
      });

      const apiError = handleApiError(error);
      setError(apiError.message);
    } finally {
      setIsGenerating(false);
    }
  }, [projectId, characterId, characterName, uploadedImages, prompt, negativePrompt, navigate]);

  const getImageTypeLabel = (type: UploadedImage['type']) => {
    const labels = {
      reference: '参考图',
      front: '正面图',
      back: '背面图',
      side: '侧面图'
    };
    return labels[type] || '参考图';
  };

  const getImageTypeColor = (type: UploadedImage['type']) => {
    const colors = {
      reference: 'default',
      front: 'primary',
      back: 'secondary',
      side: 'success'
    };
    return colors[type] || 'default';
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Button
          variant="outlined"
          onClick={() => navigate(-1)}
          sx={{ mb: 2 }}
        >
          ← 返回角色列表
        </Button>

        <Typography variant="h4" component="h1" gutterBottom>
          生成角色卡
        </Typography>

        {character && (
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6">{character.name}</Typography>
            <Typography variant="body2" color="text.secondary">
              {character.description}
            </Typography>
            <Box sx={{ mt: 1 }}>
              {character.traits.map((trait: string, index: number) => (
                <Chip key={index} label={trait} size="small" sx={{ mr: 1, mb: 1 }} />
              ))}
            </Box>
          </Paper>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 3 }}>
          {success}
        </Alert>
      )}

      <Grid container spacing={4}>
        {/* 左侧：上传图片区域 */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <CloudUpload sx={{ mr: 1, verticalAlign: 'middle' }} />
                上传参考图片
              </Typography>

              <Paper
                variant="outlined"
                sx={{
                  p: 3,
                  textAlign: 'center',
                  border: '2px dashed',
                  borderColor: 'primary.main',
                  bgcolor: 'background.default',
                  cursor: 'pointer',
                  '&:hover': {
                    bgcolor: 'action.hover'
                  }
                }}
                onClick={() => document.getElementById('image-upload')?.click()}
              >
                <CloudUpload sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
                <Typography variant="body1" gutterBottom>
                  上传角色参考图片（可选）
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 'bold', mb: 1 }}>
                  📸 建议上传全身照：正面、侧面、背面完整图有助于生成更准确的角色卡
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  支持 JPG、PNG、JPEG 格式 | 也可仅使用文本描述生成
                </Typography>
                <input
                  id="image-upload"
                  type="file"
                  multiple
                  accept="image/*"
                  style={{ display: 'none' }}
                  onChange={handleFileUpload}
                />
              </Paper>

              {/* 已上传的图片列表 */}
              {uploadedImages.length > 0 && (
                <Box sx={{ mt: 3 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    已上传的图片 ({uploadedImages.length})
                  </Typography>
                  <Grid container spacing={2}>
                    {uploadedImages.map((image, index) => (
                      <Grid item xs={6} sm={4} key={index}>
                        <Paper variant="outlined" sx={{ p: 1, position: 'relative' }}>
                          <Box
                            component="img"
                            src={image.preview_url}
                            alt={`Upload ${index + 1}`}
                            sx={{
                              width: '100%',
                              height: 80,
                              objectFit: 'cover',
                              borderRadius: 1
                            }}
                          />

                          <IconButton
                            size="small"
                            onClick={() => removeImage(index)}
                            sx={{
                              position: 'absolute',
                              top: 4,
                              right: 4,
                              bgcolor: 'rgba(0,0,0,0.5)',
                              color: 'white',
                              '&:hover': {
                                bgcolor: 'rgba(0,0,0,0.7)'
                              }
                            }}
                          >
                            <Delete fontSize="small" />
                          </IconButton>

                          <FormControl size="small" sx={{ mt: 1, width: '100%' }}>
                            <InputLabel>图片类型</InputLabel>
                            <Select
                              value={image.type}
                              label="图片类型"
                              onChange={(e) => updateImageType(index, e.target.value as UploadedImage['type'])}
                            >
                              <MenuItem value="reference">参考图</MenuItem>
                              <MenuItem value="front">正面图</MenuItem>
                              <MenuItem value="back">背面图</MenuItem>
                              <MenuItem value="side">侧面图</MenuItem>
                            </Select>
                          </FormControl>

                          <Chip
                            label={getImageTypeLabel(image.type)}
                            color={getImageTypeColor(image.type) as any}
                            size="small"
                            sx={{ mt: 1, width: '100%' }}
                          />
                        </Paper>
                      </Grid>
                    ))}
                  </Grid>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* 右侧：生成参数设置 */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <AutoAwesome sx={{ mr: 1, verticalAlign: 'middle' }} />
                生成参数设置
              </Typography>

              <Box sx={{ mb: 3 }}>
                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  label="生成描述 (Prompt)"
                  placeholder="请详细描述角色的外观、服装、发型、身材特征等。建议包含：全身造型描述、身高体型、服装细节、配饰、性格表现等。例如：身材高挑的女性角色，身穿蓝色连衣裙，长发飘逸，面带微笑..."
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  helperText="详细描述有助于生成更准确的角色卡，特别是全身造型描述"
                />
              </Box>

              <Box sx={{ mb: 3 }}>
                <TextField
                  fullWidth
                  multiline
                  rows={3}
                  label="负面描述 (Negative Prompt)"
                  placeholder="描述不希望出现的内容..."
                  value={negativePrompt}
                  onChange={(e) => setNegativePrompt(e.target.value)}
                  helperText="避免生成不希望出现的元素"
                />
              </Box>

              <Divider sx={{ my: 3 }} />

              <Typography variant="subtitle2" gutterBottom>
                使用说明：
              </Typography>
              <Box sx={{ mb: 3 }}>
                <Typography variant="body2" color="text.secondary" component="div">
                  <ul>
                    <li><strong>图片上传（可选）</strong>：上传全身照、正面、侧面、背面图片有助于生成更准确的角色卡</li>
                    <li><strong>文本描述（必需）</strong>：详细描述角色的外观、服装、性格等特征</li>
                    <li>系统会自动生成包含正面和背面的详细角色卡</li>
                    <li>角色卡包含角色属性、技能、关系等完整信息</li>
                    <li>生成过程可能需要等待1-3分钟</li>
                  </ul>
                </Typography>
              </Box>

              {/* 进度显示 */}
              {isGenerating && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="body2" color="primary" gutterBottom>
                    {generationProgress.stage}
                  </Typography>
                  <Box sx={{ mt: 1 }}>
                    <LinearProgress
                      variant="determinate"
                      value={generationProgress.progress}
                      sx={{ height: 8, borderRadius: 4 }}
                    />
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      {generationProgress.message}
                    </Typography>
                  </Box>
                </Box>
              )}

              <Button
                fullWidth
                variant="contained"
                size="large"
                startIcon={isGenerating ? <CircularProgress size={20} /> : <AutoAwesome />}
                onClick={handleGenerateCard}
                disabled={isGenerating || !characterId || !prompt.trim()}
                sx={{ py: 1.5, mb: 2 }}
              >
                {isGenerating ? '正在生成角色卡...' : '开始生成角色卡'}
              </Button>

              {/* 生成成功后显示手动跳转按钮 */}
              {success && !isGenerating && projectId && characterName && characterId && (
                <Button
                  fullWidth
                  variant="outlined"
                  size="large"
                  onClick={() => {
                    const encodedCharacterName = encodeURIComponent(characterName);
                    const navigateUrl = `/project/${projectId}/characters?viewCard=${encodedCharacterName}&characterId=${characterId}`;
                    navigate(navigateUrl);
                  }}
                  sx={{ py: 1.5 }}
                >
                  前往角色管理页面查看角色卡
                </Button>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
};

export default CharacterCardGenerator;