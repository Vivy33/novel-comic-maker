import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  useTheme,
} from '@mui/material';
import { useNavigate, useLocation } from 'react-router-dom';

const Navbar: React.FC = () => {
  const theme = useTheme();
  const navigate = useNavigate();
  const location = useLocation();

  const navItems = [
    { label: '首页', path: '/' },
    { label: '项目', path: '/projects' },
    { label: '漫画', path: '/comics' },
  ];

  return (
    <AppBar
      position="static"
      sx={{
        background: `linear-gradient(45deg, ${theme.palette.primary.main} 30%, ${theme.palette.secondary.main} 90%)`,
      }}
    >
      <Toolbar>
        <Typography
          variant="h6"
          component="div"
          sx={{ flexGrow: 1, cursor: 'pointer' }}
          onClick={() => navigate('/')}
        >
          🎨 小说生成漫画应用
        </Typography>
        <Box>
          {navItems.map((item) => (
            <Button
              key={item.path}
              color="inherit"
              sx={{
                mx: 1,
                borderBottom: location.pathname === item.path ? '2px solid white' : 'none',
                borderRadius: 0,
              }}
              onClick={() => navigate(item.path)}
            >
              {item.label}
            </Button>
          ))}
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;