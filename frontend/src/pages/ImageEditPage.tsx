import React, { useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Paper,
  Button,
  Grid,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Upload as UploadIcon,
  Image as ImageIcon,
  Download as DownloadIcon,
  Refresh as RefreshIcon,
  Compare as CompareIcon,
  PhotoFilter as PhotoFilterIcon,
  } from '@mui/icons-material';
import { useMutation } from '@tanstack/react-query';
import { imageEditService, handleApiError } from '../services';
import MaskEditor from '../components/MaskEditor';

const ImageEditPage: React.FC = () => {
  const { id: projectId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const maskInputRef = useRef<HTMLInputElement>(null);

  // 状态管理
  const [originalImage, setOriginalImage] = useState<string | null>(null);
  const [editedImage, setEditedImage] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedMaskFile, setSelectedMaskFile] = useState<File | null>(null);
  const [maskPreview, setMaskPreview] = useState<string | null>(null);
  const [editPrompt, setEditPrompt] = useState('');
  const [selectedModel] = useState('doubao-seedream-4-0-250828');
  const [imageSize, setImageSize] = useState('1024x1024');
    const [notification, setNotification] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'warning';
  }>({
    open: false,
    message: '',
    severity: 'success',
  });
  const [showCompareDialog, setShowCompareDialog] = useState(false);

  // 同步图片验证函数
  const validateImageFile = (file: File): { isValid: boolean; error?: string } => {
    // 检查文件类型
    if (!file.type.startsWith('image/')) {
      return { isValid: false, error: '请选择有效的图片文件' };
    }

    // 检查文件大小（不能太小，避免1x1像素的图片）
    if (file.size < 100) { // 小于100字节的图片很可能有问题
      return { isValid: false, error: '图片文件太小，请选择正常的图片文件' };
    }

    // 检查文件扩展名
    const validExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'];
    const fileName = file.name.toLowerCase();
    const hasValidExtension = validExtensions.some(ext => fileName.endsWith(ext));

    if (!hasValidExtension) {
      return { isValid: false, error: '不支持的图片格式，请使用 JPG、PNG、GIF 等常见格式' };
    }

    return { isValid: true };
  };

  // 图片上传预览
  const handleImagePreview = (file: File) => {
    // 先进行同步验证
    const validation = validateImageFile(file);
    if (!validation.isValid) {
      showNotification(validation.error || '图片验证失败', 'error');
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        // 检查图片尺寸，豆包要求最小14x14像素
        if (img.width < 14 || img.height < 14) {
          showNotification('图片尺寸太小，请上传至少14x14像素的图片', 'error');
          setSelectedFile(null);
          setOriginalImage(null);
          if (fileInputRef.current) fileInputRef.current.value = '';
          return;
        }

        // 检查图片尺寸是否过大（避免性能问题）
        if (img.width > 4096 || img.height > 4096) {
          showNotification('图片尺寸过大，请使用小于4096x4096像素的图片', 'error');
          setSelectedFile(null);
          setOriginalImage(null);
          if (fileInputRef.current) fileInputRef.current.value = '';
          return;
        }

        setOriginalImage(e.target?.result as string);
        setEditedImage(null);
        showNotification('图片选择成功', 'success');
      };
      img.onerror = () => {
        showNotification('图片格式无效，请选择其他图片', 'error');
        setSelectedFile(null);
        setOriginalImage(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
      };
      img.src = e.target?.result as string;
    };
    reader.readAsDataURL(file);
  };

  // 掩码文件预览
  const handleMaskPreview = (file: File) => {
    const validation = validateImageFile(file);
    if (!validation.isValid) {
      showNotification(validation.error || '掩码文件验证失败', 'error');
      setSelectedMaskFile(null);
      if (maskInputRef.current) maskInputRef.current.value = '';
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        setMaskPreview(e.target?.result as string);
        showNotification('掩码文件选择成功', 'success');
      };
      img.onerror = () => {
        showNotification('掩码文件格式无效，请选择其他图片', 'error');
        setSelectedMaskFile(null);
        setMaskPreview(null);
        if (maskInputRef.current) maskInputRef.current.value = '';
      };
      img.src = e.target?.result as string;
    };
    reader.readAsDataURL(file);
  };

  // 图像编辑
  const imageEditMutation = useMutation({
    mutationFn: (data: { prompt: string; file: File; maskFile?: File | null }) =>
      imageEditService.editUploadedImage(
        data.prompt,
        data.file,
        data.maskFile || undefined,
        selectedModel,
        imageSize
      ),
    onSuccess: (response) => {
      if (response.success && response.result_url) {
        setEditedImage(response.result_url);
        showNotification('图像编辑成功', 'success');
      }
    },
    onError: (error) => {
      const apiError = handleApiError(error);
      showNotification(`图像编辑失败: ${apiError.message}`, 'error');
    },
  });

  // 处理主图片文件选择
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    // 先进行同步验证
    const validation = validateImageFile(file);
    if (!validation.isValid) {
      showNotification(validation.error || '图片验证失败', 'error');
      setSelectedFile(null);
      setOriginalImage(null);
      setEditedImage(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    setSelectedFile(file);
    handleImagePreview(file);
  };

  // 处理掩码文件选择
  const handleMaskSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    setSelectedMaskFile(file);
    handleMaskPreview(file);
  };

  // 处理图像编辑
  const handleImageEdit = () => {
    if (!selectedFile) {
      showNotification('请先上传图片', 'error');
      return;
    }

    if (!editPrompt || !editPrompt.trim()) {
      showNotification('请输入编辑提示', 'error');
      return;
    }

    if (editPrompt.trim().length < 3) {
      showNotification('编辑提示太短，请输入至少3个字符的描述', 'error');
      return;
    }

    // 验证文件是否仍然有效
    if (selectedFile.size < 100) {
      showNotification('图片文件无效，请重新选择', 'error');
      return;
    }

    console.log('发送图像编辑请求:', {
      prompt: editPrompt.trim(),
      fileName: selectedFile.name,
      fileSize: selectedFile.size,
      model: selectedModel,
      size: imageSize
    });

    console.log('发送图像编辑请求:', {
      prompt: editPrompt.trim(),
      fileName: selectedFile.name,
      fileSize: selectedFile.size,
      maskFileName: selectedMaskFile?.name,
      hasMask: !!selectedMaskFile,
      model: selectedModel,
      size: imageSize
    });

    imageEditMutation.mutate({
      prompt: editPrompt.trim(),
      file: selectedFile,
      maskFile: selectedMaskFile || undefined,
    });
  };

  // 下载图片
  const handleDownload = async (imageUrl: string, filename: string) => {
    try {
      // 使用后端代理下载，避免CORS问题
      const proxyUrl = `/api/image-edit/proxy-download?image_url=${encodeURIComponent(imageUrl)}`;
      const response = await fetch(proxyUrl);

      if (!response.ok) {
        throw new Error(`下载失败: ${response.statusText}`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      showNotification('图片下载成功', 'success');
    } catch (error) {
      console.error('下载错误:', error);
      showNotification('下载失败', 'error');
    }
  };

  // 重置
  const handleReset = () => {
    setOriginalImage(null);
    setEditedImage(null);
    setSelectedFile(null);
    setSelectedMaskFile(null);
    setMaskPreview(null);
    setEditPrompt('');
    if (fileInputRef.current) fileInputRef.current.value = '';
    if (maskInputRef.current) maskInputRef.current.value = '';
  };

  // 显示通知
  const showNotification = (message: string, severity: 'success' | 'error' | 'warning') => {
    setNotification({ open: true, message, severity });
  };

  // 关闭通知
  const closeNotification = () => {
    setNotification({ ...notification, open: false });
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
              图像编辑
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 2 }}>
            {editedImage && (
              <>
                <Tooltip title="对比原图">
                  <IconButton onClick={() => setShowCompareDialog(true)}>
                    <CompareIcon />
                  </IconButton>
                </Tooltip>
                <Button
                  variant="outlined"
                  startIcon={<DownloadIcon />}
                  onClick={() => handleDownload(editedImage, 'generated-image.png')}
                >
                  下载结果
                </Button>
              </>
            )}
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={handleReset}
            >
              重置
            </Button>
          </Box>
        </Box>

        <Grid container spacing={3}>
          {/* 左侧：控制面板 */}
          <Grid item xs={12} md={5}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                编辑控制
              </Typography>

              {/* 上传参考图 */}
              <Box sx={{ mb: 3 }}>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleFileSelect}
                  style={{ display: 'none' }}
                />
                <Button
                  variant="outlined"
                  fullWidth
                  startIcon={<UploadIcon />}
                  onClick={() => fileInputRef.current?.click()}
                  sx={{ py: 2 }}
                >
                  选择参考图
                </Button>
              </Box>

              {/* 上传掩码 */}
              <Box sx={{ mb: 3 }}>
                <input
                  ref={maskInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleMaskSelect}
                  style={{ display: 'none' }}
                />
                <Button
                  variant="outlined"
                  fullWidth
                  startIcon={<UploadIcon />}
                  onClick={() => maskInputRef.current?.click()}
                  sx={{ py: 2 }}
                >
                  {selectedMaskFile ? '更换掩码' : '选择掩码（可选）'}
                </Button>
              </Box>

              {/* 掩码预览 */}
              {maskPreview && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    掩码预览
                  </Typography>
                  <MaskEditor
                      originalImage={originalImage || ''}
                      initialMask={maskPreview || ''}
                      onMaskChange={(maskDataUrl) => {
                        setMaskPreview(maskDataUrl);
                        // 如果有掩码数据，创建File对象用于API调用
                        if (maskDataUrl) {
                          fetch(maskDataUrl)
                            .then(res => res.blob())
                            .then(blob => {
                              const file = new File([blob], 'mask.png', { type: 'image/png' });
                              setSelectedMaskFile(file);
                            });
                        } else {
                          setSelectedMaskFile(null);
                        }
                      }}
                    />
                </Box>
              )}

              {/* 编辑提示 */}
              <TextField
                fullWidth
                multiline
                rows={3}
                label="编辑提示"
                placeholder="描述您想要的编辑效果..."
                value={editPrompt}
                onChange={(e) => setEditPrompt(e.target.value)}
                sx={{ mb: 3 }}
              />

              {/* 图片尺寸 */}
              <FormControl fullWidth sx={{ mb: 3 }}>
                <InputLabel>图片尺寸</InputLabel>
                <Select
                  value={imageSize}
                  label="图片尺寸"
                  onChange={(e) => setImageSize(e.target.value)}
                >
                  <MenuItem value="512x512">512x512</MenuItem>
                  <MenuItem value="768x768">768x768</MenuItem>
                  <MenuItem value="1024x1024">1024x1024</MenuItem>
                  <MenuItem value="1024x768">1024x768 (横版)</MenuItem>
                  <MenuItem value="768x1024">768x1024 (竖版)</MenuItem>
                  <MenuItem value="1280x720">1280x720 (高清横版)</MenuItem>
                  <MenuItem value="720x1280">720x1280 (高清竖版)</MenuItem>
                </Select>
              </FormControl>

              
              {/* 编辑按钮 */}
              <Button
                variant="contained"
                fullWidth
                startIcon={<PhotoFilterIcon />}
                onClick={handleImageEdit}
                disabled={!selectedFile || !editPrompt.trim() || imageEditMutation.isPending}
                sx={{ py: 1.5 }}
              >
                {imageEditMutation.isPending ? '编辑中...' : '开始编辑'}
              </Button>
            </Paper>
          </Grid>

          {/* 右侧：图片预览 */}
          <Grid item xs={12} md={7}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                图片预览
              </Typography>

              {imageEditMutation.isPending ? (
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 4 }}>
                  <CircularProgress />
                  <Typography variant="body2" sx={{ mt: 2 }}>
                    编辑中...
                  </Typography>
                </Box>
              ) : (
                <Grid container spacing={2}>
                  {/* 原图 */}
                  {originalImage && (
                    <Grid item xs={12} md={editedImage ? 6 : 12}>
                      <Box>
                        <Typography variant="subtitle2" gutterBottom>
                          参考图
                        </Typography>
                        <Box
                          sx={{
                            border: '1px solid',
                            borderColor: 'grey.300',
                            borderRadius: 1,
                            overflow: 'hidden',
                            backgroundColor: 'grey.50',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            minHeight: 300,
                          }}
                        >
                          <img
                            src={originalImage}
                            alt="参考图"
                            style={{
                              maxWidth: '100%',
                              maxHeight: '400px',
                              objectFit: 'contain',
                            }}
                          />
                        </Box>
                      </Box>
                    </Grid>
                  )}

                  {/* 编辑后的图片 */}
                  {editedImage && (
                    <Grid item xs={12} md={6}>
                      <Box>
                        <Typography variant="subtitle2" gutterBottom>
                          编辑结果
                          <Chip
                            label="新"
                            size="small"
                            color="success"
                            sx={{ ml: 1 }}
                          />
                        </Typography>
                        <Box
                          sx={{
                            border: '2px solid',
                            borderColor: 'success.main',
                            borderRadius: 1,
                            overflow: 'hidden',
                            backgroundColor: 'grey.50',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            minHeight: 300,
                          }}
                        >
                          <img
                            src={editedImage}
                            alt="编辑结果"
                            style={{
                              maxWidth: '100%',
                              maxHeight: '400px',
                              objectFit: 'contain',
                            }}
                          />
                        </Box>
                      </Box>
                    </Grid>
                  )}

                  {/* 空状态 */}
                  {!originalImage && (
                    <Grid item xs={12}>
                      <Box
                        sx={{
                          border: '2px dashed',
                          borderColor: 'grey.300',
                          borderRadius: 1,
                          p: 4,
                          textAlign: 'center',
                          backgroundColor: 'grey.50',
                        }}
                      >
                        <ImageIcon sx={{ fontSize: 64, color: 'grey.400', mb: 2 }} />
                        <Typography variant="h6" color="text.secondary" gutterBottom>
                          尚未选择图片
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          请在左侧选择参考图片开始编辑
                        </Typography>
                      </Box>
                    </Grid>
                  )}
                </Grid>
              )}
            </Paper>
          </Grid>
        </Grid>

        {/* 对比对话框 */}
        <Dialog
          open={showCompareDialog}
          onClose={() => setShowCompareDialog(false)}
          maxWidth="lg"
          fullWidth
        >
          <DialogTitle>图片对比</DialogTitle>
          <DialogContent>
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Typography variant="subtitle2" gutterBottom textAlign="center">
                  参考图
                </Typography>
                {originalImage && (
                  <Box sx={{ textAlign: 'center' }}>
                    <img
                      src={originalImage}
                      alt="参考图"
                      style={{
                        maxWidth: '100%',
                        maxHeight: '400px',
                        objectFit: 'contain',
                      }}
                    />
                  </Box>
                )}
              </Grid>
              <Grid item xs={6}>
                <Typography variant="subtitle2" gutterBottom textAlign="center">
                  编辑结果
                </Typography>
                {editedImage && (
                  <Box sx={{ textAlign: 'center' }}>
                    <img
                      src={editedImage}
                      alt="编辑结果"
                      style={{
                        maxWidth: '100%',
                        maxHeight: '400px',
                        objectFit: 'contain',
                      }}
                    />
                  </Box>
                )}
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowCompareDialog(false)}>
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

export default ImageEditPage;