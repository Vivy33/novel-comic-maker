import React from 'react';
import { useParams } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Paper,
} from '@mui/material';

const ComicPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          漫画阅读 - {id}
        </Typography>
        <Paper sx={{ p: 3, mt: 3 }}>
          <Typography variant="body1">
            这里将显示漫画 {id} 的阅读界面。
          </Typography>
        </Paper>
      </Box>
    </Container>
  );
};

export default ComicPage;