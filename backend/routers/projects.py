"""
项目管理API路由
Project Management API Routes
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
import logging

from services.file_system import ProjectFileSystem
from models.file_system import ProjectCreate, ProjectInfo, ProjectTimeline

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/projects", tags=["projects"])

# 依赖注入：获取文件系统实例
def get_file_system():
    return ProjectFileSystem()


@router.post("/", response_model=ProjectInfo)
async def create_project(
    project: ProjectCreate,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    创建新项目
    Create a new project
    """
    try:
        project_path = fs.create_project(project.project_name, project.novel_text)
        project_info = fs.get_project_info(project_path)
        project_info["project_path"] = project_path
        return ProjectInfo(**project_info)
    except Exception as e:
        logger.error(f"创建项目失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建项目失败: {str(e)}")


@router.get("/", response_model=List[ProjectInfo])
async def list_projects(fs: ProjectFileSystem = Depends(get_file_system)):
    """
    获取所有项目列表
    Get list of all projects
    """
    try:
        projects = fs.list_projects()
        return [ProjectInfo(**project) for project in projects]
    except Exception as e:
        logger.error(f"获取项目列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取项目列表失败: {str(e)}")


@router.get("/{project_id}", response_model=ProjectInfo)
async def get_project(
    project_id: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    获取项目详细信息
    Get project details
    """
    try:
        # 查找项目路径
        projects = fs.list_projects()
        project_path = None

        for project in projects:
            if project.get("project_id") == project_id:
                project_path = project.get("project_path")
                break

        if not project_path:
            raise HTTPException(status_code=404, detail="项目不存在")

        project_info = fs.get_project_info(project_path)
        project_info["project_path"] = project_path
        return ProjectInfo(**project_info)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取项目信息失败: {str(e)}")


@router.get("/{project_id}/timeline", response_model=ProjectTimeline)
async def get_project_timeline(
    project_id: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    获取项目时间线
    Get project timeline
    """
    try:
        # 查找项目路径
        projects = fs.list_projects()
        project_path = None

        for project in projects:
            if project.get("project_id") == project_id:
                project_path = project.get("project_path")
                break

        if not project_path:
            raise HTTPException(status_code=404, detail="项目不存在")

        timeline = fs.get_project_timeline(project_path)
        return ProjectTimeline(
            project_id=project_id,
            timeline=timeline
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目时间线失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取项目时间线失败: {str(e)}")