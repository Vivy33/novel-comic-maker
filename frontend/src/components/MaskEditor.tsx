import React, { useRef, useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  IconButton,
  Slider,
  Button,
  ButtonGroup,
  Tooltip,
} from '@mui/material';
import {
  Undo as UndoIcon,
  Redo as RedoIcon,
  Clear as ClearIcon,
} from '@mui/icons-material';

interface MaskEditorProps {
  originalImage?: string;
  initialMask?: string;
  onMaskChange: (maskDataUrl: string | null) => void;
  width?: number;
  height?: number;
}

const MaskEditor: React.FC<MaskEditorProps> = ({
  originalImage,
  initialMask,
  onMaskChange,
  width = 512,
  height = 512,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [brushSize, setBrushSize] = useState(10);
  const [history, setHistory] = useState<ImageData[]>([]);
  const [historyStep, setHistoryStep] = useState(-1);

  // 初始化Canvas
  useEffect(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!ctx) return;

    // 设置Canvas尺寸
    canvas.width = width;
    canvas.height = height;

    // 清除画布
    ctx.clearRect(0, 0, width, height);

    if (originalImage) {
      // 加载并显示原始图片作为背景
      const img = new Image();
      img.onload = () => {
        // 绘制背景图片（半透明）
        ctx.globalAlpha = 0.3;
        ctx.drawImage(img, 0, 0, width, height);

        // 重置绘制状态
        ctx.globalAlpha = 1.0;

        // 如果有初始掩码，加载它
        if (initialMask) {
          const maskImg = new Image();
          maskImg.onload = () => {
            ctx.globalAlpha = 1.0;
            ctx.drawImage(maskImg, 0, 0, width, height);
            // 保存初始状态到历史记录
            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            setHistory([imageData]);
            setHistoryStep(0);
          };
          maskImg.src = initialMask;
        }
      };
      img.src = originalImage;
    } else if (initialMask) {
      // 如果没有原始图片但有初始掩码
      const maskImg = new Image();
      maskImg.onload = () => {
        ctx.globalAlpha = 1.0;
        ctx.drawImage(maskImg, 0, 0, width, height);
        // 保存初始状态到历史记录
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        setHistory([imageData]);
        setHistoryStep(0);
      };
      maskImg.src = initialMask;
    }
  }, [originalImage, initialMask, width, height]);

  // 获取鼠标在Canvas中的位置
  const getMousePos = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!canvasRef.current) return { x: 0, y: 0 };

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();

    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  }, []);

  // 开始绘制
  const startDrawing = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!canvasRef.current) return;

    setIsDrawing(true);
    const pos = getMousePos(e);

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.beginPath();
    ctx.moveTo(pos.x, pos.y);
  }, [getMousePos]);

  // 绘制
  const draw = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing || !canvasRef.current) return;

    const pos = getMousePos(e);

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.lineTo(pos.x, pos.y);
    ctx.strokeStyle = 'black';
    ctx.lineWidth = brushSize;
    ctx.lineCap = 'round';
    ctx.stroke();
  }, [isDrawing, getMousePos, brushSize]);

  // 停止绘制
  const stopDrawing = useCallback(() => {
    setIsDrawing(false);
  }, []);

  // 清除画布
  const clearCanvas = useCallback(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 重新绘制背景图片
    if (originalImage) {
      const img = new Image();
      img.onload = () => {
        ctx.globalAlpha = 0.3;
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        ctx.globalAlpha = 1.0;
      };
      img.src = originalImage;
    }

    onMaskChange(null);
    setHistory([]);
    setHistoryStep(-1);
  }, [originalImage, onMaskChange]);

  // 保存到历史记录
  const saveToHistory = useCallback(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);

    const newHistory = history.slice(0, historyStep + 1);
    newHistory.push(imageData);

    setHistory(newHistory);
    setHistoryStep(historyStep + 1);
  }, [history, historyStep]);

  // 撤销
  const undo = useCallback(() => {
    if (historyStep > 0) {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const previousImageData = history[historyStep - 1];
      ctx.putImageData(previousImageData, 0, 0);

      setHistoryStep(historyStep - 1);
    }
  }, [history, historyStep]);

  // 重做
  const redo = useCallback(() => {
    if (historyStep < history.length - 1) {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const nextImageData = history[historyStep + 1];
      ctx.putImageData(nextImageData, 0, 0);

      setHistoryStep(historyStep + 1);
    }
  }, [history, historyStep]);

  // 导出掩码
  const exportMask = useCallback(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // 创建临时画布来生成黑白掩码
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = canvas.width;
    tempCanvas.height = canvas.height;
    const tempCtx = tempCanvas.getContext('2d');
    if (!tempCtx) return;

    // 绘制白色背景
    tempCtx.fillStyle = 'white';
    tempCtx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);

    // 绘制当前的黑色绘制内容
    tempCtx.drawImage(canvas, 0, 0);

    // 转换为DataURL
    const maskDataUrl = tempCanvas.toDataURL('image/png');
    onMaskChange(maskDataUrl);
  }, [onMaskChange]);

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        掩码绘制工具
      </Typography>

      {/* 工具栏 */}
      <Box sx={{ mb: 2, display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="body2" sx={{ minWidth: 80 }}>
            画笔大小:
          </Typography>
          <Slider
            value={brushSize}
            onChange={(_, value) => setBrushSize(value as number)}
            min={1}
            max={50}
            valueLabelDisplay="auto"
            sx={{ width: 120 }}
          />
        </Box>

        <ButtonGroup size="small">
          <Tooltip title="撤销">
            <IconButton onClick={undo} disabled={historyStep <= 0}>
              <UndoIcon />
            </IconButton>
          </Tooltip>

          <Tooltip title="重做">
            <IconButton onClick={redo} disabled={historyStep >= history.length - 1}>
              <RedoIcon />
            </IconButton>
          </Tooltip>

          <Tooltip title="清除画布">
            <IconButton onClick={clearCanvas} color="error">
              <ClearIcon />
            </IconButton>
          </Tooltip>
        </ButtonGroup>
      </Box>

      {/* Canvas画布 */}
      <Box
        sx={{
          border: '2px solid',
          borderColor: 'grey.300',
          borderRadius: 2,
          overflow: 'hidden',
          backgroundColor: 'white',
          cursor: isDrawing ? 'crosshair' : 'default',
        }}
      >
        <canvas
          ref={canvasRef}
          onMouseDown={startDrawing}
          onMouseMove={draw}
          onMouseUp={stopDrawing}
          onMouseLeave={stopDrawing}
          style={{
            display: 'block',
            touchAction: 'none',
          }}
        />
      </Box>

      {/* 操作按钮 */}
      <Box sx={{ mt: 2, display: 'flex', gap: 2, justifyContent: 'center' }}>
        <Button
          variant="outlined"
          onClick={saveToHistory}
          sx={{ mr: 1 }}
        >
          保存当前状态
        </Button>

        <Button
          variant="contained"
          onClick={exportMask}
        >
          生成掩码
        </Button>
      </Box>

      <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
        提示：黑色区域将被编辑，白色区域保持不变
      </Typography>
    </Box>
  );
};

export default MaskEditor;