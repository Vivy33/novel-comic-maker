import React from 'react';
import {
  Container,
  Typography,
  Box,
  Paper,
  Button,
  Grid,
  Card,
  CardContent,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';

const HomePage: React.FC = () => {
  const navigate = useNavigate();

  const features = [
    {
      title: '🤖 AI智能生成',
      description: '基于豆包Seedream，智能将小说转换为漫画',
    },
    {
      title: '🎭 角色一致性',
      description: '先进的人物一致性机制，确保角色在整部漫画中保持统一外观',
    },
    {
      title: '📖 剧情连贯性',
      description: '前情提要系统，避免长文本理解问题，保持剧情连贯',
    },
    {
      title: '🎨 快速上手',
      description: '为不熟悉画画的用户提供直观的创作工具，快速生成高质量漫画',
    },
  ];

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 8, textAlign: 'center' }}>
        <Typography
          variant="h2"
          component="h1"
          gutterBottom
          sx={{
            background: 'linear-gradient(45deg, #1976d2, #dc004e)',
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            fontWeight: 'bold',
          }}
        >
          小说生成漫画应用
        </Typography>
        <Typography variant="h5" color="text.secondary" paragraph>
          AI驱动的智能漫画生成工具，让您的小说生动起来
        </Typography>
        <Box sx={{ mt: 4, mb: 8 }}>
          <Button
            variant="contained"
            size="large"
            sx={{ mr: 2, px: 4, py: 2 }}
            onClick={() => navigate('/projects')}
          >
            开始创作
          </Button>
          <Button
            variant="outlined"
            size="large"
            sx={{ px: 4, py: 2 }}
            onClick={() => navigate('/comics')}
          >
            浏览作品
          </Button>
        </Box>
      </Box>

      <Grid container spacing={4}>
        {features.map((feature, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card
              sx={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                transition: 'transform 0.2s',
                '&:hover': {
                  transform: 'translateY(-4px)',
                },
              }}
            >
              <CardContent sx={{ flexGrow: 1, textAlign: 'center' }}>
                <Typography variant="h6" component="h3" gutterBottom>
                  {feature.title}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {feature.description}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Container>
  );
};

export default HomePage;