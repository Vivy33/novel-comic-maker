import React from 'react';
import {
  Box,
  CardMedia,
  Typography,
  CircularProgress,
} from '@mui/material';
import {
  Person as PersonIcon,
} from '@mui/icons-material';

interface CharacterCardImageProps {
  projectId: string;
  characterName: string;
  size?: 'small' | 'medium' | 'large';
  viewType?: 'front' | 'back';
  fallbackText?: string;
}

const CharacterCardImage: React.FC<CharacterCardImageProps> = ({
  projectId,
  characterName,
  size = 'medium',
  viewType = 'front',
  fallbackText = '角色卡',
}) => {
  const [imageError, setImageError] = React.useState(false);
  const [isLoading, setIsLoading] = React.useState(true);

  // 根据尺寸设置样式
  const getSizeStyles = () => {
    switch (size) {
      case 'small':
        return { width: 60, height: 60, fontSize: 12 };
      case 'medium':
        return { width: 120, height: 120, fontSize: 16 };
      case 'large':
        return { width: 200, height: 200, fontSize: 20 };
      default:
        return { width: 120, height: 120, fontSize: 16 };
    }
  };

  const sizeStyles = getSizeStyles();
  const imageUrl = `/api/characters/${projectId}/${characterName}/card-image/${viewType}`;

  const handleImageLoad = () => {
    setIsLoading(false);
    setImageError(false);
  };

  const handleImageError = () => {
    setIsLoading(false);
    setImageError(true);
  };

  return (
    <Box
      sx={{
        width: sizeStyles.width,
        height: sizeStyles.height,
        position: 'relative',
        backgroundColor: 'grey.100',
        borderRadius: 1,
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {isLoading && (
        <Box sx={{ position: 'absolute', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <CircularProgress size={sizeStyles.width / 3} />
        </Box>
      )}

      {imageError ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', p: 1 }}>
          <PersonIcon sx={{ fontSize: sizeStyles.fontSize * 2, color: 'grey.400', mb: 0.5 }} />
          <Typography variant="caption" color="text.secondary" align="center" sx={{ fontSize: sizeStyles.fontSize * 0.75 }}>
            {fallbackText}
          </Typography>
        </Box>
      ) : (
        <CardMedia
          component="img"
          image={imageUrl}
          alt={`${characterName} - ${viewType} view`}
          onLoad={handleImageLoad}
          onError={handleImageError}
          sx={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            display: isLoading ? 'none' : 'block',
          }}
        />
      )}
    </Box>
  );
};

export default CharacterCardImage;