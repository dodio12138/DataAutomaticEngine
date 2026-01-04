"""飞书多维表格同步路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, date, timedelta
from docker.errors import APIError
import os

from utils import client, LOG_DIR, ensure_image_exists, get_db_env_dict

router = APIRouter(prefix="/run", tags=["feishu-sync"])


class FeishuSyncRequest(BaseModel):
    start_date: str | None = Field(None, description="开始日期 YYYY-MM-DD（不传则获取全部数据）")
    end_date: str | None = Field(None, description="结束日期 YYYY-MM-DD（不传则获取全部数据）")
    store_code: str | None = Field(None, description="店铺代码（可选）")
    platform: str | None = Field(None, description="平台：panda/deliveroo（可选）")


@router.post("/feishu-sync")
def run_feishu_sync(req: FeishuSyncRequest):
    """
    创建临时容器执行飞书多维表格同步任务。
    
    逻辑：
    - 从 daily_sales_summary 表读取数据
    - 同步到飞书多维表格
    - 支持增量更新（已存在则更新，不存在则创建）
    - 默认同步全部已知数据，可指定日期范围
    """
    # 确保镜像存在
    ensure_image_exists("dataautomaticengine-feishu-sync", "../feishu_sync")
    
    # 构建环境变量（包含 DB 和飞书配置）
    env_dict = get_db_env_dict()
    
    # 添加飞书配置
    feishu_vars = [
        "FEISHU_APP_ID",
        "FEISHU_APP_SECRET",
        "FEISHU_BITABLE_APP_TOKEN",
        "FEISHU_BITABLE_TABLE_ID"
    ]
    
    for var in feishu_vars:
        value = os.environ.get(var)
        if not value:
            raise HTTPException(
                status_code=500,
                detail=f"缺少环境变量：{var}，请在 .env 文件中配置飞书相关参数"
            )
        env_dict[var] = value
    
    # 添加用户 Access Token（如果配置了）
    user_token = os.environ.get("FEISHU_USER_ACCESS_TOKEN")
    print(f"DEBUG API - USER_TOKEN: {'已获取' if user_token else '未获取'}")
    if user_token:
        print(f"DEBUG API - TOKEN前缀: {user_token[:10]}...")
        env_dict["FEISHU_USER_ACCESS_TOKEN"] = user_token
        print(f"DEBUG API - 已添加到env_dict")
    else:
        print("DEBUG API - user_token为空，将使用tenant_access_token")
    
    # 生成时间戳用于日志文件名和容器名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(LOG_DIR, f"feishu_sync_{timestamp}.log")
    container_name = f"feishu_sync_{timestamp}"
    
    # 构建命令参数
    command = ["python", "main.py"]
    if req.start_date:
        command.extend(["--start-date", req.start_date])
    if req.end_date:
        command.extend(["--end-date", req.end_date])
    if req.store_code:
        command.extend(["--store-code", req.store_code])
    if req.platform:
        command.extend(["--platform", req.platform])
    
    try:
        print(f"🚀 创建飞书同步容器: {container_name}")
        print(f"📝 命令: {' '.join(command)}")
        print(f"🔑 环境变量数量: {len(env_dict)}")
        
        # 创建临时容器（连接到 docker compose 网络）- 不自动删除
        container = client.containers.run(
            image="dataautomaticengine-feishu-sync",
            name=container_name,
            environment=env_dict,
            network="dataautomaticengine_default",
            working_dir="/app",
            labels={
                "com.docker.compose.project": "dataautomaticengine",
                "com.docker.compose.service": "feishu-sync-temp"
            },
            command=command,
            remove=False,  # 先不删除，获取日志后再删除
            detach=True
        )
        
        print(f"⏳ 等待容器执行完成...")
        
        # 等待容器执行完成（设置超时）
        result = container.wait(timeout=300)  # 5分钟超时
        exit_code = result['StatusCode']
        
        print(f"✅ 容器执行完成，退出码: {exit_code}")
        
        # 获取日志
        logs = container.logs(stdout=True, stderr=True).decode('utf-8', errors='ignore')
        
        # 删除容器
        try:
            container.remove()
        except:
            pass  # 删除失败不影响结果
        
        # 保存日志到文件
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(logs)
        
        # 打印日志到控制台
        print("=== 飞书同步日志 ===")
        print(logs)
        print("======================")
        
        if exit_code == 0:
            return {
                "status": "success",
                "message": "飞书同步完成",
                "log_file": log_file,
                "container_name": container_name,
                "exit_code": exit_code
            }
        else:
            return {
                "status": "failed",
                "message": f"飞书同步失败，退出码：{exit_code}",
                "log_file": log_file,
                "container_name": container_name,
                "exit_code": exit_code,
                "logs": logs[-1000:] if len(logs) > 1000 else logs  # 返回最后1000字符的日志
            }
    
    except APIError as e:
        error_msg = f"Docker 容器创建失败: {str(e)}"
        print(f"❌ {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        error_msg = f"未知错误: {type(e).__name__} - {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)
