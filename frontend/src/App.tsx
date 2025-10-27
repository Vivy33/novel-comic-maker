import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { Container, Box, Typography } from '@mui/material';
import CustomQueryClientProvider from './providers/QueryClientProvider';
import Navbar from './components/Navbar';
import HomePage from './pages/HomePage';
import ProjectPage from './pages/ProjectPage';
import ComicPage from './pages/ComicPage';
import ProjectsPage from './pages/ProjectsPage';
import CharactersPage from './pages/CharactersPage';
import CharacterCardGeneratorPage from './pages/CharacterCardGeneratorPage';
import ComicGenerationPage from './pages/ComicGenerationPage';
import SegmentedComicGenerationPage from './pages/SegmentedComicGenerationPage';
import WorkflowOrchestratorPage from './pages/WorkflowOrchestratorPage';
import ImageEditPage from './pages/ImageEditPage';
import CoverGenerationPage from './pages/CoverGenerationPage';
import { Routes, Route } from 'react-router-dom';

function App() {
  return (
    <CustomQueryClientProvider>
      <BrowserRouter>
        <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
          <Navbar />
          <Box component="main" sx={{ flexGrow: 1, py: 3 }}>
            <Container maxWidth="xl">
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/projects" element={<ProjectsPage />} />
                <Route path="/project/:id" element={<ProjectPage />} />
                <Route path="/project/:id/characters" element={<CharactersPage />} />
                <Route path="/project/:id/characters/:characterId/:characterName/generate-card" element={<CharacterCardGeneratorPage />} />
                <Route path="/project/:id/generate" element={<ComicGenerationPage />} />
                <Route path="/project/:id/generate-segmented" element={<SegmentedComicGenerationPage />} />
                <Route path="/project/:id/cover-generate" element={<CoverGenerationPage />} />
                <Route path="/project/:id/image-edit" element={<ImageEditPage />} />
                <Route path="/project/:id/workflow" element={<WorkflowOrchestratorPage />} />
                <Route path="/comic/:id" element={<ComicPage />} />
              </Routes>
            </Container>
          </Box>
          <Box
            component="footer"
            sx={{
              py: 3,
              backgroundColor: 'background.paper',
              textAlign: 'center',
            }}
          >
            <Typography variant="body2" color="text.secondary">
              © 2025 小说生成漫画应用. All rights reserved.
            </Typography>
          </Box>
        </Box>
      </BrowserRouter>
    </CustomQueryClientProvider>
  );
}

export default App;