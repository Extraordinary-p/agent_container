import json
from typing import Dict, Any, List, Optional
from loguru import logger
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings
from tools.tool_definitions import get_tools_list
from tools.tool_executor import ToolExecutor

class AIOpsAgent:
    def __init__(self, provider: Optional[str] = None, api_key: Optional[str] = None, 
                 base_url: Optional[str] = None, model: Optional[str] = None):
        self.provider = provider or settings.PROVIDER
        provider_config = settings.get_provider_config()
        
        self.api_key = api_key or provider_config["api_key"]
        self.base_url = base_url or provider_config["base_url"]
        self.model = model or provider_config["model"]
        
        if not self.api_key:
            logger.warning(f"未配置 {self.provider} 的 API Key，AI 模式可能无法正常工作")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        self.tools = get_tools_list()
        self.tool_executor = ToolExecutor()
        
        self.conversation_history: List[Dict[str, Any]] = []
        self.detected_issues: List[str] = []
        self.diagnosis_recommendations: List[str] = []
        self.actions_taken: List[str] = []
        
        self.max_iterations = settings.MAX_TOOL_CALL_ITERATIONS
        
        logger.info(f"初始化 AI Agent - Provider: {self.provider}, Model: {self.model}")
    
    def set_system_prompt(self) -> str:
        return """你是一个专业的Docker AIOps 智能运维 Agent。你的职责是：

1. **异常发现**：主动检查系统状态，识别潜在问题
2. **诊断分析**：深入分析问题根源，给出专业建议
3. **自动处置**：在安全范围内执行修复动作

工作流程：
- 首先进行全面的系统健康检查
- 发现问题后，使用相应工具进行深度诊断
- 分析诊断结果，给出修复建议
- 在用户允许的情况下自动执行修复动作
- 生成最终的诊断报告

注意事项：
- 始终按照 Tool Calling 规范进行操作
- 优先验证配置和基础服务状态
- 对于重启等破坏性操作要谨慎，确保确实需要
- 每次只调用一个工具，逐步分析
- 使用 final_report 生成最终报告来结束对话

诊断流程要求（必须严格遵守）：
1. 发现容器停止或异常时，必须调用 inspect_container_logs 检查日志
2. 检查日志时，要找到容器退出的具体原因
3. 只有明确原因后，才能执行启动或重启操作

NetBox 关键服务包括：
- netbox: 主应用
- postgres: 数据库
- redis: 缓存和队列
- netbox-worker: 后台任务
- nginx: 反向代理
"""
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _call_openai_with_retry(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]):
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.1
        )
    
    def run_diagnosis_cycle(self, initial_query: str = "检查 NetBox Docker 环境的健康状态") -> Dict[str, Any]:
        logger.info(f"开始诊断周期，初始查询: {initial_query}")
        
        if not self.api_key:
            error_msg = f"未配置 {self.provider} 的 API Key，请在 .env 文件中配置后重试"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
        self.conversation_history = [
            {"role": "system", "content": self.set_system_prompt()},
            {"role": "user", "content": initial_query}
        ]
        
        for iteration in range(self.max_iterations):
            logger.info(f"迭代 {iteration + 1}/{self.max_iterations}")
            
            try:
                response = self._call_openai_with_retry(
                    messages=self.conversation_history, #对话的上下文历史信息
                    tools=self.tools
                )
            except Exception as e:
                logger.error(f"API 调用失败: {e}")
                return {"success": False, "error": f"API error: {str(e)}"}
            
            response_message = response.choices[0].message
            #重复调用，添加上下文信息到新一次的chat中
            self.conversation_history.append(response_message.dict())
            '''
            tool_calls: OpenAI Function Calling（工具调用）机制的核心。
            tool_calls 是 OpenAI API 返回的消息对象中的一个字段，当 LLM 决定需要调用工具时才会存在。
            如果 LLM 认为不需要调用工具（直接回答问题），这个字段就是 None。
            '''
            if not response_message.tool_calls:
                logger.info("没有更多工具调用，完成诊断流程")
                break
            
            for tool_call in response_message.tool_calls:
                tool_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                logger.info(f"执行工具: {tool_name}")
                tool_result = self.tool_executor.execute(tool_name, arguments)

                #如果工具返回中有问题，则将问题对应的信息添加到全局列表中
                if "issues" in tool_result and tool_result["issues"]:
                    self.detected_issues.extend(tool_result["issues"])
                #如果使用了处置动作的工具，则也加入全局列表中
                if tool_name in ["restart_service","prune_docker_resources","start_service"]:
                    if tool_result.get("success"):
                        self.actions_taken.append(tool_result.get("message", f"执行了 {tool_name}"))

                #如果工具名称是报告，则用收集到的 issues 覆盖 LLM 传的
                if tool_name == "final_report":
                    # 用实际收集到的 issues 和 actions，避免 LLM 漏掉
                    arguments["issues_found"] = self.detected_issues
                    arguments["actions_taken"] = self.actions_taken
                    if self.diagnosis_recommendations:
                        arguments["recommendations"] = self.diagnosis_recommendations
                    # 重新执行 final_report 生成正确报告
                    return self.tool_executor.execute(tool_name, arguments)

                #上下问历史中添加本次调用信息
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": json.dumps(tool_result, ensure_ascii=False)
                })
        
        return self._generate_final_report()
    
    def _generate_final_report(self) -> Dict[str, Any]:
        #如果detected_issues不存在的话则运行正常。
        if not self.detected_issues:
            summary = "系统运行正常，未发现明显异常"
        else:
            summary = f"检测到 {len(self.detected_issues)} 个问题，已执行 {len(self.actions_taken)} 个处置动作"

        #调用生成报告的工具
        return self.tool_executor.execute("final_report", {
            "summary": summary,
            #将所有问题传入
            "issues_found": self.detected_issues,
            "recommendations": self.diagnosis_recommendations or ["建议定期检查系统健康状态"],
            "actions_taken": self.actions_taken or ["未执行任何自动处置动作"]
        })
    
    def get_statistics(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "total_issues_detected": len(self.detected_issues),
            "total_actions_taken": len(self.actions_taken),
            "total_iterations": len(self.conversation_history) // 2
        }
